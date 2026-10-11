#!/usr/bin/env python3
"""Idempotent, incremental data updater for the stock insights dashboard.

Usage:
  python update_data.py                 # daily run: prices (incremental) + fundamentals if stale (>7 days) + metrics
  python update_data.py --full-prices   # re-download full price history
  python update_data.py --force-fund    # refresh all fundamentals now
  python update_data.py --prices-only   # intraday snapshot (e.g. 3:45 PM IST): prices + metrics only
  python update_data.py --universe nifty500   # other universes (NSE index constituent CSV)
  Default universe = data/universe_tech.csv (curated Indian tech/SaaS/AI/fintech list; edit to add names)

Sources:
  * Constituents: NSE archives index constituent CSV (public)
  * Prices: Yahoo Finance via yfinance (.NS tickers, ^NSEI, ^BSESN)
  * Fundamentals: screener.in public company pages (polite: 1 req / ~4s, cached, weekly refresh)
"""
import argparse, datetime as dt, io, json, logging, os, random, re, sqlite3, sys, time
import pandas as pd, requests
import yfinance as yf
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "market.db")
CACHE = os.path.join(DATA, "screener_cache")
os.makedirs(CACHE, exist_ok=True)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
UNIVERSES = {
    "tech": os.path.join(DATA, "universe_tech.csv"),   # curated Indian tech / SaaS / AI / fintech list (default)
    "nifty50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "nifty100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "nifty500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
}
INDICES = {"^CNXIT": "Nifty IT", "^NSEI": "Nifty 50", "^BSESN": "Sensex"}
FUND_MAX_AGE_DAYS = 7
# stop hammering screener.in when it is clearly refusing us (e.g. blocked cloud/CI IP ranges):
# after this many companies in a row return nothing, keep the cached fundamentals and move on
FUND_MAX_CONSECUTIVE_FAILS = int(os.environ.get("BEEMER_FUND_MAX_FAILS", "5"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("update")


def db():
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS prices(symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
        adj_close REAL, volume REAL, PRIMARY KEY(symbol, date));
    CREATE TABLE IF NOT EXISTS universe(symbol TEXT PRIMARY KEY, name TEXT, industry TEXT, isin TEXT, yf TEXT, universe TEXT,
        subsector TEXT, theme TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS fundamentals(symbol TEXT, section TEXT, item TEXT, period TEXT, value REAL,
        PRIMARY KEY(symbol, section, item, period));
    CREATE TABLE IF NOT EXISTS fund_meta(symbol TEXT PRIMARY KEY, fetched_at TEXT, basis TEXT, top_ratios TEXT, about TEXT);
    CREATE TABLE IF NOT EXISTS runs(ts TEXT, step TEXT, detail TEXT);
    """)
    return con


def load_universe(con, name):
    src = UNIVERSES[name]
    if src.endswith(".csv") and os.path.exists(src):          # curated local list
        df = pd.read_csv(src).fillna("")
        rows = [(r.symbol, r.name, r.subsector, "", f"{r.symbol}.NS", name, r.subsector, r.theme, r.note) for r in df.itertuples()]
    else:                                                       # NSE index constituent list
        try:
            r = requests.get(src, headers={"User-Agent": UA}, timeout=30); r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            df.to_csv(os.path.join(DATA, f"{name}_constituents.csv"), index=False)
        except Exception as e:
            log.warning("constituent download failed (%s); using cached list", e)
            df = pd.read_csv(os.path.join(DATA, f"{name}_constituents.csv"))
        df.columns = [c.strip() for c in df.columns]
        rows = [(s, n, i, isin, f"{s}.NS", name, i, "", "") for n, i, s, isin in
                zip(df["Company Name"], df["Industry"], df["Symbol"], df["ISIN Code"])]
    con.execute("DELETE FROM universe")
    con.executemany("INSERT OR REPLACE INTO universe VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    log.info("universe %s: %d symbols", name, len(rows))
    return [r[0] for r in rows]


def _store_prices(con, sym, h):
    if h is None or h.empty:
        return 0
    h = h.dropna(subset=["Close"])
    recs = [(sym, d.strftime("%Y-%m-%d"), float(r.Open), float(r.High), float(r.Low), float(r.Close),
             float(r["Adj Close"]), float(r.Volume or 0)) for d, r in h.iterrows()]
    con.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?)", recs)
    return len(recs)


def update_prices(con, tickers, full=False):
    """tickers: dict of db-symbol -> yahoo ticker"""
    n_total = 0
    for sym, yft in tickers.items():
        last = con.execute("SELECT MAX(date) FROM prices WHERE symbol=?", (sym,)).fetchone()[0]
        try:
            if full or last is None:
                h = yf.Ticker(yft).history(period="max", auto_adjust=False, actions=False)
                con.execute("DELETE FROM prices WHERE symbol=?", (sym,))
            else:
                start = (pd.Timestamp(last) - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
                h = yf.Ticker(yft).history(start=start, auto_adjust=False, actions=False)
                # corporate action check: if adj factor on overlapping days changed -> refetch full
                old = pd.read_sql("SELECT date, close, adj_close FROM prices WHERE symbol=? AND date>=?",
                                  con, params=(sym, start)).set_index("date")
                if not h.empty and not old.empty:
                    h2 = h.copy(); h2.index = h2.index.strftime("%Y-%m-%d")
                    j = old.join(h2[["Close", "Adj Close"]], how="inner")
                    if len(j):
                        f_old = (j.adj_close / j.close).iloc[0]; f_new = (j["Adj Close"] / j["Close"]).iloc[0]
                        r_close = (j.close / j["Close"]).iloc[0]
                        if abs(f_old / f_new - 1) > 0.002 or abs(r_close - 1) > 0.01:
                            log.info("%s: corporate action detected -> full refresh", sym)
                            h = yf.Ticker(yft).history(period="max", auto_adjust=False, actions=False)
                            con.execute("DELETE FROM prices WHERE symbol=?", (sym,))
            n = _store_prices(con, sym, h); n_total += n
            con.commit()
        except Exception as e:
            log.warning("price update failed for %s: %s", sym, e)
        time.sleep(0.3)
    # trim known-bad pre-listing rows (universe CSV column data_start)
    src = UNIVERSES.get("tech")
    if src and os.path.exists(src):
        u = pd.read_csv(src).fillna("")
        for r in u.itertuples():
            if getattr(r, "data_start", ""):
                con.execute("DELETE FROM prices WHERE symbol=? AND date<?", (r.symbol, r.data_start))
        con.commit()
    log.info("prices: %d rows written", n_total)
    con.execute("INSERT INTO runs VALUES (?,?,?)", (dt.datetime.now().isoformat(), "prices", str(n_total)))
    con.commit()


# ---------------- screener.in fundamentals (polite) ----------------
def _num(s):
    s = (s or "").replace(",", "").replace("%", "").replace("₹", "").strip()
    if s in ("", "-", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_screener(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for sec in ["quarters", "profit-loss", "balance-sheet", "cash-flow", "ratios", "shareholding"]:
        t = soup.select_one(f"section#{sec} table")
        if not t:
            continue
        hdr = [th.get_text(strip=True) for th in t.select("thead th")][1:]
        for tr in t.select("tbody tr"):
            tds = tr.select("td")
            if not tds:
                continue
            item = tds[0].get_text(" ", strip=True).replace("+", "").strip()
            if item.lower().startswith("raw pdf"):
                continue
            for p, td in zip(hdr, tds[1:]):
                v = _num(td.get_text(strip=True))
                if v is not None:
                    out.append((sec, item, p, v))
    top = {}
    for li in soup.select("#top-ratios li"):
        n = li.select_one(".name"); v = li.select_one(".value")
        if n and v:
            top[n.get_text(strip=True)] = " ".join(v.get_text(" ", strip=True).split())
    for t in soup.select("table.ranges-table"):
        rows = [x.get_text(" ", strip=True) for x in t.select("tr")]
        if rows:
            top[rows[0]] = "; ".join(rows[1:])
    about = soup.select_one(".company-profile .about p") or soup.select_one(".about p")
    return out, top, (about.get_text(" ", strip=True) if about else "")


def fetch_screener(sym, session):
    rows = []
    for basis, url in [("consolidated", f"https://www.screener.in/company/{sym}/consolidated/"),
                       ("standalone", f"https://www.screener.in/company/{sym}/")]:
        r = session.get(url, timeout=30)
        time.sleep(3.5 + random.random() * 1.5)  # be polite
        if r.status_code == 429:
            log.warning("screener rate-limited; sleeping 60s"); time.sleep(60)
            r = session.get(url, timeout=30)
        if r.status_code != 200:
            log.warning("screener %s -> HTTP %s", url, r.status_code); continue
        with open(os.path.join(CACHE, f"{sym}_{basis}.html"), "w") as f:
            f.write(r.text)
        rows, top, about = parse_screener(r.text)
        pl = [x for x in rows if x[0] == "profit-loss"]
        if len(pl) > 20:  # usable annual data
            return basis, rows, top, about
    return None, rows, {}, ""


def update_fundamentals(con, symbols, force=False):
    s = requests.Session(); s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    done = fails = 0
    for sym in symbols:
        row = con.execute("SELECT fetched_at FROM fund_meta WHERE symbol=?", (sym,)).fetchone()
        if row and not force and (dt.datetime.now() - dt.datetime.fromisoformat(row[0])).days < FUND_MAX_AGE_DAYS:
            continue
        try:
            basis, rows, top, about = fetch_screener(sym, s)
            if not basis:
                log.warning("no fundamentals for %s", sym)
                fails += 1
                if fails >= FUND_MAX_CONSECUTIVE_FAILS:
                    log.warning("screener.in refused %d companies in a row - likely blocked from this network; "
                                "keeping previously stored fundamentals and continuing with prices only", fails)
                    break
                continue
            fails = 0
            con.execute("DELETE FROM fundamentals WHERE symbol=?", (sym,))
            con.executemany("INSERT OR REPLACE INTO fundamentals VALUES (?,?,?,?,?)", [(sym,) + r for r in rows])
            con.execute("INSERT OR REPLACE INTO fund_meta VALUES (?,?,?,?,?)",
                        (sym, dt.datetime.now().isoformat(), basis, json.dumps(top), about))
            con.commit(); done += 1
            log.info("fundamentals %s (%s): %d values", sym, basis, len(rows))
        except Exception as e:
            log.warning("fundamentals failed for %s: %s", sym, e)
            fails += 1
            if fails >= FUND_MAX_CONSECUTIVE_FAILS:
                log.warning("too many consecutive fundamentals failures; keeping stored fundamentals")
                break
    con.execute("INSERT INTO runs VALUES (?,?,?)", (dt.datetime.now().isoformat(), "fundamentals", str(done)))
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="tech", choices=list(UNIVERSES))
    ap.add_argument("--prices-only", action="store_true", help="intraday snapshot: refresh prices + metrics, skip fundamentals")
    ap.add_argument("--full-prices", action="store_true")
    ap.add_argument("--force-fund", action="store_true")
    ap.add_argument("--skip-fund", action="store_true")
    a = ap.parse_args()
    con = db()
    syms = load_universe(con, a.universe)
    tick = {s: f"{s}.NS" for s in syms}; tick.update({k: k for k in INDICES})
    update_prices(con, tick, full=a.full_prices)
    if not (a.skip_fund or a.prices_only):
        update_fundamentals(con, syms, force=a.force_fund)
    sys.path.insert(0, BASE)
    from analytics import build_metrics
    m = build_metrics(con, syms)
    m.to_parquet(os.path.join(DATA, "metrics.parquet"))
    con.execute("INSERT INTO runs VALUES (?,?,?)", (dt.datetime.now().isoformat(), "metrics", str(len(m))))
    con.commit()
    log.info("done: metrics for %d stocks", len(m))
    try:   # Beemer Picks: rules-based belts, one snapshot per run (stored in market.db → ships with published data)
        import picks
        picks.run(con, DATA, m)
        log.info("done: Beemer Picks refreshed")
    except Exception as e:  # never fail the data run over the picks
        log.warning("picks failed: %s", e)


if __name__ == "__main__":
    main()
