import datetime as dt
import numpy as np, pandas as pd
import plotly.graph_objects as go
import streamlit as st
import beemer as B
from beemer import A, C

B.hero("Cockpit · India tech at a glance",
       "Precision research for India's tech stocks.",
       "IT services giants, SaaS exporters, AI infrastructure, internet platforms, fintech and electronics design — "
       "measured with the same calm instruments Warren Buffett uses, and explained in plain English. Every number below is computed from daily market data.")

m = B.load_metrics()
idx = {"Nifty IT": B.load_prices("^CNXIT")["adj_close"], "Nifty 50": B.load_prices("^NSEI")["adj_close"], "Sensex": B.load_prices("^BSESN")["adj_close"]}
it, nf, sx = idx["Nifty IT"], idx["Nifty 50"], idx["Sensex"]
start = max(it.index[0], nf.index[0])

# ---------------- KPI cluster ----------------
k = st.columns(5)
with k[0]: B.kpi(f"Nifty IT · since {it.index[0].year}", B.pct(A.cagr_from_series(it, 'max')) + "/yr", f"vs Nifty 50 {B.pct(A.cagr_from_series(nf[nf.index >= start], 'max'))}/yr over the same period.", "acc")
with k[1]: B.kpi(f"Sensex · since {sx.index[0].year}", B.pct(A.cagr_from_series(sx, 'max')) + "/yr", "India's long-run market return, before dividends.")
cur = A.drawdowns(it).iloc[-1]
with k[2]: B.kpi("Nifty IT vs its peak", B.pct(cur, 1) if cur < -0.001 else "At a high", "How far the IT index sits below its all-time high today.", "neg" if cur < -0.1 else None)
if not m.empty:
    with k[3]: B.kpi("Companies tracked", f"{len(m)}", f"{int(m.profitable_ttm.sum())} profitable over the last 12 months · {int(m.young_listing.sum())} listed < 5 yrs ago.")
    with k[4]: B.kpi("Pass Buffett's tests", f"{int((m.buffett_score >= 60).sum())}", "companies score 60+ (Good or Strong) on our six-test checklist.", "pos")

# ---------------- growth of ₹1 lakh ----------------
st.markdown("### ₹1 lakh, three ways")
fig = go.Figure()
for name, col, dash in [("Nifty IT", C["blue"], None), ("Nifty 50", C["ice"], None), ("Sensex", C["muted"], "dot")]:
    s = idx[name]; s = s[s.index >= start]; v = 1e5 * s / s.iloc[0]
    fig.add_trace(go.Scatter(x=v.index, y=v, name=f"{name}  {B.lakh(v.iloc[-1])}", line=dict(color=col, width=2 if name == "Nifty IT" else 1.5, dash=dash),
                             fill="tozeroy" if name == "Nifty IT" else None, fillcolor="rgba(31,143,255,0.07)"))
B.log_axis(fig, 4e4, float(max((1e5 * idx[n][idx[n].index >= start] / idx[n][idx[n].index >= start].iloc[0]).max() for n in idx)))
fig.update_layout(height=400)
st.plotly_chart(fig, width="stretch")
B.caption(f"one-time ₹1,00,000 invested on {start:%d %b %Y} (the first day Yahoo has Nifty IT data) in each index. Log scale, so equal heights mean equal % moves. "
          "Price indices exclude dividends (≈1–2% a year extra, more for IT, which pays out generously).")

# ---------------- sub-sector board ----------------
if not m.empty:
    st.markdown("### Sub-sector instrument panel")
    g = m.groupby("subsector").agg(companies=("symbol", "count"), score=("buffett_score", "median"), profitable=("profitable_ttm", "mean"),
                                   r1=("cagr_1y", "median"), r3=("cagr_3y", "median"), roe=("roe_median_10y", "median"), pe=("pe", "median")).sort_values("score", ascending=False)
    c1, c2 = st.columns([1.05, 1])
    with c1:
        fig = go.Figure(go.Bar(y=[f"{B.SUB_ICON.get(i,'')} {i}" for i in g.index], x=g.score, orientation="h",
                               marker_color=[B.score_color(v) for v in g.score], text=[f"{v:.0f}" for v in g.score], textposition="outside"))
        fig.update_layout(height=340, title="Median Buffett Score by sub-sector", hovermode=False, yaxis=dict(autorange="reversed", showgrid=False), xaxis=dict(range=[0, 100], showgrid=True, gridcolor=C["grid"]))
        st.plotly_chart(fig, width="stretch")
    with c2:
        t = pd.DataFrame({"Sub-sector": [f"{B.SUB_ICON.get(i,'')} {i}" for i in g.index], "Cos.": g.companies, "Profitable": (g.profitable * 100).round(0),
                          "Median ROE %": (g.roe * 100).round(1), "Median P/E": g.pe.round(1), "1y return %": (g.r1 * 100).round(1), "3y CAGR %": (g.r3 * 100).round(1)})
        st.dataframe(t, hide_index=True, width="stretch", column_config={"Profitable": st.column_config.ProgressColumn("Profitable", min_value=0, max_value=100, format="%d%%")})
        best, worst = g.index[0], g.index[-1]
        B.callout(f"💡 <b>In plain English:</b> <b>{best}</b> companies pass the most Buffett tests (median score {g.score.iloc[0]:.0f}); "
                  f"<b>{worst}</b> pass the fewest ({g.score.iloc[-1]:.0f}) — often because many are young or still loss-making, which Buffett's tests punish by design.")
    B.caption("the median company in each sub-sector. 'Profitable' = share of companies with positive net profit over the last 12 months.")

    # ---------------- new-age listings ----------------
    st.markdown("### The new-age listing tracker")
    y = m[m.listing_year >= 2019].copy()
    if not y.empty:
        p0 = {r.symbol: B.load_prices(r.symbol) for r in y.itertuples()}
        y["since_list"] = [p0[s_]["adj_close"].iloc[-1] / p0[s_]["adj_close"].iloc[0] - 1 for s_ in y.symbol]
        y = y.sort_values("since_list")
        fig = go.Figure(go.Bar(x=y.since_list * 100, y=y.name.str.replace(r" \(.*\)", "", regex=True) + "  " + y.listing_year.astype(str),
                               orientation="h", marker_color=[C["green"] if p else C["ember"] for p in y.profitable_ttm],
                               customdata=np.stack([y.first_date, y.subsector], axis=1),
                               hovertemplate="%{y}<br>First trade %{customdata[0]} · %{customdata[1]}<br>Since first close: %{x:.0f}%<extra></extra>"))
        fig.add_vline(x=0, line_color=C["muted"], line_dash="dot")
        fig.update_layout(height=max(380, 22 * len(y)), title="Return since first trading-day close (green = profitable today, red = loss-making)", hovermode="closest",
                          yaxis=dict(showgrid=False), xaxis=dict(ticksuffix="%", showgrid=True, gridcolor=C["grid"]))
        st.plotly_chart(fig, width="stretch")
        up = (y.since_list > 0).mean(); pu = y[y.profitable_ttm].since_list.median(); lu = y[~y.profitable_ttm].since_list.median()
        B.callout(f"💡 Of <b>{len(y)}</b> tech companies that listed since 2019, <b>{up*100:.0f}%</b> trade above their first-day closing price. "
                  f"Median return for the ones profitable today: <b>{pu*100:+.0f}%</b>; for the ones still losing money: <b>{(lu*100 if pd.notna(lu) else 0):+.0f}%</b>. "
                  "Buffett's view: a listing day is a sale by people who know the business best — the price is rarely a bargain.")
        B.caption("first-day close, not the IPO allotment price (Yahoo doesn't carry IPO prices). Companies listed in the last year are too young for meaningful returns.")

# ---------------- rolling returns ----------------
st.markdown("### Does holding longer help — even in tech?")
roll = {}
s_m = it.resample("ME").last()
for yrs in [1, 3, 5, 10]:
    roll[yrs] = ((s_m / s_m.shift(12 * yrs)) ** (1 / yrs) - 1).dropna()
fig = go.Figure()
for yrs, col, w in [(1, C["ember"], 1.2), (5, C["ice"], 1.5), (10, C["blue"], 2.4)]:
    fig.add_trace(go.Scatter(x=roll[yrs].index, y=roll[yrs] * 100, name=f"{yrs}-year holding", line=dict(color=col, width=w)))
fig.add_hline(y=0, line_color=C["muted"], line_dash="dot")
fig.update_yaxes(ticksuffix="%"); fig.update_layout(height=360, title="Nifty IT · yearly return by holding period")
st.plotly_chart(fig, width="stretch")
c1, c2 = st.columns([1.2, 1])
with c1:
    st.dataframe(pd.DataFrame([{"Holding": f"{y_} yr", "Periods": len(r), "Lost money": f"{(r<0).mean()*100:.0f}%", "Beat 10%/yr": f"{(r>0.10).mean()*100:.0f}%",
                                "Worst": B.pct(r.min()), "Median": B.pct(r.median())} for y_, r in roll.items()]), hide_index=True, width="stretch")
with c2:
    B.callout(f"💡 <b>In plain English:</b> buy the Nifty IT index in a random month and hold <b>1 year</b> — you lost money <b>{(roll[1]<0).mean()*100:.0f}%</b> of the time. "
              f"Hold <b>10 years</b>: <b>{(roll[10]<0).mean()*100:.0f}%</b>, with a median of <b>{roll[10].median()*100:.1f}%</b> a year. Time is the instrument most beginners ignore.")
B.caption("each point = the yearly return if you bought at that month-end and sold N years later (plotted at the sell date).")

# ---------------- crashes ----------------
st.markdown("### Every big tech crash — and the recovery")
ddi = A.drawdowns(it); ep = A.crash_episodes(it, -0.2)
c1, c2 = st.columns([1.3, 1])
with c1:
    fig = go.Figure(go.Scatter(x=ddi.index, y=ddi * 100, fill="tozeroy", line=dict(color=C["ember"], width=1), fillcolor="rgba(255,77,94,0.22)", name="Below peak"))
    fig.update_yaxes(ticksuffix="%"); fig.update_layout(height=330, title="Nifty IT · distance below previous high")
    st.plotly_chart(fig, width="stretch")
with c2:
    if not ep.empty:
        show = pd.DataFrame({"Peak": pd.to_datetime(ep.peak_date).dt.strftime("%b %Y"), "Bottom": pd.to_datetime(ep.trough_date).dt.strftime("%b %Y"),
                             "Fall": ep.fall_pct.map(lambda x: f"{x:.0f}%"), "Months down": ep.months_to_bottom,
                             "Recovered": ep.recovery_date.map(lambda d: d.strftime("%b %Y") if d else "Not yet"), "Months to recover": ep.months_to_recover})
        st.dataframe(show, hide_index=True, width="stretch")
        w = ep.loc[ep.fall_pct.idxmin()]
        B.callout(f"💡 Nifty IT has fallen 20%+ <b>{len(ep)}</b> times since {it.index[0].year}. Worst: <b>{w.fall_pct:.0f}%</b> ({w.peak_date:%b %Y} → {w.trough_date:%b %Y}). "
                  "Buffett: <i>“Be fearful when others are greedy, and greedy when others are fearful.”</i>")
B.caption("zero = a new all-time high; the deeper the red, the more painful it felt to hold.")

# ---------------- SIP simulator ----------------
st.markdown("### SIP simulator")
opts = ["Nifty IT", "Nifty 50", "Sensex"] + ([f"{r.name} ({r.symbol})" for r in m.sort_values("name").itertuples()] if not m.empty else [])
c1, c2, c3 = st.columns(3)
which = c1.selectbox("Invest in", opts)
s = idx[which] if which in idx else B.load_prices(which.split("(")[-1].rstrip(")"))["adj_close"]
yrs_avail = list(range(s.index[0].year + 1, dt.date.today().year)) or [s.index[0].year]
start_y = c2.select_slider("Start year", options=yrs_avail, value=2015 if 2015 in yrs_avail else yrs_avail[0])
amt = c3.number_input("Monthly SIP (₹)", 500, 1_000_000, 10_000, step=500)
r = A.sip(s, amt, f"{start_y}-01-01")
sub = s[s.index >= f"{start_y}-01-01"]; lump_val = r["invested"] * sub.iloc[-1] / sub.iloc[0]
k = st.columns(4)
with k[0]: B.kpi("You put in", B.lakh(r["invested"]), f"{r['months']} monthly instalments since {r['start']:%b %Y}")
with k[1]: B.kpi("SIP worth today", B.lakh(r["value"]), f"{r['value']/r['invested']:.2f}× your money", "pos" if r["value"] > r["invested"] else "neg")
with k[2]: B.kpi("SIP return (XIRR)", (B.pct(r["xirr"]) + "/yr") if r["xirr"] is not None else "–", "True yearly return, counting when each rupee went in.")
with k[3]: B.kpi("Same money, day one", B.lakh(lump_val), f"lump sum at the start ({B.pct(A.cagr_from_series(sub,'max'))}/yr)")
buys = sub.groupby([sub.index.year, sub.index.month]).head(1)
path = pd.DataFrame({"inv": amt * np.arange(1, len(buys) + 1), "val": (amt / buys).cumsum() * buys.values}, index=buys.index) / 1e5
fig = go.Figure()
fig.add_trace(go.Scatter(x=path.index, y=path.inv, name="Money you put in", line=dict(color=C["muted"], dash="dot")))
fig.add_trace(go.Scatter(x=path.index, y=path.val, name="What it was worth", line=dict(color=C["blue"], width=2), fill="tonexty", fillcolor="rgba(31,143,255,0.10)"))
fig.update_yaxes(tickprefix="₹", ticksuffix=" L"); fig.update_layout(height=340)
st.plotly_chart(fig, width="stretch")
B.caption("dotted = total invested; blue = what it was worth each month (₹ lakh). When blue dips under the dotted line, your SIP is buying the most units.")
B.footer()
