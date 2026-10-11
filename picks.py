"""Beemer Picks — transparent, rules-based data signals (NOT recommendations, NOT predictions).

Three "belts", recomputed after every update_data.py run and stored in market.db (table `picks`, one
snapshot per run) plus data/picks.parquet + data/picks_meta.json for convenience:

1. SHORT-TERM MOMENTUM (1–3 months) — who has been beating the Nifty IT index lately, with the trend
   and volume behind them and improving quarterly results.
     Eligible : ≥ 200 trading days of history · close above its 50-day average · beat Nifty IT over 3 months
                · average daily traded value (20 days) ≥ ₹2 crore
     Score    : 35% 3-month return vs Nifty IT (percentile rank among eligible)
                15% 1-month return vs Nifty IT (rank)
                20% trend: ½ for close > 50-DMA, ½ for 50-DMA > 200-DMA
                10% volume surge: 20-day average volume ÷ 120-day average (rank)
                20% results momentum: latest quarter's YoY sales growth + YoY profit growth (rank; neutral 0.5 if unknown)

2. LONG-TERM COMPOUNDERS (5 years +) — Buffett-style quality at a sensible price.
     Eligible : ≥ 5 years of financials · profitable over the last 12 months · Buffett Score ≥ 60
                · debt/equity ≤ 1 · ≥ 3 years of price history
     Score    : 40% Buffett Score
                15% ROE consistency (share of the last 10 years with ROE > 15%)
                15% ROCE level (10-yr median; 10% → 0, 40% → full)
                15% valuation: margin of safety (−50% → 0, +30% → full) and P/E vs own 10-yr median (+50% → 0, −30% → full)
                15% earnings growth: 5-yr profit CAGR (0% → 0, 20% → full; 10-yr if 5-yr missing)

3. VOLATILE MOVERS (last 1–5 trading days) — the biggest *unusual* moves, up or down.
     Eligible : ≥ 120 trading days of history · average daily traded value (20 days) ≥ ₹1 crore
     Score    : 60% size of the 5-day move in units of the stock's own normal 5-day swing (|z|, rank)
                25% unusual volume: last-5-day average volume ÷ previous 60-day average (rank)
                15% size of the latest 1-day move in units of its own daily volatility (rank)

Scores are 0–100 (higher = stronger signal on these rules). Every chip carries a one-line reason built from
the same numbers. A simple backtest (price-only rules; fundamentals aren't available point-in-time) is
stored with the picks so the app can show an honest "how has this signal done" note.
"""
import datetime as dt, json, math, os, sqlite3
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

import analytics as A

IST = ZoneInfo("Asia/Kolkata")
RULES_VERSION = "1.0"
TOP_N = 5
BELTS = {
    "short": {"title": "Momentum", "horizon": "1–3 months",
              "blurb": "Outpacing Nifty IT, with trend and results behind it."},
    "long": {"title": "Compounders", "horizon": "5 years +",
             "blurb": "Quality businesses at sensible prices."},
    "volatile": {"title": "Movers", "horizon": "Last 5 days",
                 "blurb": "The largest unusual moves, up and down."},
}
W_SHORT = {"rs3": .35, "rs1": .15, "trend": .20, "volsurge": .10, "results": .20}
W_LONG = {"buffett": .40, "roe_consistency": .15, "roce": .15, "valuation": .15, "growth": .15}
W_VOL = {"move5_z": .60, "volume": .25, "move1_z": .15}


# ---------------- panel helpers ----------------
def load_panel(con, syms):
    """Wide adj-close and volume frames (dates × symbols) using the cleaned price series."""
    px, vol, cl = {}, {}, {}
    for s in syms:
        p = A.prices(con, s)
        if p.empty:
            continue
        px[s], vol[s], cl[s] = p["adj_close"], p["volume"], p["close"]
    P, V, Cl = pd.DataFrame(px), pd.DataFrame(vol), pd.DataFrame(cl)
    idx = A.prices(con, "^CNXIT")["adj_close"]
    cal = P.index.union(idx.index)
    P = P.reindex(cal).ffill(limit=5); Cl = Cl.reindex(cal).ffill(limit=5); V = V.reindex(cal).fillna(0)
    I = idx.reindex(cal).ffill(limit=5)
    # rows where nobody traded (index-only holidays) add noise
    keep = P.notna().sum(axis=1) > 0
    return P[keep], V[keep], Cl[keep], I[keep]


def features(P, V, Cl, I):
    """All price features, vectorised (dates × symbols)."""
    n_obs = P.notna().cumsum()
    lr = np.log(P).diff()
    f = {
        "n_obs": n_obs,
        "r1": P.pct_change(1, fill_method=None), "r5": P.pct_change(5, fill_method=None),
        "r21": P.pct_change(21, fill_method=None), "r63": P.pct_change(63, fill_method=None),
        "r252": P.pct_change(252, fill_method=None),
        "dma50": P.rolling(50, min_periods=45).mean(), "dma200": P.rolling(200, min_periods=180).mean(),
        "vol20": V.rolling(20, min_periods=15).mean(), "vol120": V.rolling(120, min_periods=100).mean(),
        "vol5": V.rolling(5).mean(), "vol60_prev": V.shift(5).rolling(60, min_periods=50).mean(),
        "val20": (Cl * V).rolling(20, min_periods=15).mean() / 1e7,          # ₹ crore per day
        "sig_d": lr.rolling(252, min_periods=100).std(),
    }
    f["i21"] = I.pct_change(21, fill_method=None); f["i63"] = I.pct_change(63, fill_method=None)
    f["fwd21"] = P.shift(-21) / P - 1; f["fwd63"] = P.shift(-63) / P - 1
    return f


def _row(f, key, d):
    x = f[key]
    return x.loc[d] if isinstance(x, pd.DataFrame) else x.loc[d]


def _rank(s):
    return s.rank(pct=True) if len(s.dropna()) > 1 else s.notna().astype(float)


def short_scores(f, d, results=None):
    """Momentum scores at date d. Returns DataFrame of eligible symbols with components."""
    g = pd.DataFrame({k: _row(f, k, d) for k in ["n_obs", "r1", "r21", "r63", "dma50", "dma200", "vol20", "vol120", "val20"]})
    g["close"] = f["_P"].loc[d]
    g["rs3"] = g.r63 - f["i63"].loc[d]; g["rs1"] = g.r21 - f["i21"].loc[d]
    g["volsurge"] = g.vol20 / g.vol120
    el = g[(g.n_obs >= 200) & (g.close > g.dma50) & (g.rs3 > 0) & (g.val20 >= 2)].copy()
    if el.empty:
        return el
    el["trend"] = 0.5 * (el.close > el.dma50) + 0.5 * (el.dma50 > el.dma200).fillna(False)
    comp = {"rs3": _rank(el.rs3), "rs1": _rank(el.rs1), "trend": el.trend, "volsurge": _rank(el.volsurge).fillna(0.5)}
    w = dict(W_SHORT)
    if results is not None:
        rr = results.reindex(el.index)
        el["sales_yoy"], el["profit_yoy"], el["qtr"] = rr.get("sales_yoy"), rr.get("profit_yoy"), rr.get("qtr")
        mix = 0.5 * el.sales_yoy.clip(-0.5, 1) + 0.5 * el.profit_yoy.clip(-1, 2)
        comp["results"] = _rank(mix).fillna(0.5)
    else:      # backtest: no point-in-time results, renormalise
        w.pop("results")
    tot = sum(w.values())
    el["score"] = 100 * sum(w[k] * comp[k] for k in w) / tot
    for k in comp:
        el[f"c_{k}"] = comp[k]
    return el.sort_values("score", ascending=False)


def vol_scores(f, d):
    g = pd.DataFrame({k: _row(f, k, d) for k in ["n_obs", "r1", "r5", "vol5", "vol60_prev", "val20", "sig_d"]})
    el = g[(g.n_obs >= 120) & (g.val20 >= 1) & g.sig_d.gt(0) & g.r5.notna()].copy()
    if el.empty:
        return el
    el["z5"] = el.r5 / (el.sig_d * math.sqrt(5)); el["z1"] = el.r1 / el.sig_d
    el["volx"] = el.vol5 / el.vol60_prev
    el["score"] = 100 * (W_VOL["move5_z"] * _rank(el.z5.abs()) + W_VOL["volume"] * _rank(el.volx).fillna(0.5)
                         + W_VOL["move1_z"] * _rank(el.z1.abs()))
    return el.sort_values("score", ascending=False)


def _lin(x, lo, hi):
    return A._lin(x, lo, hi)


def long_scores(m):
    el = m[(m.get("fin_years", pd.Series(0, index=m.index)).fillna(0) >= 5) & (m.profitable_ttm.fillna(False))
           & (m.buffett_score.fillna(0) >= 60) & (m.debt_to_equity.fillna(0) <= 1) & (m.history_years >= 3)].copy()
    rows = []
    for r in el.itertuples():
        roe_c = (r.roe_years_above_15 / r.roe_years_checked) if getattr(r, "roe_years_checked", 0) else None
        roce = _lin(getattr(r, "roce_median_10y", None), 0.10, 0.40)
        mos = _lin(r.margin_of_safety, -0.5, 0.3); pvh = r.pe_vs_history
        pv = (1 - _lin(pvh, -0.3, 0.5)) if pvh is not None and not pd.isna(pvh) else None
        val = np.nanmean([x for x in [mos, pv] if x is not None]) if any(x is not None for x in [mos, pv]) else 0.3
        g = r.profit_cagr_5y if not pd.isna(r.profit_cagr_5y) else getattr(r, "profit_cagr_10y", None)
        gr = _lin(g, 0, 0.20)
        comp = {"buffett": r.buffett_score / 100, "roe_consistency": roe_c if roe_c is not None else 0.5,
                "roce": roce if roce is not None else 0.5, "valuation": val, "growth": gr if gr is not None else 0.3}
        rows.append({"symbol": r.symbol, "score": 100 * sum(W_LONG[k] * comp[k] for k in W_LONG), "g": g,
                     **{f"c_{k}": v for k, v in comp.items()}})
    return pd.DataFrame(rows).set_index("symbol").sort_values("score", ascending=False) if rows else pd.DataFrame()


# ---------------- quarterly results ----------------
def latest_results(con, syms):
    q = pd.read_sql("SELECT symbol, item, period, value FROM fundamentals WHERE section='quarters' AND item IN ('Sales','Revenue','Net Profit')", con)
    out = {}
    for s, g in q.groupby("symbol"):
        if s not in syms:
            continue
        w = g.pivot_table(index="period", columns="item", values="value", aggfunc="first")
        w.index = [A._pdate(p) for p in w.index]; w = w[w.index.notna()].sort_index()
        if len(w) < 5:
            continue
        sales = w.get("Sales", w.get("Revenue")); np_ = w.get("Net Profit")
        last = w.index[-1]; prev = last - pd.DateOffset(years=1) + pd.offsets.MonthEnd(0)
        if prev not in w.index:
            continue
        def yoy(s_):
            if s_ is None: return None
            a, b = s_.get(prev), s_.get(last)
            if a is None or b is None or pd.isna(a) or pd.isna(b) or a <= 0: return None
            return b / a - 1
        out[s] = {"sales_yoy": yoy(sales), "profit_yoy": yoy(np_), "qtr": last.strftime("%b %Y"),
                  "profit_turnaround": bool(np_ is not None and np_.get(prev, 0) <= 0 < np_.get(last, 0))}
    return pd.DataFrame(out).T


# ---------------- reasons (plain English) ----------------
def _p(x, d=1):
    return f"{x*100:+.{d}f}%"


def reason_short(r):
    bits = [f"+{r.rs3*100:.0f} pts vs Nifty IT, 3M"]
    if r.close > r.dma50 and pd.notna(r.dma200) and r.dma50 > r.dma200:
        bits.append("Above 50- and 200-day averages")
    elif r.close > r.dma50:
        bits.append("Above 50-day average")
    q = pd.Timestamp(r.qtr).strftime("%b-%y") + " qtr" if pd.notna(r.get("qtr")) else ""
    if pd.notna(r.get("profit_yoy")) and r.profit_yoy > 0.1:
        bits.append(f"{q} profit {_p(r.profit_yoy, 0)}")
    elif pd.notna(r.get("sales_yoy")) and r.sales_yoy > 0.1:
        bits.append(f"{q} sales {_p(r.sales_yoy, 0)}")
    if pd.notna(r.volsurge) and r.volsurge > 1.3:
        bits.append(f"Volume {r.volsurge:.1f}×")
    return " · ".join(bits[:3])


def reason_long(r, m):
    bits = [f"Buffett Score {m.buffett_score:.0f}"]
    if m.get("roe_years_checked"):
        bits.append(f"ROE 15%+ in {int(m.roe_years_above_15)}/{int(m.roe_years_checked)} yrs")
    pv = m.get("pe_vs_history")
    if pv is not None and not pd.isna(pv):
        bits.append(f"P/E {abs(pv)*100:.0f}% {'below' if pv < 0 else 'above'} 10-yr median")
    elif r.g is not None and not pd.isna(r.g):
        bits.append(f"Profit {_p(r.g, 0)}/yr, 5 yrs")
    return " · ".join(bits)


def reason_vol(r):
    s = f"{_p(r.r5)} in 5 days · {abs(r.z5):.1f}× normal swing"
    if pd.notna(r.volx) and r.volx > 1.5:
        s += f" · Volume {r.volx:.1f}×"
    elif abs(r.z1) > 2:
        s += f" · {_p(r.r1)} last session"
    return s


# ---------------- backtest (price-only, honest) ----------------
def backtest(f, P, start="2008-01-01"):
    """Month-end rebalances: forward 1m/3m return of the top-5 vs the median eligible stock.
    Universe = today's list (survivorship bias: favours the backtest a little)."""
    me = P.index.to_series().groupby([P.index.year, P.index.month]).last()
    me = [d for d in me if d >= pd.Timestamp(start) and d <= P.index[-64]]
    res_s, res_v = [], []
    for d in me:
        univ = f["n_obs"].loc[d] >= 200
        if univ.sum() < 15:
            continue
        fw1, fw3 = f["fwd21"].loc[d][univ], f["fwd63"].loc[d][univ]
        s = short_scores(f, d)
        if len(s) >= TOP_N:
            top = s.index[:TOP_N]
            res_s.append({"date": d, "top1m": fw1[top].mean(), "med1m": fw1.median(), "top3m": fw3[top].mean(), "med3m": fw3.median()})
        v = vol_scores(f, d)
        if len(v) >= TOP_N:
            top = v.index[:TOP_N]
            up = [x for x in top if v.loc[x, "r5"] > 0]; dn = [x for x in top if v.loc[x, "r5"] < 0]
            res_v.append({"date": d, "up1m": fw1.reindex(up).mean() if up else np.nan, "dn1m": fw1.reindex(dn).mean() if dn else np.nan,
                          "top1m": fw1.reindex(top).mean(), "med1m": fw1.median()})
    out = {}
    if res_s:
        b = pd.DataFrame(res_s); ex1 = b.top1m - b.med1m; ex3 = b.top3m - b.med3m
        out["short"] = {"months": len(b), "from": b.date.min().strftime("%b %Y"), "to": b.date.max().strftime("%b %Y"),
                        "hit_rate_1m": float((ex1 > 0).mean()), "median_excess_1m": float(ex1.median()), "mean_excess_1m": float(ex1.mean()),
                        "hit_rate_3m": float((ex3 > 0).mean()), "median_excess_3m": float(ex3.median()),
                        "top_median_1m": float(b.top1m.median()), "univ_median_1m": float(b.med1m.median()),
                        "rules": "price-only (results momentum excluded: no point-in-time quarterly data)"}
    if res_v:
        b = pd.DataFrame(res_v)
        out["volatile"] = {"months": len(b), "from": b.date.min().strftime("%b %Y"), "to": b.date.max().strftime("%b %Y"),
                           "after_up_1m_excess": float((b.up1m - b.med1m).median()), "after_down_1m_excess": float((b.dn1m - b.med1m).median()),
                           "hit_rate_1m": float(((b.top1m - b.med1m) > 0).mean())}
    out["long"] = {"note": "not backtested — the Buffett Score uses today's fundamentals, and testing it on past prices would leak future information"}
    return out


# ---------------- build + persist ----------------
def _spark(series, n):
    s = series.dropna().tail(n)
    return [round(float(x), 2) for x in s.values]


def build_picks(con, m, do_backtest=True):
    syms = list(m.symbol)
    P, V, Cl, I = load_panel(con, syms)
    f = features(P, V, Cl, I); f["_P"] = Cl
    d = P.index[-1]
    mi = m.set_index("symbol")
    rows = []

    def chip(belt, rank, sym, score, reason, extra, spark_n, spark_step=1):
        r = mi.loc[sym]
        sp = P[sym].dropna().iloc[::-1][::spark_step].iloc[::-1]
        rows.append({"belt": belt, "rank": rank, "symbol": sym, "name": r["name"], "subsector": r["subsector"],
                     "price": float(Cl[sym].dropna().iloc[-1]), "chg_1d": float(f["r1"].loc[d, sym]) if pd.notna(f["r1"].loc[d, sym]) else None,
                     "score": round(float(score), 1), "buffett_score": float(r["buffett_score"]) if pd.notna(r["buffett_score"]) else None,
                     "reason": reason, "spark": json.dumps(_spark(sp, spark_n)), **extra})

    res = latest_results(con, syms)
    s = short_scores(f, d, res if not res.empty else None)
    for i, (sym, r) in enumerate(s.head(TOP_N).iterrows(), 1):
        chip("short", i, sym, r.score, reason_short(r), {"stat_label": "3M vs NIFTY IT", "stat": float(r.rs3), "direction": "up"}, 63)
    lg = long_scores(m)
    for i, (sym, r) in enumerate(lg.head(TOP_N).iterrows(), 1):
        r1y = f["r252"].loc[d, sym]
        chip("long", i, sym, r.score, reason_long(r, mi.loc[sym]),
             {"stat_label": "1Y RETURN", "stat": float(r1y) if pd.notna(r1y) else None, "direction": "up"}, 52, spark_step=5)
    v = vol_scores(f, d)
    for i, (sym, r) in enumerate(v.head(TOP_N).iterrows(), 1):
        chip("volatile", i, sym, r.score, reason_vol(r), {"stat_label": "5-DAY MOVE", "stat": float(r.r5), "direction": "up" if r.r5 > 0 else "down"}, 30)
    picks = pd.DataFrame(rows)
    meta = {"generated_at": dt.datetime.now(IST).isoformat(timespec="seconds"), "as_of": d.date().isoformat(),
            "rules_version": RULES_VERSION, "weights": {"short": W_SHORT, "long": W_LONG, "volatile": W_VOL},
            "eligible": {"short": int(len(s)), "long": int(len(lg)), "volatile": int(len(v)), "universe": len(syms)}}
    if do_backtest:
        try:
            meta["backtest"] = backtest(f, P)
        except Exception as e:  # never block the pipeline on the backtest
            meta["backtest"] = {"error": str(e)}
    return picks, meta


def _ensure_table(con):
    con.execute("""CREATE TABLE IF NOT EXISTS picks(run_at TEXT, as_of TEXT, belt TEXT, rank INTEGER, symbol TEXT,
                   score REAL, reason TEXT, payload TEXT, PRIMARY KEY(run_at, belt, rank))""")
    con.execute("CREATE TABLE IF NOT EXISTS picks_meta(run_at TEXT PRIMARY KEY, meta TEXT)")


def save_picks(con, picks, meta, data_dir):
    """Persist one snapshot. Also records which symbols entered/left each belt vs the last snapshot with an
    earlier as_of date (so the belt can animate arrivals and departures)."""
    _ensure_table(con)
    changes = {}
    prev_run = con.execute("SELECT MAX(run_at) FROM picks WHERE as_of < ?", (meta["as_of"],)).fetchone()[0]
    for belt in BELTS:
        now = list(picks[picks.belt == belt].symbol)
        before = [r[0] for r in con.execute("SELECT symbol FROM picks WHERE run_at=? AND belt=? ORDER BY rank", (prev_run, belt))] if prev_run else []
        changes[belt] = {"entered": [x for x in now if x not in before] if before else [], "dropped": [x for x in before if x not in now],
                         "previous": before}
    meta["changes"] = changes
    run_at = meta["generated_at"]
    for r in picks.to_dict("records"):
        con.execute("INSERT OR REPLACE INTO picks VALUES (?,?,?,?,?,?,?,?)",
                    (run_at, meta["as_of"], r["belt"], int(r["rank"]), r["symbol"], r["score"], r["reason"], json.dumps(r, default=float)))
    con.execute("INSERT OR REPLACE INTO picks_meta VALUES (?,?)", (run_at, json.dumps(meta)))
    con.commit()
    picks.to_parquet(os.path.join(data_dir, "picks.parquet"))
    with open(os.path.join(data_dir, "picks_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    return meta


def load_latest(con):
    """(picks DataFrame, meta dict) from the newest snapshot in the db, or (empty, {})."""
    try:
        run = con.execute("SELECT MAX(run_at) FROM picks").fetchone()[0]
    except sqlite3.OperationalError:
        return pd.DataFrame(), {}
    if not run:
        return pd.DataFrame(), {}
    rows = [json.loads(r[0]) for r in con.execute("SELECT payload FROM picks WHERE run_at=? ORDER BY belt, rank", (run,))]
    meta = json.loads(con.execute("SELECT meta FROM picks_meta WHERE run_at=?", (run,)).fetchone()[0])
    return pd.DataFrame(rows), meta


def run(con, data_dir, m=None):
    if m is None:
        m = pd.read_parquet(os.path.join(data_dir, "metrics.parquet"))
    picks, meta = build_picks(con, m)
    return picks, save_picks(con, picks, meta, data_dir)


if __name__ == "__main__":   # python picks.py  → rebuild picks from the current db + metrics
    import sys
    base = os.path.dirname(os.path.abspath(__file__)); data = os.path.join(base, "data")
    c = sqlite3.connect(os.path.join(data, "market.db"))
    pk, mt = run(c, data)
    for b in BELTS:
        print(f"\n== {BELTS[b]['title']} ==")
        for r in pk[pk.belt == b].itertuples():
            print(f"{r.rank}. {r.symbol:<11} {r.score:5.1f}  ₹{r.price:,.2f}  {r.reason}")
    print("\nbacktest:", json.dumps(mt.get("backtest"), indent=1))
    print("changes:", json.dumps(mt.get("changes")))
