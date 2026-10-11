import json, re
import numpy as np, pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import beemer as B
from beemer import A, C

m = B.load_metrics()
if m.empty:
    st.warning("Data is loading. Back in a few minutes."); st.stop()
m = m.sort_values("name")
syms = list(m.symbol)
default = st.query_params.get("symbol") or st.session_state.get("company") or (m.sort_values("buffett_score", ascending=False).symbol.iloc[0])
if default not in syms: default = syms[0]
sym = st.selectbox("Company", syms, index=syms.index(default),
                   format_func=lambda s: f"{m.set_index('symbol').loc[s, 'name']}  ·  {s}")
st.session_state["company"] = sym; st.query_params["symbol"] = sym
r = m.set_index("symbol").loc[sym]
subs = json.loads(r.subscores_json)
p = B.load_prices(sym)
fm, ser = B.load_fund(sym, r.industry, float(r.price))

a = ser.get("annual")
short = r["name"]

# ---------- verdict ----------
def status(s):
    f = s["pts"] / s["max"]
    return "pass" if f >= 0.7 else ("watch" if f >= 0.4 else "fail")
good = [s for s in subs if status(s) == "pass"]; bad = [s for s in subs if status(s) == "fail"]
def nm(s): return s["name"].lower()
verdict = ""
if good: verdict += "Strong on " + ", ".join(nm(s) for s in good) + ". "
if bad: verdict += "Weak on " + ", ".join(nm(s) for s in bad) + ". "
if not bad and good: verdict += "No red flags."
young = f" · listed {r.first_date[:4]}" if r.young_listing else f" · data since {r.first_date[:4]}"
c_h, c_g = st.columns([3.2, 1])
with c_h:
    st.markdown(f"""<div class="bm-hero" style="padding-right:34px"><div class="bm-k">{B.sub_dot(r.subsector, 7)}{r.subsector} · {r.theme} · <span class="bm-mono">NSE:{sym}</span>{young}</div>
<h1>{short} {B.badge(r.buffett_score, r.score_label)}</h1><p>{verdict}</p></div>""", unsafe_allow_html=True)
with c_g:
    st.plotly_chart(B.gauge(r.buffett_score), width="stretch", config={"displayModeBar": False})
if r.young_listing:
    B.callout(f"<b>Young listing.</b> {r.history_years:.1f} years of prices, {int(r.fin_years) if pd.notna(r.get('fin_years')) else 'few'} years of results. Treat the score as provisional.")
if not r.profitable_ttm:
    B.callout(f"<b>Loss-making.</b> 12-month net profit {B.crore(r.get('profit_ttm_cr'))}. Most tests read low until profits arrive.")
about = (ser.get("meta") or {}).get("about")
about = re.sub(r"\s*\[\d+\]", "", about).strip() if about else about
if about:
    st.markdown(f"<div style='color:{C['muted']};margin:-6px 0 12px 0;font-size:.92rem'>{about}</div>", unsafe_allow_html=True)

k = st.columns(5)
with k[0]: B.kpi("Price", B.inr(r.price, 0), f"{pd.Timestamp(r.last_date):%d %b %Y}. 52-week high {B.inr(r.high_52w)}.")
with k[1]: B.kpi("Market cap", B.crore(r.market_cap_cr), f"Rank {int((m.market_cap_cr > r.market_cap_cr).sum()) + 1} of {len(m)}." if pd.notna(r.market_cap_cr) else "")
with k[2]:
    if pd.notna(r.pe):
        B.kpi("P/E", B.num(r.pe), f"10-yr median {B.num(r.get('pe_median_10y'))}." if pd.notna(r.get('pe_median_10y')) else B.EXPLAIN["pe"][1])
    else:
        B.kpi("P/E", "n/m", "Not meaningful while loss-making.")
with k[3]: B.kpi("ROE · 10-yr median", B.pct(r.roe_median_10y, 0), f"Latest {B.pct(r.roe_latest, 0)}. Target 15%+.",
                 "pos" if (r.roe_median_10y or 0) >= .15 else "neg")
with k[4]:
    mos = r.margin_of_safety
    B.kpi("Margin of safety", B.pct(mos, 0) if pd.notna(mos) else "n/m", f"Value estimate {B.inr(r.intrinsic_value)}." if pd.notna(mos) else "No profit record to value.",
          "pos" if pd.notna(mos) and mos > 0 else "neg")

# ---------- checklist ----------
st.markdown("### Buffett checklist")
cl, cr = st.columns([1.35, 1])
with cl:
    html = ""
    for s in subs:
        f = s["pts"] / s["max"]
        stt = status(s); sc = {"pass": C["green"], "watch": C["amber"], "fail": C["ember"]}[stt]
        html += (f'<div class="bm-check"><div class="ic" style="color:{B.ink(sc)};border:1px solid {B.rgba(sc, .5)};background:{B.rgba(sc, .1)}">{stt.upper()}</div><div style="flex:1"><div class="t">{s["name"]} '
                 f'<span style="color:{C["muted"]};font-weight:500;font-size:.85rem">· {s["pts"]:.3g}/{s["max"]}</span></div>'
                 f'<div class="bm-bar"><i style="width:{f*100:.0f}%;background:{B.score_color(f*100)}"></i></div>'
                 f'<div class="d">{s["detail"]}</div><div class="w">{s["why"]}</div></div></div>')
    st.markdown(f'<div class="bm-card">{html}</div>', unsafe_allow_html=True)
with cr:
    cats = [{"roe": "QUALITY", "debt": "DEBT", "growth": "GROWTH", "moat": "MOAT", "fcf": "CASH", "value": "PRICE"}[s["key"]] for s in subs]
    vals = [s["pts"] / s["max"] * 100 for s in subs]
    fig = go.Figure(go.Scatterpolar(r=vals + vals[:1], theta=cats + cats[:1], fill="toself", line=dict(color=C["blue"], width=1.6),
                                    fillcolor=B.rgba(C["blue"], .14), marker=dict(size=5, color=C["blue"]), name=short))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor=C["grid"], linecolor=C["grid"]), angularaxis=dict(gridcolor=C["grid"], linecolor=C["line"], tickfont=dict(color=C["muted"], size=11, family="JetBrains Mono")),
                                 bgcolor="rgba(0,0,0,0)"), height=380, showlegend=False, title="Profile", margin=dict(t=60, l=50, r=50, b=20))
    st.plotly_chart(fig, width="stretch")

# ---------- returns ----------
st.markdown("### Returns")
k = st.columns(6)
for col, (lab, key) in zip(k, [("1 yr", "cagr_1y"), ("3 yrs", "cagr_3y"), ("5 yrs", "cagr_5y"), ("10 yrs", "cagr_10y"), ("20 yrs", "cagr_20y"), (f"Since {r.first_date[:4]}", "cagr_max")]):
    v = r.get(key)
    with col: B.kpi(f"{lab} / yr", B.pct(v) if pd.notna(v) else "–", "", "pos" if pd.notna(v) and v > 0 else ("neg" if pd.notna(v) else None))
st.markdown(f"<div class='bm-caption' style='margin-top:6px'>Annualised, price only.</div>", unsafe_allow_html=True)
s = p["adj_close"]; dd = A.drawdowns(s)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.72, .28], vertical_spacing=.04)
fig.add_trace(go.Scatter(x=s.index, y=s, name="Price, adjusted", line=dict(color=C["blue"], width=1.6), hovertemplate="₹%{y:,.1f}", **B.soft(C["blue"])), 1, 1)
sx = B.load_prices("^BSESN")["adj_close"]; sx = sx[sx.index >= s.index[0]]
fig.add_trace(go.Scatter(x=sx.index, y=sx / sx.iloc[0] * s.iloc[0], name="Sensex, rebased", line=dict(color=C["dim"], width=1.2, dash="dot"), hovertemplate="₹%{y:,.1f}"), 1, 1)
fig.add_trace(go.Scatter(x=dd.index, y=dd * 100, name="Below peak", line=dict(color=C["ember"], width=1), hovertemplate="%{y:.1f}%", **B.area(C["ember"], .28, down=True)), 2, 1)
B.log_axis(fig, float(min(s.min(), (sx / sx.iloc[0] * s.iloc[0]).min())), float(max(s.max(), (sx / sx.iloc[0] * s.iloc[0]).max())), row=1, col=1); fig.update_yaxes(ticksuffix="%", row=2, col=1)
fig.update_layout(height=520)
st.plotly_chart(fig, width="stretch")
B.caption(f"Log scale vs Sensex, rebased. Worst fall <b>{r.max_drawdown*100:.0f}%</b> ({pd.Timestamp(r.max_dd_date):%b %Y}). "
          f"Now <b>{r.current_drawdown*100:.0f}%</b> below peak. 3-yr volatility <b>{B.pct(r.volatility_3y,0)}</b>.")

# ---------- fundamentals ----------
if a is not None and len(a):
    st.markdown("### Fundamentals")
    yrs = [d.year for d in a.index]
    sales = A.first_col(a, ["Sales", "Revenue"]); npf = A.first_col(a, ["Net Profit"]); opm = A.first_col(a, ["OPM %"])
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        if sales is not None: fig.add_trace(go.Bar(x=yrs, y=sales, name="Sales / revenue", marker_color=C["bar"], hovertemplate="₹%{y:,.0f} cr"))
        if npf is not None: fig.add_trace(go.Bar(x=yrs, y=npf, name="Net profit", marker_color=C["blue"], hovertemplate="₹%{y:,.0f} cr"))
        fig.update_layout(barmode="group", bargap=.3, bargroupgap=.08, height=340, title="Sales and profit · ₹ crore"); fig.update_yaxes(tickprefix="₹")
        st.plotly_chart(fig, width="stretch")
        per = next((n for n in (10, 5, 3) if pd.notna(r.get(f"sales_cagr_{n}y"))), None)
        gtxt = (f"{per}-yr growth: sales <b>{B.pct(r.get(f'sales_cagr_{per}y'))}</b>" + (f", profit <b>{B.pct(r.get(f'profit_cagr_{per}y'))}</b> a year. " if pd.notna(r.get(f'profit_cagr_{per}y')) else " a year. Profit growth n/m. ")) if per else "Too few years to measure growth. "
        B.caption(gtxt + f"Profit up in <b>{int(r.profit_up_years) if pd.notna(r.get('profit_up_years')) else '–'}</b> of {int(r.profit_years_checked) if pd.notna(r.get('profit_years_checked')) else '–'} years.")
    with c2:
        roe = ser.get("roe")
        fig = go.Figure()
        if roe is not None:
            fig.add_trace(go.Scatter(x=yrs, y=roe * 100, name="ROE", mode="lines+markers", line=dict(color=C["blue"], width=1.8), marker=dict(size=5), hovertemplate="%{y:.1f}%"))
        if opm is not None:
            fig.add_trace(go.Scatter(x=yrs, y=opm, name="Operating margin", mode="lines+markers", line=dict(color=C["teal"], width=1.6), marker=dict(size=5), hovertemplate="%{y:.1f}%"))
        roce = A.first_col(ser["tables"].get("ratios"), ["ROCE %"])
        if roce is not None:
            fig.add_trace(go.Scatter(x=[A._pdate(i).year for i in roce.index], y=roce, name="ROCE", mode="lines+markers", line=dict(color=C["violet"], width=1.3, dash="dot"), marker=dict(size=4), hovertemplate="%{y:.1f}%"))
        fig.add_hline(y=15, line_dash="dot", line_width=1, line_color=C["dim"], annotation_text="15%", annotation_position="top left", annotation_font=dict(color=C["muted"], size=11))
        fig.update_yaxes(ticksuffix="%"); fig.update_layout(height=340, title="Returns on capital and margin")
        st.plotly_chart(fig, width="stretch")
    c3, c4 = st.columns(2)
    with c3:
        pe_h = ser.get("pe_hist")
        if pe_h is not None and len(pe_h) >= 3:
            fig = go.Figure(go.Bar(x=[d.year for d in pe_h.index], y=pe_h.values, name="P/E at year end", marker_color=C["bar"], hovertemplate="%{y:.1f}"))
            if pd.notna(r.pe): fig.add_trace(go.Scatter(x=[pe_h.index[-1].year + 1], y=[r.pe], mode="markers+text", text=["today"], textposition="top center",
                                                        marker=dict(size=12, color=C["blue"], line=dict(color=C["surface"], width=2)), textfont=dict(color=C["blue"], size=11), name="Today", hovertemplate="%{y:.1f}"))
            fig.add_hline(y=pe_h.median(), line_dash="dot", line_width=1, line_color=C["dim"], annotation_text=f"median {pe_h.median():.1f}", annotation_position="top left", annotation_font=dict(color=C["muted"], size=11))
            fig.update_layout(height=330, title="P/E vs its own history", showlegend=False)
            st.plotly_chart(fig, width="stretch")
            B.caption(f"Year-end P/E vs today: <b>{abs(r.pe_vs_history)*100:.0f}% {'below' if r.pe_vs_history < 0 else 'above'}</b> the 10-yr median. Approximate." if pd.notna(r.get("pe_vs_history")) else "Year-end P/E. Approximate.")
        else:
            B.callout("<b>No P/E history.</b> Too few profitable years to compare.")
    with c4:
        cf = ser["tables"].get("cash-flow")
        fcf = A.first_col(cf, ["Free Cash Flow"])
        if fcf is not None:
            fy = [A._pdate(i).year for i in fcf.index]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=fy, y=fcf, name="Free cash flow", marker_color=[C["teal"] if v > 0 else C["ember"] for v in fcf], hovertemplate="₹%{y:,.0f} cr"))
            if npf is not None: fig.add_trace(go.Scatter(x=yrs, y=npf, name="Net profit", line=dict(color=C["blue"], width=1.8), hovertemplate="₹%{y:,.0f} cr"))
            fig.update_layout(height=330, title="Profit vs free cash flow"); fig.update_yaxes(tickprefix="₹")
            st.plotly_chart(fig, width="stretch")
            conv = r.get("fcf_conversion_10y")
            B.caption(f"Cash conversion <b>{B.pct(conv,0)}</b> of profit, 10 years." if pd.notna(conv) else "Cash conversion n/m.")
        else:
            B.callout("No cash-flow history yet.")

# ---------- metric glossary grid ----------
st.markdown("### Key metrics")
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
        with col: B.kpi(t, val, what)
    st.write("")

with st.expander("Value estimate: method"):
    if pd.notna(r.get("intrinsic_value")):
        st.markdown(f"""
- Earnings per share, last 12 months: **₹{r.eps_ttm:,.2f}**
- Growth, 10 years: **{r.iv_growth_used*100:.1f}%** a year (capped at 18%)
- Dividend payout: **{r.iv_payout_used*100:.0f}%**
- Exit P/E in year 10: **{r.iv_terminal_pe:.1f}**
- Discount rate: **12%**
- Value: **₹{r.intrinsic_value:,.0f}** vs price **₹{r.price:,.0f}**. Margin of safety **{r.margin_of_safety*100:.0f}%**

Sensitive to growth and exit P/E. A sanity check, not a target.
""")
    else:
        st.write("Not enough profit history to estimate.")
with st.expander("Data notes"):
    st.markdown(f"- Prices: **{r.first_date}** to **{r.last_date}**, Yahoo Finance `{sym}.NS`.\n"
                f"- Fundamentals: screener.in, **{r.get('basis')}**, FY{int(r.first_fy) if pd.notna(r.get('first_fy')) else '?'}–FY{int(r.last_fy) if pd.notna(r.get('last_fy')) else '?'}; refreshed {str(r.get('fund_fetched'))[:10]}.\n"
                f"- Price cleaning: {r.get('price_clean_notes') or 'none'}.")
    if a is not None:
        st.dataframe(a.T.rename(columns=lambda d: f"FY{d.year}"), width="stretch")
B.footer()
