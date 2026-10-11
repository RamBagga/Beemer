import pandas as pd, numpy as np
import plotly.graph_objects as go
import streamlit as st
import beemer as B
import belts
from beemer import A, C

B.hero("Screener",
       "Quality first. Then price.",
       "Ranked by Buffett Score, 0–100, across six tests.")

m = B.load_metrics()
if m.empty:
    st.warning("Data is loading. Back in a few minutes."); st.stop()

belts.render(compact=True)

with st.expander("Filters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    subs_ = sorted(m.subsector.dropna().unique())
    pick = c1.multiselect("Sub-sector", subs_, placeholder="All sub-sectors", format_func=lambda x: x)
    min_score = c2.slider("Minimum Buffett Score", 0, 100, 0, 5)
    max_pe = c3.slider("Max P/E", 5, 150, 150, 5, help="150 = no limit. Loss-makers have no P/E; use Profitable only to exclude them.")
    max_de = c4.slider("Max debt / equity", 0.0, 2.0, 2.0, 0.1, help="2.0 = no limit")
    c5, c6, c7, c8 = st.columns(4)
    roe_min = c5.slider("Min median ROE", 0, 40, 0, 1, format="%d%%")
    prof = c6.toggle("Profitable only", False, help="Positive net profit, last 12 months.")
    seasoned = c7.toggle("Listed 5+ years", False)
    only_mos = c8.toggle("Below value estimate", False)

f = m.copy()
if pick: f = f[f.subsector.isin(pick)]
f = f[f.buffett_score.fillna(0) >= min_score]
if max_pe < 150: f = f[f.pe.isna() | (f.pe <= max_pe)]
if max_de < 2.0: f = f[f.debt_to_equity.isna() | (f.debt_to_equity <= max_de)]
f = f[f.roe_median_10y.fillna(-1) >= roe_min / 100] if roe_min > 0 else f
if prof: f = f[f.profitable_ttm]
if seasoned: f = f[~f.young_listing]
if only_mos: f = f[f.margin_of_safety > 0]
f = f.sort_values("buffett_score", ascending=False)

passes = f.buffett_score.ge(60).sum()
B.callout(f"<b>{len(f)}</b> matches. <b>{passes}</b> score 60+. <b>{int(f.profitable_ttm.sum())}</b> profitable. Median P/E <b>{f.pe.median():.1f}</b>.")

tbl = pd.DataFrame({
    "Company": f.name,
    "Symbol": f.symbol,
    "Sub-sector": f.subsector,
    "Buffett Score": f.buffett_score,
    "Verdict": f.score_label,
    "ROE test": f.sub_roe, "Debt test": f.sub_debt, "Growth test": f.sub_growth, "Moat test": f.sub_moat, "Cash test": f.sub_fcf, "Price test": f.sub_value,
    "Listed": f.listing_year,
    "Profitable": f.profitable_ttm.map({True: "Yes", False: "No"}),
    "ROE median %": f.roe_median_10y * 100,
    "ROCE %": f.roce_median_10y * 100,
    "Debt/Equity": f.debt_to_equity,
    "Sales growth 3y %": f.sales_cagr_3y * 100,
    "Profit growth 5y %": f.profit_cagr_5y * 100,
    "Op. margin %": f.opm_median_10y * 100,
    "P/E": f.pe, "P/E vs own history %": f.pe_vs_history * 100,
    "Div. yield %": f.dividend_yield * 100,
    "Margin of safety %": f.margin_of_safety * 100,
    "1y return %": f.cagr_1y * 100, "5y CAGR %": f.cagr_5y * 100, "Worst fall %": f.max_drawdown * 100,
    "Mkt cap (₹ cr)": f.market_cap_cr,
})
sub_cfg = {k: st.column_config.NumberColumn(k, width="small") for k in ["ROE test", "Debt test", "Growth test", "Moat test", "Cash test", "Price test"]}
signed = ["1y return %", "5y CAGR %", "Margin of safety %", "P/E vs own history %", "Worst fall %"]
def _tone(v, invert=False):
    if pd.isna(v) or v == 0: return ""
    good = (v < 0) if invert else (v > 0)
    return f"color:{C['pos_t'] if good else C['neg_t']};font-weight:600"
tests = ["Buffett Score", "ROE test", "Debt test", "Growth test", "Moat test", "Cash test", "Price test"]
styled = (tbl.style
          .map(lambda v: B.heat(v), subset=tests)
          .map(lambda v: B.heat(v, signed=True, cap=.6), subset=["1y return %", "5y CAGR %", "Margin of safety %"])
          .map(lambda v: B.heat(-v if pd.notna(v) else v, signed=True, cap=.6), subset=["P/E vs own history %"])
          .map(lambda v: f"color:{B.sub_color(v)};font-weight:600", subset=["Sub-sector"])
          .map(lambda v: f"color:{B.ink(B.score_color({'Strong': 80, 'Good': 65, 'Mixed': 50, 'Weak': 20}.get(v, None)))};font-weight:650" if v in ('Strong', 'Good', 'Mixed', 'Weak') else "", subset=["Verdict"])
          .format("{:.0f}", subset=tests, na_rep="–")
          .format("{:.1f}", subset=["ROE median %", "ROCE %", "Sales growth 3y %", "Profit growth 5y %", "Op. margin %", "P/E", "P/E vs own history %", "Div. yield %", "Margin of safety %", "1y return %", "5y CAGR %", "Worst fall %"], na_rep="–")
          .format("{:.2f}", subset=["Debt/Equity"], na_rep="–")
          .format("{:,.0f}", subset=["Mkt cap (₹ cr)"], na_rep="–")
          .map(lambda v: f"color:{C['pos_t'] if v == 'Yes' else C['neg_t']};font-weight:600", subset=["Profitable"])
          .map(lambda v: "font-weight:650", subset=["Company"]))
event = st.dataframe(
    styled, hide_index=True, width="stretch", row_height=40, height=min(40 * len(tbl) + 42, 800), on_select="rerun", selection_mode="single-row",
    column_config={
        "Buffett Score": st.column_config.NumberColumn("Buffett Score", help="0–100 overall score", width="small"),
        **sub_cfg,
        "Sub-sector": st.column_config.TextColumn("Sub-sector", width="medium"),
        "Company": st.column_config.TextColumn("Company", width="medium"),

        "Listed": st.column_config.NumberColumn("Listed", format="%d", help="First year with NSE price data (≈ listing year for new-age companies)"),
    })
B.caption("Select a row to open the company. Blank: too little data.")
sel = event.selection.rows if event and event.selection else []
if sel:
    st.session_state["company"] = tbl.iloc[sel[0]]["Symbol"]
    st.switch_page("views/company.py")

st.markdown("### Quality vs price")
q = f.dropna(subset=["roe_median_10y", "pe"]); q = q[q.pe <= 200]
fig = go.Figure(go.Scatter(
    x=q.pe, y=q.roe_median_10y * 100, mode="markers+text", text=q.symbol, textposition="top center", textfont=dict(size=10, color=C["muted"], family="JetBrains Mono"),
    marker=dict(size=np.clip(np.sqrt(q.market_cap_cr.fillna(1e4)) / 22, 7, 34), color=[B.score_color(s) for s in q.buffett_score],
                line=dict(color=C["surface"], width=1.2), opacity=.88),
    customdata=np.stack([q.name, q.buffett_score], axis=1),
    hovertemplate="<b>%{customdata[0]}</b><br>P/E %{x:.1f}<br>ROE (10y median) %{y:.1f}%<br>Buffett Score %{customdata[1]:.0f}<extra></extra>"))
fig.add_hline(y=15, line_dash="dot", line_width=1, line_color=C["teal"], annotation_text="15% ROE", annotation_position="top left", annotation_font=dict(color=C["teal"], size=11))
fig.update_xaxes(type="log", title="P/E, log scale", tickvals=[5, 10, 20, 30, 50, 100, 200], ticktext=["5", "10", "20", "30", "50", "100", "200"])
fig.update_yaxes(title="ROE, 10-yr median (%)")
fig.update_layout(height=520, hovermode="closest", xaxis_showspikes=False, yaxis_showspikes=False)
st.plotly_chart(fig, width="stretch")
B.caption("Size: market cap. Colour: Buffett Score. P/E above 200 hidden.")

with st.expander("How the Buffett Score works"):
    st.markdown("""
| Test | Points | Measures |
|---|---|---|
| Return on equity | 20 | Years above 15% ROE (last 10), median ROE |
| Debt | 15 | Debt/equity: 0.1 or less full marks, 1.5+ zero. Lenders: return on assets |
| Earnings consistency | 20 | Years profit grew, 10-yr profit growth, loss years |
| Moat | 15 | Level and stability of operating margin, 10 years |
| Cash generation | 15 | Years of positive free cash flow, cash vs profit |
| Price | 15 | P/E vs own 10-yr median, margin of safety vs value estimate |

Tests without enough data are skipped and the score rescaled to 100. Young listings score on thin evidence. Loss-makers score low by design.

**Value estimate.** 10 years of earnings growing at the median of 10-yr sales, 10-yr and 5-yr profit growth (capped at 18%), the usual dividend paid out, then valued at P/E 15 (or the historical median if lower). Discounted at 12% a year. A sanity check, not a target.

**Sources.** Up to 12 years of financials from screener.in public pages, consolidated where available.
""")

B.footer()
