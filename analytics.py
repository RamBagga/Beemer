"""Beemer analytics: price + fundamental metrics and the transparent Buffett Score."""
import json, math, re, sqlite3
import numpy as np, pandas as pd

MONTHS = {m: i for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], 1)}
FIN_INDUSTRY = "Financial Services"
DISCOUNT = 0.12      # Buffett-ish hurdle rate for Indian equities (risk-free ~7% + equity premium)
TERMINAL_PE = 15.0
MAX_G = 0.18


# ---------------- loading helpers ----------------
_MKT = {}


def _market(con):
    if "s" not in _MKT:
        m = pd.read_sql("SELECT date, adj_close FROM prices WHERE symbol='^BSESN' ORDER BY date", con)
        m["date"] = pd.to_datetime(m["date"])
        _MKT["s"] = m.set_index("date")["adj_close"].pct_change()
    return _MKT["s"]


def clean_prices(df, mkt=None, spike=0.30, ca=0.30):
    """Yahoo's NSE history (esp. pre-2006) has one-day glitches and some unadjusted corporate actions
    (splits/demergers). 1) drop one-day spikes that immediately revert; 2) for remaining single-day moves
    beyond +/-30% while the market moved <8%, treat as an unadjusted corporate action and rescale earlier history."""
    df = df[(df.close > 0) & (df.adj_close > 0)].copy()
    notes = []
    for _ in range(25):
        r = df.adj_close.pct_change(); rn = r.shift(-1)
        bad = ((r > spike) & (rn < -spike / (1 + spike))) | ((r < -spike / (1 + spike)) & (rn > spike))
        if not bad.any():
            break
        notes.append(f"dropped {int(bad.sum())} glitch days")
        df = df[~bad]
    r = df.adj_close.pct_change()
    m = mkt.reindex(df.index).fillna(0) if mkt is not None else pd.Series(0, index=df.index)
    jumps = r[(r.abs() > ca) & (m.abs() < 0.08)]
    vol_ratio = (df.volume / df.volume.rolling(20, min_periods=5).median().shift(1)) if "volume" in df else None
    for d, rv in jumps.items():
        vr = vol_ratio.get(d) if vol_ratio is not None else None
        if vr is not None and pd.notna(vr) and vr > 4 and d.year >= 2010:
            notes.append(f"kept {d.date()} move of {rv*100:+.0f}% as a real price move (volume {vr:.0f}x normal)")
            continue
        f = 1 + rv
        df.loc[df.index < d, ["close", "adj_close"]] *= f
        notes.append(f"adjusted {d.date()} jump of {rv*100:+.0f}% (likely split/demerger)")
    df.attrs["clean_notes"] = notes
    return df


def prices(con, sym, col="adj_close", clean=True):
    df = pd.read_sql("SELECT date, close, adj_close, volume FROM prices WHERE symbol=? ORDER BY date", con, params=(sym,))
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    if clean and not sym.startswith("^"):
        return clean_prices(df, _market(con))
    return df[df.close > 0]


def _pdate(p):
    m = re.match(r"([A-Za-z]{3}) (\d{4})", p)
    return pd.Timestamp(int(m.group(2)), MONTHS[m.group(1)], 1) + pd.offsets.MonthEnd(0) if m else None


def fund_tables(con, sym):
    """Return dict section -> wide DataFrame (rows=periods sorted, cols=items)."""
    f = pd.read_sql("SELECT section, item, period, value FROM fundamentals WHERE symbol=?", con, params=(sym,))
    out = {}
    for sec, g in f.groupby("section"):
        w = g.pivot_table(index="period", columns="item", values="value", aggfunc="first")
        w["_d"] = [(_pdate(p) if p != "TTM" else pd.Timestamp("2100-01-01")) for p in w.index]
        out[sec] = w.sort_values("_d").drop(columns="_d")
    return out


def fund_meta(con, sym):
    r = con.execute("SELECT fetched_at, basis, top_ratios, about FROM fund_meta WHERE symbol=?", (sym,)).fetchone()
    if not r:
        return {}
    return {"fetched_at": r[0], "basis": r[1], "top": json.loads(r[2] or "{}"), "about": r[3]}


def _topnum(top, key):
    v = top.get(key)
    if not v:
        return None
    m = re.findall(r"-?[\d,]+\.?\d*", v)
    return float(m[0].replace(",", "")) if m else None


def first_col(df, names):
    for n in names:
        if df is not None and n in df.columns:
            return df[n]
    return None


# ---------------- price metrics ----------------
def cagr_from_series(s, years):
    s = s.dropna()
    if s.empty:
        return None
    end_d, end_v = s.index[-1], s.iloc[-1]
    if years == "max":
        start_d, start_v = s.index[0], s.iloc[0]
    else:
        target = end_d - pd.DateOffset(years=years)
        if s.index[0] > target + pd.Timedelta(days=10):
            return None
        sub = s[:target]
        if sub.empty:
            return None
        start_d, start_v = sub.index[-1], sub.iloc[-1]
    yrs = (end_d - start_d).days / 365.25
    if yrs <= 0 or start_v <= 0:
        return None
    return (end_v / start_v) ** (1 / yrs) - 1


def drawdowns(s):
    peak = s.cummax()
    return s / peak - 1


def crash_episodes(s, threshold=-0.2):
    """List of peak->trough->recovery episodes deeper than threshold."""
    s = s.dropna(); peak = s.cummax(); dd = s / peak - 1
    eps, in_dd, start = [], False, None
    for d, v in dd.items():
        if not in_dd and v < 0:
            in_dd, start = True, d
        if in_dd and v == 0:
            seg = dd[start:d]
            if seg.min() <= threshold:
                eps.append(_ep(s, seg, d))
            in_dd = False
    if in_dd:
        seg = dd[start:]
        if seg.min() <= threshold:
            eps.append(_ep(s, seg, None))
    return pd.DataFrame(eps)


def _ep(s, seg, rec):
    trough = seg.idxmin()
    pk = s[:seg.index[0]].index[-2] if len(s[:seg.index[0]]) > 1 else seg.index[0]
    return {"peak_date": pk.date(), "trough_date": trough.date(), "fall_pct": seg.min() * 100,
            "months_to_bottom": round((trough - pk).days / 30.44, 1),
            "recovery_date": rec.date() if rec is not None else None,
            "months_to_recover": round((rec - trough).days / 30.44, 1) if rec is not None else None}


def sip(s, monthly=10000, start=None):
    s = s.dropna()
    if start is not None:
        s = s[s.index >= pd.Timestamp(start)]
    buys = s.groupby([s.index.year, s.index.month]).head(1)
    units = (monthly / buys).sum()
    invested = monthly * len(buys)
    value = units * s.iloc[-1]
    flows = [(d, -monthly) for d in buys.index] + [(s.index[-1], value)]
    return {"invested": invested, "value": value, "months": len(buys), "xirr": xirr(flows), "start": buys.index[0].date()}


def xirr(flows):
    t0 = flows[0][0]
    def npv(r):
        return sum(v / (1 + r) ** ((d - t0).days / 365.25) for d, v in flows)
    lo, hi = -0.99, 5.0
    try:
        if npv(lo) * npv(hi) > 0:
            return None
        for _ in range(200):
            mid = (lo + hi) / 2
            if npv(lo) * npv(mid) <= 0:
                hi = mid
            else:
                lo = mid
        return mid
    except (OverflowError, ZeroDivisionError):
        return None


def price_metrics(p):
    s = p["adj_close"]
    out = {"first_date": s.index[0].date().isoformat(), "last_date": s.index[-1].date().isoformat(),
           "price": float(p["close"].iloc[-1]), "history_years": round((s.index[-1] - s.index[0]).days / 365.25, 1)}
    for y in [1, 3, 5, 10, 20]:
        out[f"cagr_{y}y"] = cagr_from_series(s, y)
    out["cagr_max"] = cagr_from_series(s, "max") if out["history_years"] >= 1 else None
    out["total_return_since_start"] = float(s.iloc[-1] / s.iloc[0] - 1)
    dd = drawdowns(s)
    out["max_drawdown"] = float(dd.min()); out["max_dd_date"] = dd.idxmin().date().isoformat()
    out["current_drawdown"] = float(dd.iloc[-1])
    r = np.log(s).diff().dropna()
    r3 = r[r.index >= s.index[-1] - pd.DateOffset(years=3)]
    out["volatility_3y"] = float(r3.std() * math.sqrt(252)) if len(r3) > 50 else None
    out["high_52w"] = float(p["close"][p.index >= s.index[-1] - pd.DateOffset(weeks=52)].max())
    return out


# ---------------- fundamentals ----------------
def _cagr(a, b, n):
    if a is None or b is None or n <= 0 or a <= 0 or b <= 0 or pd.isna(a) or pd.isna(b):
        return None
    return (b / a) ** (1 / n) - 1


def annual(tbl):
    pl = tbl.get("profit-loss")
    if pl is None:
        return None
    a = pl[pl.index != "TTM"].copy()
    a.index = [_pdate(i) for i in a.index]
    return a


def fundamentals_metrics(con, sym, industry, price_now, p):
    t = fund_tables(con, sym); meta = fund_meta(con, sym); top = meta.get("top", {})
    pl, bs, cf, ra = t.get("profit-loss"), t.get("balance-sheet"), t.get("cash-flow"), t.get("ratios")
    out = {"basis": meta.get("basis"), "fund_fetched": meta.get("fetched_at")}
    is_fin = industry == FIN_INDUSTRY
    out["is_financial"] = is_fin
    if pl is None or pl.empty:
        return out, {}
    a = annual(t)
    a = a[a.index.notna()]
    sales = first_col(a, ["Sales", "Revenue"]); np_ = first_col(a, ["Net Profit"]); eps = first_col(a, ["EPS in Rs"])
    opm = first_col(a, ["OPM %"])
    ttm = pl.loc["TTM"] if "TTM" in pl.index else pl.iloc[-1]
    eps_ttm = ttm.get("EPS in Rs"); np_ttm = ttm.get("Net Profit")
    sales_ttm = ttm.get("Sales", ttm.get("Revenue"))
    last10 = a.tail(11)
    out["profit_ttm_cr"] = float(np_ttm) if np_ttm is not None and not pd.isna(np_ttm) else None
    out["sales_ttm_cr"] = float(sales_ttm) if sales_ttm is not None and not pd.isna(sales_ttm) else None
    out["profitable_ttm"] = bool(np_ttm is not None and not pd.isna(np_ttm) and np_ttm > 0)
    if np_ is not None:
        out["profitable_years"] = int((np_.dropna() > 0).sum()); out["fin_years"] = int(np_.notna().sum())
    if out.get("sales_ttm_cr") and np_ttm is not None and not pd.isna(np_ttm):
        out["net_margin_ttm"] = float(np_ttm / out["sales_ttm_cr"]) if out["sales_ttm_cr"] else None
    out["fy_years"] = len(a)
    out["first_fy"] = a.index[0].year if len(a) else None
    out["last_fy"] = a.index[-1].year if len(a) else None
    for n in [3, 5, 10]:
        if sales is not None and len(sales.dropna()) > n:
            out[f"sales_cagr_{n}y"] = _cagr(sales.iloc[-1 - n], sales.iloc[-1], n)
        if np_ is not None and len(np_.dropna()) > n:
            out[f"profit_cagr_{n}y"] = _cagr(np_.iloc[-1 - n], np_.iloc[-1], n)
    if np_ is not None:
        g = np_.tail(11).pct_change().dropna()
        out["profit_up_years"] = int((np_.tail(11).diff().dropna() > 0).sum()); out["profit_years_checked"] = int(len(g))
        out["loss_years_10y"] = int((np_.tail(10) < 0).sum())
    if sales is not None:
        out["sales_up_years"] = int((sales.tail(11).diff().dropna() > 0).sum())
    # ROE from balance sheet
    roe = None
    if bs is not None and not bs.empty:
        b = bs.copy(); b.index = [_pdate(i) for i in b.index]
        eq = (b.get("Equity Capital", 0) + b.get("Reserves", 0))
        eq_a = eq.reindex(a.index)
        avg_eq = (eq_a + eq_a.shift(1)) / 2
        avg_eq = avg_eq.fillna(eq_a)
        avg_eq = avg_eq.where(avg_eq > 0)          # negative equity makes ROE meaningless
        roe = (np_ / avg_eq).replace([np.inf, -np.inf], np.nan) if np_ is not None else None
        borrow = first_col(b, ["Borrowings", "Borrowing"])
        latest_eq = eq.dropna().iloc[-1] if eq.notna().any() else None
        if borrow is not None and latest_eq:
            out["debt_to_equity"] = float(borrow.dropna().iloc[-1] / latest_eq) if borrow.notna().any() else 0.0
        elif latest_eq:
            out["debt_to_equity"] = 0.0
        ta = b.get("Total Assets")
        if ta is not None and np_ is not None:
            ta_a = ta.reindex(a.index)
            roa = np_ / ((ta_a + ta_a.shift(1)) / 2).fillna(ta_a)
            out["roa_latest"] = float(roa.dropna().iloc[-1]) if roa.notna().any() else None
            out["roa_median_5y"] = float(roa.dropna().tail(5).median()) if roa.notna().any() else None
        out["equity_latest_cr"] = float(latest_eq) if latest_eq else None
    if roe is not None and roe.notna().any():
        r10 = roe.dropna().tail(10)
        out["roe_latest"] = float(r10.iloc[-1]); out["roe_median_10y"] = float(r10.median())
        out["roe_years_above_15"] = int((r10 > 0.15).sum()); out["roe_years_checked"] = int(len(r10))
    roce = first_col(ra, ["ROCE %"])
    if roce is not None and roce.notna().any():
        rc = roce.dropna()
        out["roce_latest"] = float(rc.iloc[-1]) / 100; out["roce_median_10y"] = float(rc.tail(10).median()) / 100
    if opm is not None and opm.notna().any():
        o = opm.dropna().tail(10) / 100
        out["opm_latest"] = float(o.iloc[-1]); out["opm_median_10y"] = float(o.median())
        out["opm_cv"] = float(o.std() / abs(o.mean())) if abs(o.mean()) > 1e-9 else None
        if len(o) >= 5:
            y = o.tail(5).values; out["opm_trend_5y_pp"] = float((y[-1] - y[0]) * 100)
    # cash flow
    fcf = first_col(cf, ["Free Cash Flow"]); cfo = first_col(cf, ["Cash from Operating Activity"])
    if fcf is not None and fcf.notna().any():
        f10 = fcf.dropna().tail(10)
        out["fcf_latest_cr"] = float(f10.iloc[-1]); out["fcf_positive_years"] = int((f10 > 0).sum())
        out["fcf_years_checked"] = int(len(f10))
        if np_ is not None:
            npsum = np_.tail(len(f10)).sum()
            out["fcf_conversion_10y"] = float(f10.sum() / npsum) if npsum > 0 else None
    # valuation
    scr_price = _topnum(top, "Current Price"); mcap_scr = _topnum(top, "Market Cap")
    adj = (price_now / scr_price) if scr_price else 1.0
    out["market_cap_cr"] = mcap_scr * adj if mcap_scr else None
    pe_scr = _topnum(top, "Stock P/E")
    if np_ttm is not None and not pd.isna(np_ttm) and np_ttm <= 0:
        pe_scr = None; eps_ttm = None          # loss-making: P/E is not meaningful
    if pe_scr and pe_scr > 0:
        # screener's P/E excludes some exceptional items; prefer it and derive the EPS it implies
        out["pe"] = price_now / (scr_price / pe_scr) if scr_price else pe_scr
        out["eps_ttm"] = price_now / out["pe"]
        if eps_ttm and eps_ttm > 0 and abs(out["eps_ttm"] / eps_ttm - 1) > 0.5:
            out["eps_distorted"] = True
    elif eps_ttm and eps_ttm > 0:
        out["eps_ttm"] = float(eps_ttm); out["pe"] = price_now / eps_ttm
    bv = _topnum(top, "Book Value")
    if bv and bv > 0:
        out["pb"] = price_now / bv; out["book_value"] = bv
    dy = _topnum(top, "Dividend Yield")
    out["dividend_yield"] = (dy / 100 / adj) if dy is not None else None
    if out.get("fcf_latest_cr") is not None and out.get("market_cap_cr"):
        out["fcf_yield"] = out["fcf_latest_cr"] / out["market_cap_cr"]
    payout = first_col(a, ["Dividend Payout %"])
    out["payout_median"] = float(payout.dropna().tail(5).median()) / 100 if payout is not None and payout.notna().any() else None
    # historical P/E: FY-end split-adjusted close x current share count / that year's net profit
    pe_hist = None
    if np_ is not None and eps_ttm and np_ttm and eps_ttm > 0 and np_ttm > 0:
        shares_cr = np_ttm / eps_ttm
        close = p["close"]
        vals = {}
        for d, npv in np_.tail(10).items():
            sub = close[:d]
            if len(sub) and npv and npv > 0 and (d - sub.index[-1]).days < 15:
                vals[d] = sub.iloc[-1] * shares_cr / npv
        pe_hist = pd.Series(vals)
        if len(pe_hist) >= 3:
            out["pe_median_10y"] = float(pe_hist.median())
            if out.get("pe"):
                out["pe_vs_history"] = out["pe"] / out["pe_median_10y"] - 1
    # intrinsic value (simple, transparent)
    if out.get("eps_ttm"):
        gs = [out.get("profit_cagr_10y"), out.get("sales_cagr_10y"), out.get("profit_cagr_5y")]
        gs = [g for g in gs if g is not None]
        g = float(np.clip(np.median(gs), 0, MAX_G)) if gs else 0.05
        g_fade = g  # years 1-10 at g
        po = out.get("payout_median") or 0.3
        po = float(np.clip(po, 0.1, 1.0))
        eps_t, pv = out["eps_ttm"], 0.0
        for yr in range(1, 11):
            eps_t *= (1 + g_fade)
            pv += eps_t * po / (1 + DISCOUNT) ** yr
        tpe = min(TERMINAL_PE, out.get("pe_median_10y") or TERMINAL_PE)
        pv += eps_t * tpe / (1 + DISCOUNT) ** 10
        out["iv_growth_used"] = g; out["iv_terminal_pe"] = tpe; out["iv_payout_used"] = po
        out["intrinsic_value"] = pv
        out["margin_of_safety"] = 1 - price_now / pv
    series = {"annual": a, "roe": roe, "pe_hist": pe_hist, "tables": t, "meta": meta}
    return out, series


# ---------------- Buffett score ----------------
def _lin(x, lo, hi):
    if x is None or pd.isna(x):
        return None
    return float(np.clip((x - lo) / (hi - lo), 0, 1))


def buffett_score(m):
    """Returns (score 0-100 or None, list of sub-score dicts). Not-applicable criteria are dropped and the
    total is rescaled to 100 so financial companies are not penalised for lacking e.g. FCF."""
    subs = []
    # 1 ROE consistency (20)
    if m.get("roe_years_checked"):
        frac = m["roe_years_above_15"] / m["roe_years_checked"]
        pts = 14 * frac + 6 * (_lin(m.get("roe_median_10y"), 0.12, 0.25) or 0)
        subs.append(dict(key="roe", icon="", name="Return on equity", max=20, pts=pts,
            detail=f"Above 15% in {m['roe_years_above_15']} of {m['roe_years_checked']} years. Median {m['roe_median_10y']*100:.0f}%.",
            why="Profit per ₹100 of owners' capital. Buffett wants 15%+, year after year."))
    # 2 Debt (15) / ROA for lenders
    if m.get("is_financial"):
        if m.get("roa_median_5y") is not None:
            r = m["roa_median_5y"]
            pts = 15 * (_lin(r, 0.005, 0.02) or 0)
            subs.append(dict(key="debt", icon="", name="Balance sheet (lender)", max=15, pts=pts,
                detail=f"5-year median return on assets {r*100:.2f}%.",
                why="For lenders, debt is inventory. Return on assets is the test. 1.5%+ is excellent."))
    elif m.get("debt_to_equity") is not None:
        de = m["debt_to_equity"]
        pts = 15 * (1 - (_lin(de, 0.1, 1.5) or 0))
        subs.append(dict(key="debt", icon="", name="Debt", max=15, pts=pts,
            detail=f"Debt-to-equity {de:.2f}.",
            why="Debt magnifies bad years. Under 0.5 is comfortable. Near zero is ideal."))
    # 3 Earnings consistency/growth (20)
    if m.get("profit_years_checked"):
        frac = m["profit_up_years"] / m["profit_years_checked"]
        g = m.get("profit_cagr_10y", m.get("profit_cagr_5y"))
        pts = 10 * frac + 10 * (_lin(g, 0.0, 0.15) or 0) - 2 * m.get("loss_years_10y", 0)
        pts = max(pts, 0)
        gtxt = f"{g*100:.1f}% a year" if g is not None else "n/a"
        ly = m.get('loss_years_10y', 0)
        subs.append(dict(key="growth", icon="", name="Earnings consistency", max=20, pts=pts,
            detail=f"Profit up in {m['profit_up_years']} of {m['profit_years_checked']} years. Long-run growth {gtxt}. {'No loss years.' if not ly else f'{ly} loss years.'}",
            why="Predictable earnings are easier to value, and rarely surprise badly."))
    # 4 Moat proxy: margins level + stability (15)
    if m.get("opm_median_10y") is not None:
        lvl = _lin(m["opm_median_10y"], 0.08, 0.25) or 0
        stab = 1 - (_lin(m.get("opm_cv"), 0.1, 0.5) or 0) if m.get("opm_cv") is not None else 0.5
        rc = m.get("roce_median_10y")
        rct = f" ROCE {rc*100:.0f}%." if rc is not None else ""
        pts = 8 * lvl + 7 * stab
        subs.append(dict(key="moat", icon="", name="Moat", max=15, pts=pts,
            detail=f"Operating margin {m['opm_median_10y']*100:.0f}% (10-yr median), {m['opm_latest']*100:.0f}% latest. {'Stable' if stab>0.6 else 'Moderate swings' if stab>0.3 else 'Volatile'}.{rct}",
            why="Margins that hold for a decade signal pricing power competitors can't break."))
    # 5 FCF (15) — not applicable for financials
    if not m.get("is_financial") and m.get("fcf_years_checked"):
        frac = m["fcf_positive_years"] / m["fcf_years_checked"]
        conv = m.get("fcf_conversion_10y")
        pts = 10 * frac + 5 * (_lin(conv, 0.3, 0.9) or 0)
        ctxt = f" {conv*100:.0f}% of profit converted to cash." if conv is not None else ""
        subs.append(dict(key="fcf", icon="", name="Cash generation", max=15, pts=pts,
            detail=f"Free cash flow positive in {m['fcf_positive_years']} of {m['fcf_years_checked']} years.{ctxt}",
            why="Profit is an opinion. Cash is a fact."))
    # 6 Valuation (15)
    if m.get("pe") is not None or m.get("margin_of_safety") is not None:
        pv = m.get("pe_vs_history"); mos = m.get("margin_of_safety")
        a = 8 * (1 - (_lin(pv, -0.3, 0.5) or 0)) if pv is not None else 4
        b = 7 * (_lin(mos, -0.5, 0.3) or 0) if mos is not None else 0
        parts = []
        if m.get("pe"): parts.append(f"P/E {m['pe']:.1f}")
        if pv is not None: parts.append(f"{abs(pv)*100:.0f}% {'below' if pv<0 else 'above'} its 10-yr median of {m['pe_median_10y']:.1f}")
        if mos is not None:
            if mos > 0: mtxt = f"{mos*100:.0f}% margin of safety"
            elif mos > -1: mtxt = f"{-mos*100:.0f}% above estimate"
            else: mtxt = f"{1-mos:.1f}× estimate"
            parts.append(f"value estimate ₹{m['intrinsic_value']:,.0f}, {mtxt}")
        if m.get("eps_distorted"): parts.append("recent profit includes one-offs, so history is less comparable")
        subs.append(dict(key="value", icon="", name="Price", max=15, pts=a + b,
            detail="; ".join(parts) + ".",
            why="Price is what you pay. Value is what you get. Buffett wants a margin of safety."))
    if not subs:
        return None, subs
    tot = sum(s["pts"] for s in subs); mx = sum(s["max"] for s in subs)
    for s in subs:
        f = s["pts"] / s["max"]
        s["status"] = "pass" if f >= 0.7 else ("watch" if f >= 0.4 else "fail")
    return round(100 * tot / mx, 1), subs


def score_label(s):
    if s is None: return "n/a"
    return "Strong" if s >= 75 else "Good" if s >= 60 else "Mixed" if s >= 40 else "Weak"


def build_metrics(con, syms):
    uni = pd.read_sql("SELECT * FROM universe", con).set_index("symbol")
    rows = []
    for s in syms:
        p = prices(con, s)
        if p.empty:
            continue
        m = {"symbol": s, "name": uni.loc[s, "name"], "industry": uni.loc[s, "industry"],
             "subsector": uni.loc[s, "subsector"], "theme": uni.loc[s, "theme"], "note": uni.loc[s, "note"]}
        m.update(price_metrics(p))
        m["price_clean_notes"] = "; ".join(p.attrs.get("clean_notes", []))
        try:
            f, _ = fundamentals_metrics(con, s, m["industry"], m["price"], p)
            m.update(f)
        except Exception as e:  # keep going
            m["fund_error"] = str(e)
        yrs = m.get("history_years") or 0
        m["young_listing"] = yrs < 5
        m["listing_year"] = int(m["first_date"][:4])
        sc, subs = buffett_score(m)
        m["buffett_score"] = sc; m["score_label"] = score_label(sc)
        for sb in subs:
            m[f"sub_{sb['key']}"] = round(sb["pts"] / sb["max"] * 100)
        m["subscores_json"] = json.dumps(subs)
        rows.append(m)
    return pd.DataFrame(rows)
