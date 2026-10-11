import pandas as pd, numpy as np
import plotly.graph_objects as go
import streamlit as st
import beemer as B
import belts
from beemer import A, C

B.hero("Screener · India tech universe",
       "Which tech companies would Buffett look at twice?",
       "Every company is scored 0–100 on six plain-English tests: high returns on capital, low debt, steady profit growth, "
       "a durable moat, real cash generation and a sensible price. Higher is better — but a score is a starting point for research, not a buy signal.")

m = B.load_metrics()
if m.empty:
    st.warning("Data is still loading — check back in a few minutes."); st.stop()

belts.render(compact=True)

with st.expander("⚙️ Filters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    subs_ = sorted(m.subsector.dropna().unique())
    pick = c1.multiselect("Sub-sector", subs_, placeholder="All sub-sectors", format_func=lambda x: f"{B.SUB_ICON.get(x,'')} {x}")
    min_score = c2.slider("Minimum Buffett Score", 0, 100, 0, 5)
    max_pe = c3.slider("Max P/E", 5, 150, 150, 5, help="150 = no limit. Loss-making companies have no P/E and are kept unless you tick 'Profitable only'.")
    max_de = c4.slider("Max debt / equity", 0.0, 2.0, 2.0, 0.1, help="2.0 = no limit")
    c5, c6, c7, c8 = st.columns(4)
    roe_min = c5.slider("Min median ROE", 0, 40, 0, 1, format="%d%%")
    prof = c6.toggle("Profitable only (last 12 months)", False)
    seasoned = c7.toggle("Listed 5+ years only", False)
    only_mos = c8.toggle("Below our rough value estimate", False)

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
B.callout(f"💡 <b>{len(f)}</b> companies match your filters; <b>{passes}</b> of them score 60+ (“Good” or better). "
          f"<b>{int(f.profitable_ttm.sum())}</b> are profitable; median P/E <b>{f.pe.median():.1f}</b>. Tip: the best Buffett-style ideas usually combine a high score with a "
          f"P/E at or below the company's own history.")

tbl = pd.DataFrame({
    "Company": f.name,
    "Symbol": f.symbol,
    "Sub-sector": f.subsector.map(lambda x: f"{B.SUB_ICON.get(x,'')} {x}"),
    "Buffett Score": f.buffett_score,
    "Verdict": f.score_label,
    "⚙️ ROE": f.sub_roe, "🛡️ Debt": f.sub_debt, "📈 Growth": f.sub_growth, "🏰 Moat": f.sub_moat, "💵 Cash": f.sub_fcf, "🏷️ Price": f.sub_value,
    "Listed": f.listing_year,
    "Profitable": f.profitable_ttm.map({True: "✅", False: "❌"}),
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
sub_cfg = {k: st.column_config.ProgressColumn(k, min_value=0, max_value=100, format="%d", width="small") for k in ["⚙️ ROE", "🛡️ Debt", "📈 Growth", "🏰 Moat", "💵 Cash", "🏷️ Price"]}
event = st.dataframe(
    tbl, hide_index=True, width="stretch", height=min(38 * len(tbl) + 40, 760), on_select="rerun", selection_mode="single-row",
    column_config={
        "Buffett Score": st.column_config.ProgressColumn("Buffett Score", min_value=0, max_value=100, format="%.0f", help="0–100 overall score"),
        **sub_cfg,
        **{k: st.column_config.NumberColumn(k, format="%.1f") for k in ["ROE median %", "ROCE %", "Sales growth 3y %", "Profit growth 5y %", "Op. margin %", "P/E", "P/E vs own history %", "Div. yield %", "Margin of safety %", "1y return %", "5y CAGR %", "Worst fall %"]},
        "Debt/Equity": st.column_config.NumberColumn("Debt/Equity", format="%.2f"),
        "Listed": st.column_config.NumberColumn("Listed", format="%d", help="First year with NSE price data (≈ listing year for new-age companies)"),
        "Mkt cap (₹ cr)": st.column_config.NumberColumn("Mkt cap (₹ cr)", format="%,.0f"),
    })
B.caption("click any row to open that company's story. Sub-score columns (⚙️🛡️📈🏰💵🏷️) show how each company does on each Buffett test, out of 100. "
          "A blank means not enough data for that test. Click a column header to sort.")
sel = event.selection.rows if event and event.selection else []
if sel:
    st.session_state["company"] = tbl.iloc[sel[0]]["Symbol"]
    st.switch_page("views/company.py")

st.markdown("### 🎯 Quality vs price")
q = f.dropna(subset=["roe_median_10y", "pe"]); q = q[q.pe <= 200]
fig = go.Figure(go.Scatter(
    x=q.pe, y=q.roe_median_10y * 100, mode="markers+text", text=q.symbol, textposition="top center", textfont=dict(size=10, color=C["muted"], family="JetBrains Mono"),
    marker=dict(size=np.clip(np.sqrt(q.market_cap_cr.fillna(1e4)) / 22, 7, 34), color=[B.score_color(s) for s in q.buffett_score],
                line=dict(color=C["bg"], width=1), opacity=.9),
    customdata=np.stack([q.name, q.buffett_score], axis=1),
    hovertemplate="<b>%{customdata[0]}</b><br>P/E %{x:.1f}<br>ROE (10y median) %{y:.1f}%<br>Buffett Score %{customdata[1]:.0f}<extra></extra>"))
fig.add_hline(y=15, line_dash="dot", line_color=C["green"], annotation_text="Buffett's 15% ROE bar", annotation_position="top left")
fig.update_xaxes(type="log", title="P/E — price you pay (log scale) →  more expensive", tickvals=[5, 10, 20, 30, 50, 100, 200], ticktext=["5", "10", "20", "30", "50", "100", "200"])
fig.update_yaxes(title="Quality — median ROE over 10 years (%)")
fig.update_layout(height=520, hovermode="closest")
st.plotly_chart(fig, width="stretch")
B.caption("(companies with P/E above 200 are left off the chart.) Each bubble is a company (size = market value, colour = Buffett Score). The sweet spot Buffett hunts for is the <b>top-left</b>: high, durable returns on capital at a modest price. "
          "Top-right = great businesses the market already loves (and prices accordingly).")

with st.expander("📖 How the Buffett Score works"):
    st.markdown("""
| Test | Points | What we check | Why Buffett cares |
|---|---|---|---|
| ⚙️ High, consistent ROE | 20 | Years with ROE > 15% (last 10) + median ROE | Proof the business earns well on owners' money |
| 🛡️ Low debt | 15 | Debt/equity (0.1 or less = full marks, 1.5+ = zero) | Debt turns bad years into disasters |
| 📈 Steady earnings growth | 20 | Years profit grew (last 10), 10-year profit CAGR, loss years | Predictable earnings are easier to value |
| 🏰 Moat (margins) | 15 | Level and stability of operating margin over 10 years | Stable high margins = pricing power competitors can't break |
| 💵 Free cash flow | 15 | Years with positive FCF, FCF ÷ net profit | Profit is an opinion, cash is a fact |
| 🏷️ Sensible price | 15 | P/E vs company's own 10-year median, margin of safety vs rough intrinsic value | Even great businesses are bad buys if you overpay |

Tests without enough data are skipped and the score is rescaled to 100. Young listings have only a few years of results, so their scores rest on less evidence.
Loss-making companies score low by design: Buffett only buys businesses whose future earnings he can estimate.
Fundamentals: up to ~12 financial years from screener.in public pages (consolidated where available). Intrinsic value: 10 years of earnings growing at the
median of the company's 10y sales growth, 10y and 5y profit growth (capped at 18%), paying out its usual dividend share, then valued at P/E 15
(or its historical median if lower), all discounted at 12% a year. It is deliberately simple — treat it as a sanity check, not a target price.
""")
B.footer()
