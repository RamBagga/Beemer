import streamlit as st
import beemer as B
import belts
from beemer import C

B.hero("Academy · 10 short lessons",
       "Engineered understanding.",
       "How Warren Buffett thinks — and how to apply it to India's tech stocks without getting swept up in hype. Each lesson takes about two minutes.")

q = st.columns(3)
for col, (qt, src) in zip(q, [
        ("“It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price.”", "Berkshire Hathaway shareholder letter, 1989"),
        ("“Price is what you pay. Value is what you get.”", "Berkshire Hathaway shareholder letter, 2008"),
        ("“Never invest in a business you cannot understand.”", "Warren Buffett, widely attributed")]):
    with col:
        st.markdown(f'<div class="bm-card"><div class="bm-quote">{qt}</div><div class="bm-k" style="font-size:.62rem">— {src}</div></div>', unsafe_allow_html=True)
st.write("")

LESSONS = [
    ("01", "A share is a slice of a real business",
     "Owning one share of Infosys means owning a tiny piece of its contracts, engineers and future profits. Prices wiggle every second; over many years they follow one thing — profit. Think like an owner, not a ticker-watcher.",
     "Open any Company page and read the Sales & profit chart before the price chart."),
    ("02", "Know the six kinds of Indian tech",
     "🖥️ IT services sell skilled people-hours to global clients (steady, cash-rich, slower growth). 🛰️ ER&D firms design cars, chips and devices. ☁️ SaaS/software sells products — high margins once built. 🤖 AI & data firms sell analytics, ad-tech or GPU compute. 📱 Internet platforms (food delivery, e-commerce, classifieds) chase scale first, profit later. 💳 Fintech runs payments, broking and insurance distribution. 🔌 Electronics makers assemble and design hardware on thin margins.",
     "Filter the Screener by sub-sector and compare their median scores on the Cockpit."),
    ("03", "Compounding is the real engine",
     "₹1 lakh growing 12% a year becomes about ₹3.1 lakh in 10 years, ₹9.6 lakh in 20 and ₹30 lakh in 30. Most of the money arrives late — which is why staying invested matters more than picking the perfect entry.",
     "Run the SIP simulator on the Cockpit with different start years."),
    ("04", "Quality = high, steady returns on capital",
     "ROE is the profit earned on every ₹100 shareholders own. Indian IT leaders have earned 25–40% for decades with almost no debt — textbook Buffett quality. One good year can be luck; ten is a business.",
     "Sort the Screener by the ⚙️ ROE column."),
    ("05", "Moats in tech are real — but rarer than they look",
     "A moat keeps competitors out: switching costs (core banking software), network effects (marketplaces), scale and reputation (large IT firms). Its footprint is high operating margins that stay high for years. Hype is not a moat.",
     "Check the 🏰 score and the Quality chart on each Company page."),
    ("06", "Why loss-making IPOs score low",
     "Buffett values a business by the cash it will hand to owners over its life. If a company has never made a profit, that cash is a guess. That doesn't mean it's a bad company — it means the price you pay is mostly hope. Our tests say so plainly.",
     "Look at the New-age listing tracker on the Cockpit."),
    ("07", "Cash is a fact",
     "Accounting profit includes estimates; free cash flow doesn't. Mature software and IT firms convert most of their profit into cash. If profit is high but cash never shows up, ask why.",
     "See 'Is profit turning into cash?' on any Company page."),
    ("08", "Price matters, even for great companies",
     "P/E is how many rupees you pay for ₹1 of yearly profit. A great company bought at a crazy P/E can deliver poor returns for a decade. Compare today's P/E with the company's own history, and keep a margin of safety.",
     "Use the 'Below our rough value estimate' filter in the Screener."),
    ("09", "Crashes are part of the ride",
     "The Nifty IT index fell about 61% in 2008–09 and about a third in 2022. Every completed crash in our index data was eventually recovered — though recovery can take years. Those who sold at the bottom locked in the loss.",
     "See the crash table on the Cockpit."),
    ("10", "Behaviour beats stock-picking",
     "Buy with a plan, diversify, keep costs low and give it years. For most people, a low-cost index fund is a perfectly Buffett-approved choice — he has said so himself. Use Beemer to learn and to question tips, not to trade daily.",
     "Compare a single stock's SIP with a Nifty IT SIP in the simulator."),
]
c1, c2 = st.columns(2)
for i, (n, t, body, tryit) in enumerate(LESSONS):
    with (c1 if i % 2 == 0 else c2):
        st.markdown(f'<div class="bm-lesson"><div class="bm-k">Lesson {n}</div><h4>{t}</h4><div style="font-size:.93rem;color:{C['body']};line-height:1.6">{body}</div>'
                    f'<div style="margin-top:10px;font-size:.83rem;color:{C["ice"]}">→ Try it in Beemer: {tryit}</div></div>', unsafe_allow_html=True)

st.markdown("### How Beemer Picks work")
B.callout("💡 <b>In plain English:</b> the moving belts on the Cockpit are <b>data signals, not recommendations</b>. A computer applies the same fixed rules to all "
          "companies after every data update and lists the five that score highest. Nobody hand-edits them, nobody is paid to include a stock, and a pick is never a "
          "prediction or a reason to buy. Think of them as “stocks worth reading about today”, then do the reading on the Company page.")
_bt = (belts.load_picks()[1] or {}).get("backtest") or {}
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div class="bm-lesson"><div class="bm-k" style="color:{C['ice']}">Belt 01 · 1–3 months</div><h4>Short-term momentum</h4>
<div style="font-size:.88rem;color:{C['body']};line-height:1.6"><b>Who qualifies:</b> 200+ trading days of history, price above its 50-day average, beat the Nifty IT index over 3 months, trades ₹2 crore+ a day.<br>
<b>Score:</b> 35% 3-month return vs Nifty IT · 15% 1-month return vs Nifty IT · 20% trend (above 50-day average; 50-day above 200-day) · 10% volume pick-up · 20% latest quarter's sales &amp; profit growth vs a year ago.<br>
<b>Why it can matter:</b> stocks that have been rising with improving results often keep drifting the same way for a while.<br>
<b>Catch:</b> momentum reverses suddenly, and it says nothing about whether the business is worth the price.</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="bm-lesson"><div class="bm-k" style="color:{C['green']}">Belt 02 · 5 years +</div><h4>Long-term compounders</h4>
<div style="font-size:.88rem;color:{C['body']};line-height:1.6"><b>Who qualifies:</b> 5+ years of financials, profitable over the last 12 months, Buffett Score 60+, debt below 1× equity, 3+ years listed.<br>
<b>Score:</b> 40% Buffett Score · 15% ROE above 15% year after year · 15% return on capital (ROCE) · 15% price vs value (margin of safety, P/E vs its own history) · 15% 5-year profit growth.<br>
<b>Why it can matter:</b> this is Buffett's recipe — great businesses at sensible prices, held for years.<br>
<b>Catch:</b> it looks backwards. A great past doesn't guarantee a great future, especially in fast-changing tech.</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="bm-lesson"><div class="bm-k" style="color:{C['amber']}">Belt 03 · last 1–5 days</div><h4>Volatile movers</h4>
<div style="font-size:.88rem;color:{C['body']};line-height:1.6"><b>Who qualifies:</b> 120+ trading days of history, trades ₹1 crore+ a day.<br>
<b>Score:</b> 60% size of the 5-day move compared with the stock's own normal weekly swing · 25% unusual volume vs the previous 60 days · 15% size of the latest day's move. Green = up, red = down.<br>
<b>Why it can matter:</b> big, unusual moves usually mean news — results, a deal, a downgrade. It's a prompt to find out why.<br>
<b>Catch:</b> this belt is a weather report, not a tip. Chasing big moves is how beginners get hurt.</div></div>""", unsafe_allow_html=True)
sb, vb = _bt.get("short") or {}, _bt.get("volatile") or {}
if sb:
    B.callout(f"📏 <b>Honest track record.</b> We re-ran the momentum rules on every month-end from {sb['from']} to {sb['to']} (prices only — we don't have past quarterly results as they were known at the time). "
              f"The top 5 beat the median stock over the next <b>3 months</b> in <b>{sb['hit_rate_3m']*100:.0f}%</b> of months, by a median {sb['median_excess_3m']*100:+.1f} percentage points; "
              f"over the next <b>1 month</b> it was close to a coin flip ({sb['hit_rate_1m']*100:.0f}%). "
              + (f"After the biggest <i>down</i> weeks, those stocks did {vb['after_down_1m_excess']*100:+.1f} pts vs the median over the next month — sharp falls have tended to partly bounce. " if vb else "")
              + "The long-term belt isn't backtested, because today's fundamentals would leak future information into the past. "
              "Caveat: the test uses today's list of companies, so firms that delisted or collapsed are missing — real-world results would likely be a bit worse.")

st.markdown("### Glossary")
cols = st.columns(2)
for i, key in enumerate(B.EXPLAIN):
    t, what, why = B.EXPLAIN[key]
    with cols[i % 2]:
        st.markdown(f"<div style='margin-bottom:12px;font-size:.92rem'><b style='color:{C['text']}'>{t}</b> — {what} <span style='color:{C['muted']}'><i>Buffett's angle:</i> {why}</span></div>", unsafe_allow_html=True)

st.markdown("### A pre-flight checklist before you buy anything")
B.callout("1 · Can I explain how this company makes money in two sentences? &nbsp; 2 · Has it earned 15%+ ROE for most of the last decade? &nbsp; 3 · Is debt low? "
          "&nbsp; 4 · Is it profitable — and have profits grown in most years? &nbsp; 5 · Does profit turn into cash? &nbsp; 6 · Is the P/E sane versus its own history? "
          "&nbsp; 7 · Would I be happy holding it if the market shut for 10 years?")
B.footer()
