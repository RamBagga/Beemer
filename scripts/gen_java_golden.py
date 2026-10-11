#!/usr/bin/env python3
"""Golden outputs for the Java port of request-time analytics.

Writes backend/src/test/resources/golden/*.json from analytics.py and the
formatters in app/beemer.py. Re-run after those functions change:

    python scripts/gen_java_golden.py
"""
import json, math, os, sqlite3, sys
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import analytics as A

OUT = os.path.join(ROOT, "backend", "src", "test", "resources", "golden")


def indian(x, d=0):
    neg = x < 0; x = abs(x)
    s = f"{x:.{d}f}"; ip, _, fp = s.partition(".")
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        ip = ",".join(parts + [tail])
    return ("-" if neg else "") + ip + (("." + fp) if fp else "")


def pct(x, d=1, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x*100:+.{d}f}%" if sign else f"{x*100:.{d}f}%"


def num(x, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x:,.{d}f}"


def inr(x, d=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return "₹" + indian(x, d)


def crore(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "–"
    sign = "−" if x < 0 else ""; x = abs(x)
    if x >= 1e5: return f"{sign}₹{x/1e5:,.2f} lakh cr"
    return f"{sign}₹{indian(x)} cr"


def lakh(x):
    if x >= 1e7: return f"₹{x/1e7:,.2f} crore"
    if x >= 1e5: return f"₹{x/1e5:,.2f} lakh"
    return inr(x)


def dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, allow_nan=False)
    print("wrote", path)


def series_blob(s):
    return {"dates": [d.strftime("%Y-%m-%d") for d in s.index], "values": [float(v) for v in s.values]}


def main():
    # --- real Nifty IT sample (request-time math) ---
    db = os.path.join(ROOT, "data", "market.db")
    if not os.path.exists(db):
        print("skip nifty sample: no market.db")
    else:
        con = sqlite3.connect(db)
        it = A.prices(con, "^CNXIT")["adj_close"]
        cagr = {}
        for y in (1, 3, 5, 10, 20):
            v = A.cagr_from_series(it, y)
            cagr[str(y)] = None if v is None else float(v)
        cagr["max"] = float(A.cagr_from_series(it, "max"))
        dd = A.drawdowns(it)
        ep = A.crash_episodes(it, -0.2)
        crashes = []
        for r in ep.itertuples():
            crashes.append({
                "peak": r.peak_date.isoformat(), "trough": r.trough_date.isoformat(),
                "fall": float(r.fall_pct), "monthsDown": float(r.months_to_bottom),
                "recovery": None if r.recovery_date is None or (isinstance(r.recovery_date, float) and math.isnan(r.recovery_date)) else r.recovery_date.isoformat(),
                "monthsRecover": None if r.months_to_recover is None or (isinstance(r.months_to_recover, float) and math.isnan(r.months_to_recover)) else float(r.months_to_recover),
            })
        sip = A.sip(it, 10000, "2015-01-01")
        sub = it[it.index >= "2015-01-01"]
        buys = sub.groupby([sub.index.year, sub.index.month]).head(1)
        path = pd.DataFrame({"inv": 10000 * np.arange(1, len(buys) + 1), "val": (10000 / buys).cumsum() * buys.values}, index=buys.index) / 1e5
        s_m = it.resample("ME").last()
        rolling = {}
        for yrs in (1, 3, 5, 10):
            r = ((s_m / s_m.shift(12 * yrs)) ** (1 / yrs) - 1).dropna()
            rolling[str(yrs)] = {
                "n": int(len(r)), "lost": float((r < 0).mean()), "beat10": float((r > 0.10).mean()),
                "worst": float(r.min()), "median": float(r.median()), "last": float(r.iloc[-1]),
                "lastDate": r.index[-1].strftime("%Y-%m-%d"),
            }
        dump("nifty_it.json", {
            **series_blob(it),
            "cagr": cagr,
            "ddMin": float(dd.min()), "ddMinDate": dd.idxmin().strftime("%Y-%m-%d"), "ddLast": float(dd.iloc[-1]),
            "crashes": crashes,
            "sip": {
                "monthly": 10000, "start": "2015-01-01",
                "invested": float(sip["invested"]), "value": float(sip["value"]), "months": int(sip["months"]),
                "xirr": float(sip["xirr"]), "firstBuy": sip["start"].isoformat(),
                "pathFirst": {"date": path.index[0].strftime("%Y-%m-%d"), "inv": float(path.inv.iloc[0]), "val": float(path.val.iloc[0])},
                "pathLast": {"date": path.index[-1].strftime("%Y-%m-%d"), "inv": float(path.inv.iloc[-1]), "val": float(path.val.iloc[-1])},
                "lump": float(sip["invested"] * sub.iloc[-1] / sub.iloc[0]),
            },
            "rolling": rolling,
            "monthEnd": {"n": int(len(s_m)), "firstDate": s_m.index[0].strftime("%Y-%m-%d"), "first": float(s_m.iloc[0]),
                         "lastDate": s_m.index[-1].strftime("%Y-%m-%d"), "last": float(s_m.iloc[-1])},
        })
        con.close()

    # --- clean_prices ---
    idx = pd.bdate_range("2015-01-05", periods=40)
    close = np.full(40, 100.0)
    adj = close.copy()
    adj[10] = 160.0
    adj[11] = 100.0
    adj[30:] = 150.0
    close = adj.copy()
    vol = np.full(40, 1000.0)
    vol[30] = 8000.0  # not enough to count as a real move (threshold is 4x the rolling median)
    df = pd.DataFrame({"close": close, "adj_close": adj, "volume": vol}, index=idx)
    mkt = pd.Series(0.01, index=idx)
    mkt.iloc[30] = 0.0
    cleaned = A.clean_prices(df, mkt)
    idx2 = pd.bdate_range("2009-06-01", periods=25)
    adj2 = np.full(25, 80.0)
    adj2[18:] = 120.0
    vol2 = np.full(25, 500.0)
    df2 = pd.DataFrame({"close": adj2.copy(), "adj_close": adj2, "volume": vol2}, index=idx2)
    mkt2 = pd.Series(0.0, index=idx2)
    cleaned2 = A.clean_prices(df2, mkt2)
    dump("clean_prices.json", {
        "dates": [d.strftime("%Y-%m-%d") for d in idx],
        "close": [float(v) for v in close],
        "adj": [float(v) for v in adj],
        "volume": [float(v) for v in vol],
        "marketReturn": [float(v) for v in mkt.values],
        "expectedDates": [d.strftime("%Y-%m-%d") for d in cleaned.index],
        "expectedAdj": [float(v) for v in cleaned.adj_close.values],
        "expectedClose": [float(v) for v in cleaned.close.values],
        "notes": cleaned.attrs.get("clean_notes", []),
        "rescale": {
            "dates": [d.strftime("%Y-%m-%d") for d in idx2],
            "close": [float(v) for v in adj2],
            "adj": [float(v) for v in adj2],
            "volume": [float(v) for v in vol2],
            "marketReturn": [float(v) for v in mkt2.values],
            "expectedDates": [d.strftime("%Y-%m-%d") for d in cleaned2.index],
            "expectedAdj": [float(v) for v in cleaned2.adj_close.values],
            "notes": cleaned2.attrs.get("clean_notes", []),
        },
    })

    # --- formatters (verbatim copies of app/beemer.py) ---
    cases = []
    samples = [
        ("pct", (0.10089715228485563, 1, False)),
        ("pct", (-0.0362, 2, False)),
        ("pct", (0.0362, 2, True)),
        ("pct", (-0.1998594564511884, 1, False)),
        ("pct", (0.0, 0, False)),
        ("pct", (None, 1, False)),
        ("num", (13.30520070841352, 1)),
        ("num", (1023.4, 0)),
        ("num", (None, 1)),
        ("inr", (1023.4, 0)),
        ("inr", (999.4, 2)),
        ("inr", (1234567.8, 0)),
        ("inr", (-2500, 0)),
        ("crore", (184582.0,)),
        ("crore", (850.0,)),
        ("crore", (250000.0,)),
        ("crore", (-120.5,)),
        ("crore", (None,)),
        ("lakh", (1420000,)),
        ("lakh", (250000,)),
        ("lakh", (999,)),
        ("indian", (12345678.9, 2)),
        ("indian", (100, 0)),
    ]
    fns = {"pct": pct, "num": num, "inr": inr, "crore": crore, "lakh": lakh, "indian": indian}
    for name, args in samples:
        cases.append({"fn": name, "args": [None if a is None else a for a in args], "out": fns[name](*args)})
    dump("format.json", cases)

    # --- screener filters ---
    rows = [
        {"symbol": "A", "subsector": "IT services", "buffett_score": 80, "pe": 20, "debt_to_equity": 0.1, "roe_median_10y": 0.25, "profitable_ttm": True, "young_listing": False, "margin_of_safety": 0.1},
        {"symbol": "B", "subsector": "Fintech", "buffett_score": 55, "pe": None, "debt_to_equity": 0.2, "roe_median_10y": 0.05, "profitable_ttm": False, "young_listing": True, "margin_of_safety": -0.2},
        {"symbol": "C", "subsector": "IT services", "buffett_score": None, "pe": 40, "debt_to_equity": None, "roe_median_10y": None, "profitable_ttm": True, "young_listing": False, "margin_of_safety": 0.4},
        {"symbol": "D", "subsector": "AI & data", "buffett_score": 70, "pe": 180, "debt_to_equity": 1.2, "roe_median_10y": 0.18, "profitable_ttm": True, "young_listing": False, "margin_of_safety": 0.01},
        {"symbol": "E", "subsector": "Fintech", "buffett_score": 40, "pe": 12, "debt_to_equity": 3.0, "roe_median_10y": 0.02, "profitable_ttm": True, "young_listing": True, "margin_of_safety": None},
    ]
    def apply(rows, pick=None, min_score=0, max_pe=150, max_de=2.0, roe_min=0, prof=False, seasoned=False, only_mos=False):
        f = rows
        if pick: f = [r for r in f if r["subsector"] in pick]
        f = [r for r in f if (r["buffett_score"] or 0) >= min_score]
        if max_pe < 150: f = [r for r in f if r["pe"] is None or r["pe"] <= max_pe]
        if max_de < 2.0: f = [r for r in f if r["debt_to_equity"] is None or r["debt_to_equity"] <= max_de]
        if roe_min > 0: f = [r for r in f if (r["roe_median_10y"] if r["roe_median_10y"] is not None else -1) >= roe_min / 100]
        if prof: f = [r for r in f if r["profitable_ttm"]]
        if seasoned: f = [r for r in f if not r["young_listing"]]
        if only_mos: f = [r for r in f if r["margin_of_safety"] is not None and r["margin_of_safety"] > 0]
        f = sorted(f, key=lambda r: (r["buffett_score"] is None, -(r["buffett_score"] or 0)))
        return [r["symbol"] for r in f]
    filters = [
        {"name": "default", "expect": apply(rows)},
        {"name": "it", "pick": ["IT services"], "expect": apply(rows, pick=["IT services"])},
        {"name": "score60", "minScore": 60, "expect": apply(rows, min_score=60)},
        {"name": "pe30", "maxPe": 30, "expect": apply(rows, max_pe=30)},
        {"name": "de1", "maxDe": 1.0, "expect": apply(rows, max_de=1.0)},
        {"name": "roe15", "minRoe": 15, "expect": apply(rows, roe_min=15)},
        {"name": "prof", "profitable": True, "expect": apply(rows, prof=True)},
        {"name": "seasoned", "seasoned": True, "expect": apply(rows, seasoned=True)},
        {"name": "mos", "belowValue": True, "expect": apply(rows, only_mos=True)},
    ]
    dump("screener.json", {"rows": rows, "cases": filters})

    # --- P/E vs history on a tiny hand series (same formula as analytics.fundamentals_metrics) ---
    # year-end close * (np_ttm/eps_ttm) / that year's profit, median of last values, today pe / median - 1
    profits = [("2018-03-31", 100.0), ("2019-03-31", 110.0), ("2020-03-31", 90.0), ("2021-03-31", 140.0)]
    closes = {"2018-03-30": 200.0, "2019-03-29": 250.0, "2020-03-31": 180.0, "2021-03-31": 300.0}
    np_ttm, eps_ttm, pe_today = 150.0, 10.0, 22.0
    shares = np_ttm / eps_ttm
    pe_hist = []
    for d, npv in profits:
        # last close on or before d within 15 days — supplied explicitly
        pass
    # mirror the loop with an explicit close series
    close = pd.Series({pd.Timestamp(k): v for k, v in closes.items()}).sort_index()
    np_ = pd.Series({pd.Timestamp(d): v for d, v in profits})
    vals = {}
    for d, npv in np_.items():
        sub = close[:d]
        if len(sub) and npv > 0 and (d - sub.index[-1]).days < 15:
            vals[d] = float(sub.iloc[-1] * shares / npv)
    pe_hist = pd.Series(vals)
    med = float(pe_hist.median())
    dump("pe_history.json", {
        "closes": [{"date": d.strftime("%Y-%m-%d"), "close": float(v)} for d, v in close.items()],
        "profits": [{"date": d.strftime("%Y-%m-%d"), "profit": float(v)} for d, v in np_.items()],
        "npTtm": np_ttm, "epsTtm": eps_ttm, "peToday": pe_today,
        "peHist": [{"date": d.strftime("%Y-%m-%d"), "pe": float(v)} for d, v in pe_hist.items()],
        "median": med,
        "vsHistory": pe_today / med - 1,
    })
    # --- INFY fundamental chart series (company page) ---
    if os.path.exists(db):
        con = sqlite3.connect(db)
        sym = "INFY"
        p = A.prices(con, sym)
        m = pd.read_parquet(os.path.join(ROOT, "data", "metrics.parquet")).set_index("symbol").loc[sym]
        fm, ser = A.fundamentals_metrics(con, sym, m["industry"], float(m["price"]), p)
        a = ser.get("annual")
        def col(frame, names):
            if frame is None: return None
            for n in names:
                if n in frame.columns: return frame[n]
            return None
        sales = col(a, ["Sales", "Revenue"]); npf = col(a, ["Net Profit"]); opm = col(a, ["OPM %"])
        roe = ser.get("roe")
        roce = col(ser["tables"].get("ratios"), ["ROCE %"])
        pe_h = ser.get("pe_hist")
        fcf = col(ser["tables"].get("cash-flow"), ["Free Cash Flow"])
        def series_year(s, scale=1.0):
            if s is None: return []
            out = []
            for i, v in s.items():
                d = i if isinstance(i, pd.Timestamp) else A._pdate(str(i))
                if d is None or pd.isna(v): 
                    out.append({"year": int(d.year) if d is not None else None, "value": None})
                else:
                    out.append({"year": int(d.year), "value": float(v) * scale})
            return out
        funds = [{"section": r[0], "item": r[1], "period": r[2], "value": r[3]} for r in con.execute(
            "SELECT section, item, period, value FROM fundamentals WHERE symbol=?", (sym,))]
        closes = [{"date": d.strftime("%Y-%m-%d"), "close": float(v)} for d, v in p["close"].items() if v > 0]
        dump("infy_fund.json", {
            "priceNow": float(m["price"]),
            "funds": funds,
            "closes": closes,
            "sales": series_year(sales),
            "profit": series_year(npf),
            "opm": series_year(opm),
            "roePct": series_year(roe, 100),
            "roce": series_year(roce),
            "peHist": series_year(pe_h),
            "fcf": series_year(fcf),
        })
        con.close()
    print("done")


if __name__ == "__main__":
    main()
