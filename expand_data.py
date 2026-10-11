#!/usr/bin/env python3
"""Beemer extended datasets: NSE public files and filings for every tech name in universe_all.

Usage:
  python expand_data.py                      # all steps, incremental (what update_data.py runs after metrics)
  python expand_data.py --steps deals,delivery
  python expand_data.py --steps feeds --force # refetch every company feed now
  BEEMER_FEED_BUDGET=150 python expand_data.py  # cap per-feed company calls (CI keeps runs short)
  BEEMER_ARCHIVE_MAX_DAYS=400 python expand_data.py  # cap archive days per run (a backfill spreads over runs)

Steps
  universe   rebuild universe_all (EQUITY_L + index lists + NSE industry tags)
  delivery   NSE sec_bhavdata_full archive: OHLC, VWAP, trades, delivery %  (2020 ->)
  index_eod  NSE ind_close_all archive: every NSE index with P/E, P/B, yield (2015 ->)
  deals      NSE bulk + block deals, market-wide (2023 ->)
  feeds      per company: corporate actions, board meetings, shareholding, insider trades, deals, XBRL results
  audit      cross-check Yahoo adjusted prices against NSE split / bonus records
  enrich     copy the latest of the above into company_metrics for the API (no network)
Every step degrades gracefully: when NSE refuses the network, stored data is kept and the run goes on.
"""
import argparse, datetime as dt, json, logging, os, sqlite3, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from sources import nse_archives, nse_corp, store, universe  # noqa: E402

DB = os.path.join(BASE, "data", "market.db")
log = logging.getLogger("expand")
STEPS = ["universe", "delivery", "index_eod", "deals", "feeds", "audit", "enrich"]


def _factor(kind, ratio):
    """Price factor implied by a split ('10:2' -> 5) or bonus ('1:1' -> 2: one new share per one held)."""
    try:
        a, b = (float(x) for x in ratio.split(":"))
    except (AttributeError, ValueError):
        return None
    if kind == "split":
        return a / b if b else None
    return (a + b) / b if b else None


def audit(con):
    """Check Yahoo's adjusted prices against NSE's split and bonus records: on an ex-date the adjusted price
    should not jump by anything like the split factor. Results go to price_audit; analytics.clean_prices
    already repairs large unexplained one-day moves, so this is a cross-check, not a rewrite."""
    acts = con.execute("SELECT symbol, ex_date, kind, ratio FROM corp_actions WHERE kind IN ('split','bonus') AND ratio IS NOT NULL").fetchall()
    n = bad = 0
    for sym, ex, kind, ratio in acts:
        f = _factor(kind, ratio)
        if not f or f <= 1.05:
            continue
        px = con.execute("""SELECT date, adj_close FROM prices WHERE symbol=? AND date BETWEEN date(?, '-7 days') AND date(?, '+3 days')
                            ORDER BY date""", (sym, ex, ex)).fetchall()
        before = [p for d, p in px if d < ex]
        after = [p for d, p in px if d >= ex]
        if not before or not after or not before[-1]:
            status, move = "no_prices", None
        else:
            move = after[0] / before[-1] - 1
            status = "unadjusted" if move < (1 / f - 1) * 0.6 else "ok"
        bad += status == "unadjusted"
        con.execute("INSERT OR REPLACE INTO price_audit VALUES (?,?,?,?,?,?,?)", (sym, ex, kind, ratio, f, move, status))
        n += 1
    con.commit()
    store.log_run(con, "audit", "ok", n, f"{bad} ex-dates look unadjusted in Yahoo prices")
    log.info("audit: %d split/bonus ex-dates checked, %d look unadjusted", n, bad)
    return n


def enrich(con):
    """Add ownership, delivery and dividend fields to company_metrics payloads (reads local tables only)."""
    try:
        rows = con.execute("SELECT symbol, payload FROM company_metrics").fetchall()
    except sqlite3.OperationalError:
        return 0
    one = lambda q, *a: con.execute(q, a).fetchall()
    n = 0
    for sym, raw in rows:
        p = json.loads(raw)
        sh = one("""SELECT period, promoter, fii, dii, mf, public, pledge_flag FROM shareholding WHERE symbol=?
                    AND substr(period, 6) IN ('03-31', '06-30', '09-30', '12-31') ORDER BY period DESC LIMIT 5""", sym)
        if sh:
            p["own_period"], p["own_promoter"], p["own_fii"], p["own_dii"], p["own_mf"] = sh[0][0], sh[0][1], sh[0][2], sh[0][3], sh[0][4]
            p["own_pledge"] = sh[0][6]
            if len(sh) >= 5 and sh[4][1] is not None and sh[0][1] is not None:
                p["own_promoter_chg_1y"] = round(sh[0][1] - sh[4][1], 2)
            fii_prev = next((r[2] for r in sh[1:] if r[2] is not None), None)
            if fii_prev is not None and sh[0][2] is not None:
                p["own_fii_chg_q"] = round(sh[0][2] - fii_prev, 2)
        d = one("SELECT AVG(deliv_pct), COUNT(*) FROM (SELECT deliv_pct FROM delivery WHERE symbol=? AND series='EQ' ORDER BY date DESC LIMIT 20)", sym)
        if d and d[0][1]:
            p["deliv_pct_20d"] = round(d[0][0], 1) if d[0][0] is not None else None
        since = (dt.date.today() - dt.timedelta(days=365)).isoformat()
        dv = one("SELECT SUM(amount), COUNT(*) FROM corp_actions WHERE symbol=? AND kind LIKE 'dividend%' AND ex_date>=?", sym, since)
        if dv and dv[0][1]:
            p["div_ttm"] = round(dv[0][0], 2) if dv[0][0] else None
            if p.get("div_ttm") and p.get("price"):
                p["div_yield_nse"] = round(p["div_ttm"] / p["price"], 4)
        nb = one("SELECT MIN(meeting_date) FROM board_meetings WHERE symbol=? AND meeting_date>=?", sym, dt.date.today().isoformat())
        p["next_board_meeting"] = nb[0][0] if nb else None
        ins = one("""SELECT SUM(CASE WHEN txn_type='Buy' THEN value ELSE 0 END), SUM(CASE WHEN txn_type='Sell' THEN value ELSE 0 END)
                     FROM insider_trades WHERE symbol=? AND COALESCE(to_date, disclosed_at)>=?
                     AND mode IN ('Market Purchase', 'Market Sale')""",
                  sym, (dt.date.today() - dt.timedelta(days=182)).isoformat())
        if ins and (ins[0][0] or ins[0][1]):
            p["insider_net_6m_cr"] = round(((ins[0][0] or 0) - (ins[0][1] or 0)) / 1e7, 2)
        con.execute("UPDATE company_metrics SET payload=? WHERE symbol=?", (json.dumps(p, allow_nan=False), sym))
        n += 1
    con.commit()
    log.info("enrich: %d companies", n)
    return n


def run(con, core=(), steps=None, force=False, budget=None):
    store.ensure(con)
    steps = steps or STEPS
    budget = budget if budget is not None else (int(os.environ["BEEMER_FEED_BUDGET"]) if os.environ.get("BEEMER_FEED_BUDGET") else None)
    if not core:
        core = [r[0] for r in con.execute("SELECT symbol FROM universe")]
    for step in steps:
        t0 = dt.datetime.now()
        try:
            if step == "universe":
                universe.build(con, os.path.join(BASE, "data", "universe_tech.csv"))
            elif step in ("delivery", "index_eod"):
                cap = os.environ.get("BEEMER_ARCHIVE_MAX_DAYS")
                nse_archives.update(con, step, max_days=int(cap) if cap else None)
            elif step == "deals":
                nse_corp.deals(con)
            elif step == "feeds":
                syms = [r[0] for r in con.execute("SELECT symbol FROM universe_all ORDER BY tier='core' DESC, symbol")]
                nse_corp.update_companies(con, syms, core=set(core), force=force, budget=budget)
            elif step == "audit":
                audit(con)
            elif step == "enrich":
                enrich(con)
        except Exception as e:  # one dataset never stops the others
            log.warning("%s failed: %s", step, e)
            store.log_run(con, step, "failed", 0, str(e)[:300])
        log.info("step %s took %ss", step, (dt.datetime.now() - t0).seconds)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default=",".join(STEPS))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--budget", type=int)
    a = ap.parse_args()
    con = sqlite3.connect(DB, timeout=60)
    run(con, steps=[s.strip() for s in a.steps.split(",") if s.strip()], force=a.force, budget=a.budget)


if __name__ == "__main__":
    main()
