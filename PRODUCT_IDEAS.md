# Beemer — product ideas

How to turn Beemer from a good dashboard into something Indian retail investors (beginner → amateur) will
use every week and pay for. Ideas are prioritised inside each group. **Effort:** S = days, M = 1–3 weeks,
L = a month or more.

> Ground rules for everything below: Beemer explains and measures; it doesn't tell people what to buy.
> Anything that looks like a personalised "buy/sell/target" is SEBI Research Analyst (RA) or
> Investment Adviser (IA) territory. Free public data (Yahoo, NSE website, screener.in) is fine for a
> personal/prototype build but **not licensed for a commercial product** — see #9.

## Top 5 (do these first)

| # | Idea | Why first |
|---|---|---|
| 1 | **Watchlist + smart alerts** (#1) | The habit loop. Gives people a reason to come back every day and the hook for paid tiers. |
| 2 | **"Explain like I'm 15" results summaries** (#5) | The clearest differentiator vs Screener/Tickertape for beginners; every quarter creates fresh content. |
| 3 | **Licensed data + SEBI-safe framing** (#9) | Hard blocker for charging money. Start the vendor + legal conversations now; they take weeks. |
| 4 | **Portfolio X-ray via CAS upload** (#6) | "Upload one PDF, see your whole portfolio through Buffett's eyes" — the strongest acquisition hook. |
| 5 | **Shareable cards for X / Instagram / WhatsApp** (#12) | Free distribution. Every Beemer Pick and Company story becomes a branded image people share. |

---

## A. Must-have for launch

### 1. Watchlist + smart alerts (email, Telegram, WhatsApp) — **M**
- **Value:** "Tell me when something I care about changes" — a stock enters/leaves a Beemer Picks belt, its Buffett Score moves 5+ points, results are out, or it falls 20% from its high.
- **Build:** accounts (Supabase/Firebase auth), a `watchlists` table, an alert job that runs after `update_data.py`. Email (Resend/SES) and Telegram bot first — both free/cheap. WhatsApp via the Business API costs ~₹0.1–0.8 per message and needs template approval.
- **Regulatory:** alerts must state facts ("score fell from 78 to 71 because debt rose"), never "sell now".

### 2. Earnings calendar + results-day tracker — **S**
- **Value:** see which tech companies report this week, and the day after: sales/profit vs last year in plain English, with the score change.
- **Data:** results dates and filings are public on NSE/BSE corporate announcements. Scraping them commercially still needs care; licensed vendors bundle this.
- **Regulatory:** fine as factual reporting.

### 3. Peer comparison ("TCS vs Infosys vs HCLTech") — **S**
- **Value:** side-by-side instrument cluster for 2–4 companies: score breakdown, ROE, margins, growth, valuation vs history, a 10-year ₹1 lakh race chart.
- **Build:** pure UI on data we already have. Great SEO landing pages ("TCS vs Infosys").
- **Regulatory:** none beyond the standard disclaimer.

### 4. Accounts, onboarding quiz and a "first 30 days" path — **S/M**
- **Value:** a 5-question quiz (goal, horizon, how a 30% fall would feel) sets the tone, then a guided path through the Academy plus 3 companies to study. Turns a dashboard into a course.
- **Regulatory:** don't map quiz answers to specific stocks (that becomes personalised advice). Map them to *lessons* and *tools*.

## B. Differentiators

### 5. "Explain like I'm 15" AI summaries of results and concalls — **M**
- **Value:** every quarterly result and earnings-call transcript turned into 5 bullet points: what happened, why, what management promised, red flags, how it moves the Buffett tests. Includes a "what changed since last quarter" diff of management promises.
- **Data:** filings and transcripts are public on BSE/NSE. Use an LLM with strict grounding (quotes + page links), and keep a human review for the first few months.
- **Regulatory:** summarise, don't recommend. Label it as AI-generated and link the source filing.

### 6. Portfolio X-ray via CAS upload — **M/L**
- **Value:** upload the NSDL/CDSL Consolidated Account Statement PDF (password = PAN + DOB) and get: Buffett Score of the whole portfolio, sector concentration, overlap with Nifty, which holdings are loss-makers, and an XIRR vs Nifty 50.
- **Build:** parse locally/in memory with `casparser`-style logic; **don't store the PDF**. Later: Account Aggregator integration (via a licensed AA/FIU partner) for automatic sync.
- **Regulatory:** this is sensitive personal financial data (DPDP Act 2023: consent, purpose limitation, deletion). Keep insights descriptive ("41% of your money is in loss-making companies"), never "sell X".

### 7. Story mode for every company — **M**
- **Value:** a scroll-driven, 60-second story: what the company does, 10 years in 6 charts, its best and worst moments (crash table, listing day), what Buffett would like and dislike. Built for phones.
- **Build:** templated from existing analytics, with an AI-written narrative reviewed for accuracy. Doubles as content for #12.

### 8. "What would Buffett ask?" checklist journal — **S**
- **Value:** before buying anything, the user answers the 7 pre-flight questions from the Academy. Beemer saves the answers and resurfaces them after 6 and 12 months ("You bought because of X — is it still true?").
- **Why it's different:** it teaches behaviour, not stock tips. Hard to copy and very on-brand.

## C. Monetisation

### 9. Licensed data + SEBI path (enabler, not a feature) — **L**
- **Data:** for commercial use, license EOD prices and fundamentals. Options: NSE Data & Analytics (EOD/historical feeds; annual licence, typically ₹ lakhs per year plus display fees), BSE data products, or a vendor such as CMOTS, Accord Fintech, ACE Equity or TrueData. Budget roughly ₹3–15 lakh/year for an EOD + fundamentals bundle at startup scale (our estimate: get quotes); ask for display-only, small-redistribution pricing. Swap the two fetch functions in `update_data.py`.
- **SEBI:** stay educational (no personalised advice, no buy/sell calls, no target prices) **or** register as a Research Analyst (individual RA registration: NISM Series XV certification, relevant qualification, net-worth/deposit requirements, and compliance such as disclosures and grievance handling). Ratings and "picks" sold to paying users are the grey zone. Get a securities lawyer to review the Picks copy before charging.
- **Also:** the SEBI (Investment Advisers/RA) rules on "finfluencers" and on past-performance claims apply to marketing.

### 10. Freemium tiers — **S** (once #1 and #9 are in place)
- **Free:** Cockpit, Screener, 3 company stories a day, Academy, belts with a 1-day delay.
- **Beemer Plus (~₹149/month or ₹1,199/year):** watchlist alerts, results summaries, peer compare, full story mode, CSV export.
- **Beemer Pro (~₹399/month):** portfolio X-ray, unlimited alerts incl. WhatsApp, concall diffs, API/Sheets export.
- **Payments:** Razorpay subscriptions (UPI Autopay). Price anchors (check current pricing): Screener Premium and Tickertape Pro both charge a few thousand rupees a year, so undercut them and target beginners.

### 11. B2B: white-label "investor education" widgets — **M**
- **Value:** brokers, finance creators and fintech apps embed Beemer's Buffett Score card or the Academy. Recurring licence revenue without retail churn.
- **Regulatory:** the partner carries the client relationship. The data licence must allow redistribution, which usually costs more.

## D. Growth and virality

### 12. Shareable cards (X, Instagram, WhatsApp status) — **S**
- **Value:** one tap makes a branded 1080×1350 image: "Infosys — Buffett Score 93 · ROE > 15% in 10 of 10 years · P/E 38% below its 10-yr norm", or this week's Beemer Picks belts. Each card carries the Beemer mark and a short link.
- **Build:** server-side rendering with Playwright or `satori`, plus Open Graph images so every company link previews nicely.
- **Regulatory:** keep the "data signals, not recommendations" line on every card.

### 13. Weekly "Beemer Brief" newsletter + Telegram channel — **S**
- **Value:** every Sunday: belt changes, results that moved scores, one Academy lesson, one chart. It's the cheapest retention and acquisition channel there is.
- **Build:** generated from the picks history table (already stored per run) and reviewed by a human before sending.

### 14. Public, honest "signal scoreboard" — **S**
- **Value:** a page that tracks every past Beemer Picks belt and how it did afterwards (we already store each snapshot in `picks`). Radical transparency builds trust and is very shareable, and it's rare among Indian tools.
- **Regulatory:** past-performance displays need careful, balanced framing and must include the bad periods.

### 15. SEO "explainers" for every stock and term — **M**
- **Value:** auto-generated, human-reviewed pages such as "Is TCS debt-free?", "What is ROCE?" and "Zomato (Eternal) profit history". These capture the long tail of beginner searches.
- **Build:** move to a crawlable front end (Next.js or Astro) that reads the same `metrics.parquet`/API. Streamlit pages aren't SEO-friendly.

---

### Suggested sequencing
1. **Weeks 0–2:** #3 peer compare, #2 earnings calendar, #12 share cards, and open conversations with data vendors and a lawyer (#9).
2. **Weeks 2–6:** accounts + #1 watchlist/alerts (email + Telegram), #13 newsletter, #14 scoreboard.
3. **Weeks 6–12:** #5 AI results summaries, #6 CAS X-ray, #10 paid tiers on licensed data.
4. **Later:** #7 story mode, #15 SEO front end, #11 B2B.
