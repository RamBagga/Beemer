import streamlit as st
import beemer as B
import belts
from beemer import C

B.hero("Academy",
       "Engineered understanding.",
       "Buffett's principles, applied to Indian tech.")

q = st.columns(3)
for col, (qt, src) in zip(q, [
        ("“It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price.”", "Shareholder letter, 1989"),
        ("“Price is what you pay. Value is what you get.”", "Shareholder letter, 2008"),
        ("“Never invest in a business you cannot understand.”", "Warren Buffett")]):
    with col:
        st.markdown(f'<div class="bm-card"><div class="bm-quote">{qt}</div><div class="bm-k" style="font-size:.62rem">{src}</div></div>', unsafe_allow_html=True)
st.write("")

LESSONS = [
    ("01", "A share is a business.",
     "One Infosys share is a slice of its contracts, people and future profit. Prices follow profit over time.",
     "Read the sales and profit chart before the price chart."),
    ("02", "Seven kinds of Indian tech.",
     "IT services sell expertise. ER&D designs products. SaaS sells software. AI & data sells insight and compute. Internet platforms chase scale. Fintech moves money. Electronics builds hardware on thin margins.",
     "Compare sub-sectors on the Cockpit."),
    ("03", "Compounding does the work.",
     "₹1 lakh at 12% a year: ₹3.1 lakh in 10 years, ₹9.6 lakh in 20, ₹30 lakh in 30. Most of it arrives late.",
     "Run the SIP simulator with different start years."),
    ("04", "Quality is return on capital.",
     "ROE is profit per ₹100 of owners' money. The best Indian IT firms have earned 25–40% for decades, with little debt.",
     "Sort the Screener by ROE test."),
    ("05", "Moats are rare.",
     "Switching costs, networks and scale keep rivals out. The evidence: high margins that hold for years. Hype is not a moat.",
     "Check the Moat test on any company."),
    ("06", "Losses mean guesswork.",
     "No profit history, no reliable value. Loss-making listings score low by design, not by judgement.",
     "Open the New-age listings chart on the Cockpit."),
    ("07", "Cash is a fact.",
     "Profit includes estimates. Free cash flow doesn't. If profit never turns into cash, ask why.",
     "See Profit vs free cash flow on any company."),
    ("08", "Price still matters.",
     "Overpay for a great company and returns can stall for a decade. Compare P/E with its own history.",
     "Filter the Screener: Below value estimate."),
    ("09", "Drawdowns are normal.",
     "Nifty IT fell about 61% in 2008–09 and has recovered from every completed fall since. Selling at the bottom made losses permanent.",
     "Review Drawdowns on the Cockpit."),
    ("10", "Behaviour beats picking.",
     "Plan, diversify, keep costs low, give it years. A low-cost index fund passes Buffett's test.",
     "Compare a stock SIP with a Nifty IT SIP."),
]
c1, c2 = st.columns(2)
for i, (n, t, body, tryit) in enumerate(LESSONS):
    with (c1 if i % 2 == 0 else c2):
        st.markdown(f'<div class="bm-lesson"><div class="bm-k">Lesson {n}</div><h4>{t}</h4><div style="font-size:.93rem;color:{C["body"]};line-height:1.6">{body}</div></div>',
                    unsafe_allow_html=True)

st.markdown("### How Beemer Picks work")
B.callout("<b>Data signals, not recommendations.</b> Fixed rules, rerun after every data update. Top five per belt.")
_bt = (belts.load_picks()[1] or {}).get("backtest") or {}


def belt_card(col, color, kicker, title, rows):
    body = "".join(f"<div style='margin:4px 0'><span class='bm-k' style='font-size:.6rem'>{k}</span><br>{v}</div>" for k, v in rows)
    col.markdown(f'<div class="bm-lesson"><div class="bm-k" style="color:{color}">{kicker}</div><h4>{title}</h4>'
                 f'<div style="font-size:.88rem;color:{C["body"]};line-height:1.55">{body}</div></div>', unsafe_allow_html=True)


c1, c2, c3 = st.columns(3)
belt_card(c1, C["blue"], "Belt 01 · 1–3 months", "Momentum", [
    ("Qualifies", "200+ trading days. Above 50-day average. Ahead of Nifty IT over 3 months. ₹2 cr+ traded daily."),
    ("Weights", "35% 3-month vs Nifty IT · 15% 1-month · 20% trend · 10% volume · 20% latest-quarter growth."),
    ("Limit", "Momentum reverses without warning. It says nothing about value.")])
belt_card(c2, C["teal"], "Belt 02 · 5 years +", "Compounders", [
    ("Qualifies", "5+ years of results. Profitable. Buffett Score 60+. Debt under 1× equity. Listed 3+ years."),
    ("Weights", "40% Buffett Score · 15% ROE consistency · 15% ROCE · 15% price vs value · 15% profit growth."),
    ("Limit", "Backward-looking. Tech changes fast.")])
belt_card(c3, C["violet"], "Belt 03 · last 5 days", "Movers", [
    ("Qualifies", "120+ trading days. ₹1 cr+ traded daily."),
    ("Weights", "60% 5-day move vs normal swing · 25% unusual volume · 15% last-session move."),
    ("Limit", "A prompt to find the news. Not a reason to chase.")])
sb, vb = _bt.get("short") or {}, _bt.get("volatile") or {}
if sb:
    B.callout(f"<b>Track record, {sb['from']} to {sb['to']}.</b> Momentum top 5 beat the median stock over 3 months in <b>{sb['hit_rate_3m']*100:.0f}%</b> of months "
              f"(median {sb['median_excess_3m']*100:+.1f} pts). Over 1 month: {sb['hit_rate_1m']*100:.0f}%. "
              + (f"After sharp falls, Movers did {vb['after_down_1m_excess']*100:+.1f} pts vs median the next month. " if vb else "")
              + "Compounders not backtested. Price-only test on today's list, so results flatter slightly.")

st.markdown("### Glossary")
cols = st.columns(2)
for i, key in enumerate(B.EXPLAIN):
    t, what, why = B.EXPLAIN[key]
    with cols[i % 2]:
        st.markdown(f"<div style='margin-bottom:12px;font-size:.92rem'><b style='color:{C['text']}'>{t}.</b> {what} <span style='color:{C['muted']}'>{why}</span></div>", unsafe_allow_html=True)

st.markdown("### Before you invest")
items = ["Explain how it makes money, in two sentences.", "ROE 15%+ for most of a decade.", "Low debt.", "Profitable, and growing most years.",
         "Profit turns into cash.", "P/E sane against its own history.", "Happy to hold if the market closed for 10 years."]
st.markdown('<div class="bm-card">' + "".join(
    f'<div style="display:flex;gap:14px;padding:7px 0;border-bottom:1px solid {C["line"]}"><span class="bm-mono">{i:02d}</span>'
    f'<span style="color:{C["body"]}">{t}</span></div>' for i, t in enumerate(items, 1)) + "</div>", unsafe_allow_html=True)
B.footer()
