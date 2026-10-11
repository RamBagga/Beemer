import json
import numpy as np, pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import beemer as B
from beemer import A, C

m = B.load_metrics()
if m.empty:
    st.warning("Data is still loading — check back in a few minutes."); st.stop()
m = m.sort_values("name")
syms = list(m.symbol)
default = st.query_params.get("symbol") or st.session_state.get("company") or (m.sort_values("buffett_score", ascending=False).symbol.iloc[0])
if default not in syms: default = syms[0]
sym = st.selectbox("Choose a company", syms, index=syms.index(default),
                   format_func=lambda s: f"{m.set_index('symbol').loc[s, 'name']}  ·  {s}")
st.session_state["company"] = sym; st.query_params["symbol"] = sym
r = m.set_index("symbol").loc[sym]
subs = json.loads(r.subscores_json)
p = B.load_prices(sym)
fm, ser = B.load_fund(sym, r.industry, float(r.price))

a = ser.get("annual")
short = r["name"]

# ---------- verdict ----------
good = [s for s in subs if s["status"] == "✅"]; bad = [s for s in subs if s["status"] == "❌"]
def nm(s): return s["name"].split(" (")[0].split(" —")[0].lower()
verdict = f"<b>{short}</b> scores <b>{r.buffett_score:.0f}/100</b> on Beemer's Buffett tests. " if pd.notna(r.buffett_score) else ""
if good: verdict += "It shines on " + ", ".join(nm(s) for s in good) + ". "
if bad: verdict += "Buffett would be wary of its " + ", ".join(nm(s) for s in bad) + ". "
if not bad and good: verdict += "No outright red flags in our checklist. "
young = f" · listed {r.first_date[:4]}" if r.young_listing else f" · data since {r.first_date[:4]}"
c_h, c_g = st.columns([3.2, 1])
with c_h:
    st.markdown(f"""<div class="bm-hero" style="padding-right:34px"><div class="bm-k">{B.SUB_ICON.get(r.subsector,'')} {r.subsector} · {r.theme} · <span class="bm-mono">NSE:{sym}</span>{young}</div>
<h1>{short} {B.badge(r.buffett_score, r.score_label)}</h1><p>{verdict}</p></div>""", unsafe_allow_html=True)
with c_g:
    st.plotly_chart(B.gauge(r.buffett_score), width="stretch", config={"displayModeBar": False})
if r.young_listing:
    B.callout(f"🕒 <b>Young listing.</b> {short} has only <b>{r.history_years:.1f} years</b> of price history and {int(r.fin_years) if pd.notna(r.get('fin_years')) else 'a few'} years of annual results. "
              "Long-run tests (10-year ROE, growth consistency, P/E history) rest on thin evidence — read the score as provisional.")
if not r.profitable_ttm:
    B.callout(f"🔻 <b>Not yet profitable.</b> {short} lost money over the last 12 months (net profit {B.crore(r.get('profit_ttm_cr'))}). "
              "Buffett avoids businesses whose future earnings can't be estimated, so most of his tests will read low until profits arrive.")
about = (ser.get("meta") or {}).get("about")
if about:
    st.markdown(f"<div style='color:{C['muted']};margin:-6px 0 12px 0;font-size:.92rem'>🏢 {about}</div>", unsafe_allow_html=True)

k = st.columns(5)
with k[0]: B.kpi("Share price", B.inr(r.price, 0), f"as of {r.last_date} · 52-week high {B.inr(r.high_52w)}")
with k[1]: B.kpi("Market value", B.crore(r.market_cap_cr), "What the whole company costs at today's price.")
with k[2]:
    if pd.notna(r.pe):
        B.kpi("P/E", B.num(r.pe), (f"Own 10-yr median: {B.num(r.get('pe_median_10y'))}. " if pd.notna(r.get('pe_median_10y')) else "") + B.EXPLAIN["pe"][1].split(".")[0] + ".")
    else:
        B.kpi("P/E", "n/m", "Not meaningful — the company made a loss over the last 12 months.")
with k[3]: B.kpi("ROE (10y median)", B.pct(r.roe_median_10y, 0), f"Latest {B.pct(r.roe_latest, 0)}. Buffett likes 15%+ year after year.",
                 "pos" if (r.roe_median_10y or 0) >= .15 else "neg")
with k[4]:
    mos = r.margin_of_safety
    B.kpi("Margin of safety", B.pct(mos, 0) if pd.notna(mos) else "n/m", f"vs our rough value estimate of {B.inr(r.intrinsic_value)} per share." if pd.notna(mos) else "We can't estimate value without a record of profits.",
          "pos" if pd.notna(mos) and mos > 0 else "neg")

# ---------- checklist ----------
st.markdown("### ✅ The Buffett checklist")
cl, cr = st.columns([1.35, 1])
with cl:
    html = ""
    for s in subs:
        f = s["pts"] / s["max"]
        html += (f'<div class="bm-check"><div class="ic">{s["status"]}</div><div style="flex:1"><div class="t">{s["icon"]} {s["name"]} '
                 f'<span style="color:{C["muted"]};font-weight:500;font-size:.85rem">· {s["pts"]:.1f}/{s["max"]}</span></div>'
                 f'<div class="bm-bar"><i style="width:{f*100:.0f}%;background:{B.score_color(f*100)}"></i></div>'
                 f'<div class="d">{s["detail"]}</div><div class="w"><b>Why Buffett cares:</b> {s["why"]}</div></div></div>')
    st.markdown(f'<div class="bm-card">{html}</div>', unsafe_allow_html=True)
with cr:
    cats = [{"roe": "QUALITY", "debt": "DEBT", "growth": "GROWTH", "moat": "MOAT", "fcf": "CASH", "value": "PRICE"}[s["key"]] for s in subs]
    vals = [s["pts"] / s["max"] * 100 for s in subs]
    fig = go.Figure(go.Scatterpolar(r=vals + vals[:1], theta=cats + cats[:1], fill="toself", line=dict(color=C["blue"], width=2),
                                    fillcolor="rgba(31,143,255,0.18)", name=short))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor=C["line"]), angularaxis=dict(gridcolor=C["line"], tickfont=dict(color=C["muted"], size=11)),
                                 bgcolor="rgba(0,0,0,0)"), height=380, showlegend=False, title="Shape of the business", margin=dict(t=60, l=50, r=50, b=20))
    st.plotly_chart(fig, width="stretch")
    B.caption("a fuller, rounder shape = passes more of Buffett's tests. Spikes show where the company is strong; dents show what to dig into.")

# ---------- returns ----------
st.markdown("### 📈 What owning it has felt like")
k = st.columns(6)
for col, (lab, key) in zip(k, [("1 yr", "cagr_1y"), ("3 yrs", "cagr_3y"), ("5 yrs", "cagr_5y"), ("10 yrs", "cagr_10y"), ("20 yrs", "cagr_20y"), (f"Since {r.first_date[:4]}", "cagr_max")]):
    v = r.get(key)
    with col: B.kpi(f"{lab} / yr", B.pct(v) if pd.notna(v) else "–", "", "pos" if pd.notna(v) and v > 0 else ("neg" if pd.notna(v) else None))
st.markdown(f"<div class='bm-caption' style='margin-top:6px'>{B.explain_html('cagr')}</div>", unsafe_allow_html=True)
s = p["adj_close"]; dd = A.drawdowns(s)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.72, .28], vertical_spacing=.04)
fig.add_trace(go.Scatter(x=s.index, y=s, name="Price (adjusted)", line=dict(color=C["blue"], width=1.6), fill="tozeroy", fillcolor="rgba(31,143,255,0.07)"), 1, 1)
sx = B.load_prices("^BSESN")["adj_close"]; sx = sx[sx.index >= s.index[0]]
fig.add_trace(go.Scatter(x=sx.index, y=sx / sx.iloc[0] * s.iloc[0], name="Sensex (same start)", line=dict(color=C["muted"], width=1.3, dash="dot")), 1, 1)
fig.add_trace(go.Scatter(x=dd.index, y=dd * 100, name="Below peak", fill="tozeroy", line=dict(color=C["ember"], width=1), fillcolor="rgba(255,77,94,0.22)"), 2, 1)
B.log_axis(fig, float(min(s.min(), (sx / sx.iloc[0] * s.iloc[0]).min())), float(max(s.max(), (sx / sx.iloc[0] * s.iloc[0]).max())), row=1, col=1); fig.update_yaxes(ticksuffix="%", row=2, col=1)
fig.update_layout(height=520)
st.plotly_chart(fig, width="stretch")
B.caption(f"top: the dividend- and split-adjusted share price on a log scale, against the Sensex rebased to the same starting point — if the blue line ends above the dotted one, "
          f"{short} beat the market. Bottom: how far below its previous peak the stock was. Worst fall: <b>{r.max_drawdown*100:.0f}%</b> ({r.max_dd_date}). "
          f"Today: <b>{r.current_drawdown*100:.0f}%</b> below peak. 3-year volatility: <b>{B.pct(r.volatility_3y,0)}</b>.")

# ---------- fundamentals ----------
if a is not None and len(a):
    st.markdown("### 🧾 The business behind the share price")
    yrs = [d.year for d in a.index]
    sales = A.first_col(a, ["Sales", "Revenue"]); npf = A.first_col(a, ["Net Profit"]); opm = A.first_col(a, ["OPM %"])
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        if sales is not None: fig.add_trace(go.Bar(x=yrs, y=sales, name="Sales / revenue", marker_color="#1E3A63"))
        if npf is not None: fig.add_trace(go.Bar(x=yrs, y=npf, name="Net profit", marker_color=C["blue"]))
        fig.update_layout(barmode="overlay", height=340, title="Sales and profit (₹ crore, financial years)"); fig.update_yaxes(tickprefix="₹")
        st.plotly_chart(fig, width="stretch")
        per = next((n for n in (10, 5, 3) if pd.notna(r.get(f"sales_cagr_{n}y"))), None)
        gtxt = (f"sales grew <b>{B.pct(r.get(f'sales_cagr_{per}y'))}</b> a year" + (f" and profit <b>{B.pct(r.get(f'profit_cagr_{per}y'))}</b> a year" if pd.notna(r.get(f'profit_cagr_{per}y')) else " (profit growth can't be measured while the company is loss-making)") + f" over {per} years. ") if per else "too few years of results to measure growth. "
        B.caption(gtxt +
                  f"Profit rose in <b>{int(r.profit_up_years) if pd.notna(r.get('profit_up_years')) else '–'}</b> of the last {int(r.profit_years_checked) if pd.notna(r.get('profit_years_checked')) else '–'} years. {B.EXPLAIN['growth'][2]}")
    with c2:
        roe = ser.get("roe")
        fig = go.Figure()
        if roe is not None:
            fig.add_trace(go.Scatter(x=yrs, y=roe * 100, name="ROE", mode="lines+markers", line=dict(color=C["blue"], width=2)))
        if opm is not None:
            fig.add_trace(go.Scatter(x=yrs, y=opm, name="Operating margin", mode="lines+markers", line=dict(color=C["amber"], width=2)))
        roce = A.first_col(ser["tables"].get("ratios"), ["ROCE %"])
        if roce is not None:
            fig.add_trace(go.Scatter(x=[A._pdate(i).year for i in roce.index], y=roce, name="ROCE", mode="lines+markers", line=dict(color=C["violet"], width=1.5, dash="dot")))
        fig.add_hline(y=15, line_dash="dot", line_color=C["green"], annotation_text="15%", annotation_position="top left")
        fig.update_yaxes(ticksuffix="%"); fig.update_layout(height=340, title="Quality: returns and margins")
        st.plotly_chart(fig, width="stretch")
        B.caption(f"{B.EXPLAIN['roe'][1]} {B.EXPLAIN['opm'][1]} Lines that stay high and flat suggest a moat.")
    c3, c4 = st.columns(2)
    with c3:
        pe_h = ser.get("pe_hist")
        if pe_h is not None and len(pe_h) >= 3:
            fig = go.Figure(go.Bar(x=[d.year for d in pe_h.index], y=pe_h.values, name="P/E at year end", marker_color="#1E3A63"))
            if pd.notna(r.pe): fig.add_trace(go.Scatter(x=[pe_h.index[-1].year + 1], y=[r.pe], mode="markers+text", text=["today"], textposition="top center",
                                                        marker=dict(size=14, color=C["blue"], line=dict(color=C["ice"], width=1)), name="Today"))
            fig.add_hline(y=pe_h.median(), line_dash="dot", line_color=C["muted"], annotation_text=f"median {pe_h.median():.1f}", annotation_position="top left")
            fig.update_layout(height=330, title="Is it cheap or expensive vs its own past?", showlegend=False)
            st.plotly_chart(fig, width="stretch")
            B.caption(f"the P/E at the end of each financial year vs today. {B.EXPLAIN['pe'][1]} Today's P/E is "
                      f"<b>{abs(r.pe_vs_history)*100:.0f}% {'below' if r.pe_vs_history < 0 else 'above'}</b> its 10-year median. "
                      "(Historical P/Es assume today's share count, so treat them as approximate.)" if pd.notna(r.get("pe_vs_history")) else "")
        else:
            B.callout("🏷️ <b>No P/E history yet.</b> A P/E needs profits; this company has too few profitable years (or too short a listing) to compare today's price with its own past.")
    with c4:
        cf = ser["tables"].get("cash-flow")
        fcf = A.first_col(cf, ["Free Cash Flow"])
        if fcf is not None:
            fy = [A._pdate(i).year for i in fcf.index]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=fy, y=fcf, name="Free cash flow", marker_color=[C["green"] if v > 0 else C["ember"] for v in fcf]))
            if npf is not None: fig.add_trace(go.Scatter(x=yrs, y=npf, name="Net profit", line=dict(color=C["ice"], width=2)))
            fig.update_layout(height=330, title="Is profit turning into cash?"); fig.update_yaxes(tickprefix="₹")
            st.plotly_chart(fig, width="stretch")
            conv = r.get("fcf_conversion_10y")
            B.caption(f"{B.EXPLAIN['fcf'][1]} " + (f"Over the period shown, free cash flow added up to <b>{B.pct(conv,0)}</b> of reported profit. " if pd.notna(conv) else "Cash conversion can't be measured while total profits are negative. ") +
                      "Green bars above the line = cash-rich; red bars = the business consumed cash that year (often heavy expansion).")
        else:
            B.callout("💵 No cash-flow history available for this company yet.")

# ---------- metric glossary grid ----------
st.markdown("### 🔢 All the numbers, in plain English")
items = [
    ("pe", B.num(r.pe)), ("pb", B.num(r.pb)), ("roe", B.pct(r.roe_median_10y, 0) + " median"), ("roce", B.pct(r.get("roce_median_10y"), 0) + " median"),
    ("de", B.num(r.get("debt_to_equity"), 2)), ("dy", B.pct(r.dividend_yield, 2)),
    ("opm", B.pct(r.get("opm_median_10y"), 0) + " median" if pd.notna(r.get("opm_median_10y")) else "n/a"),
    ("fcf", B.crore(r.get("fcf_latest_cr")) + " (latest yr)" if pd.notna(r.get("fcf_latest_cr")) else "–"),
    ("max_drawdown", B.pct(r.max_drawdown, 0)), ("volatility", B.pct(r.volatility_3y, 0)),
    ("iv", B.inr(r.intrinsic_value)), ("mos", B.pct(r.margin_of_safety, 0)),
]
for i in range(0, len(items), 4):
    cols = st.columns(4)
    for col, (key, val) in zip(cols, items[i:i + 4]):
        t, what, why = B.EXPLAIN[key]
        with col: B.kpi(t, val, f"{what}<br><i>Why Buffett cares:</i> {why}")
    st.write("")

with st.expander("🧮 How we estimated intrinsic value (and why it's rough)"):
    if pd.notna(r.get("intrinsic_value")):
        st.markdown(f"""
- Start with trailing-12-month earnings per share: **₹{r.eps_ttm:,.2f}**
- Grow them for 10 years at **{r.iv_growth_used*100:.1f}%** a year (median of the company's 10-year sales growth, 10-year and 5-year profit growth; capped at 18%)
- Assume it keeps paying out **{r.iv_payout_used*100:.0f}%** of profit as dividends each year
- In year 10, value the business at a P/E of **{r.iv_terminal_pe:.1f}** (15, or its own historical median if lower)
- Discount everything back to today at **12%** a year — roughly what Indian equities have returned long-term, so it's the "hurdle" a stock must beat
- Result: **₹{r.intrinsic_value:,.0f}** per share vs a price of **₹{r.price:,.0f}** → margin of safety **{r.margin_of_safety*100:.0f}%**

Small changes in growth or the final P/E move this number a lot. Buffett himself says it's better to be approximately right than precisely wrong — use it as a sanity check.
""")
    else:
        st.write("Not enough positive earnings history to estimate.")
with st.expander("🗂️ Data notes"):
    st.markdown(f"- Price history from **{r.first_date}** to **{r.last_date}** (Yahoo Finance, `{sym}.NS`).\n"
                f"- Fundamentals: screener.in public page, **{r.get('basis')}** figures, FY{int(r.first_fy) if pd.notna(r.get('first_fy')) else '?'}–FY{int(r.last_fy) if pd.notna(r.get('last_fy')) else '?'}; refreshed {str(r.get('fund_fetched'))[:10]}.\n"
                f"- Price cleaning: {r.get('price_clean_notes') or 'none needed'}.")
    if a is not None:
        st.dataframe(a.T.rename(columns=lambda d: f"FY{d.year}"), width="stretch")
B.footer()
