# BEEMER — Design Board v2 (India Tech edition)

> **BEEMER** · *Precision research for India's tech stocks.*
> Buffett-grade fundamentals, engineered for first-time investors.

Mood: premium German performance-car interiors and EV dashboards — sleek, precise, dark, quietly powerful.
**Inspiration only.** Beemer uses no BMW logos, roundels, model names, fonts or the M-stripe colours/trade dress;
our tri-stripe uses its own palette (Ice / Cobalt / Signal Red) and our own slanted-bar mark.

## 1. Brand story
India's tech sector — IT services giants, SaaS exporters, AI infrastructure, internet platforms, fintech and
electronics design — is where many first-time investors start, usually via hype: IPO buzz, "AI stock" tips, screenshots of
multibaggers. Warren Buffett famously avoided tech he didn't understand. **Beemer's job is to make it understandable.**

We take 60+ listed Indian tech companies and put each one through the same calm, precise instrument cluster:
*Does it earn high returns? Is it debt-light? Are profits real and steady? Does it have a moat? Is the price sane?*
Every reading comes with a one-line plain-English explanation. Loss-making new-age listings aren't hidden — they're
shown honestly, with how long they've been listed and how far they are from Buffett's tests.

- **Mission:** precision insight, zero jargon — make long-term, Buffett-style thinking usable for India's new investors in tech.
- **Promise:** every number is computed from public data, labelled with its source, and explained in one sentence.
- **Personality:** a performance engineer who's also a great teacher. Confident, exact, understated. Never hype.
- **Taglines:** "Precision research for India's tech stocks." · "Engineered understanding." · "Read the business, not the buzz."

## 2. Logo & wordmark
- **Mark** (`beemer-logo.svg`): three forward-slanted bars rising left→right (Ice, Cobalt, Signal Red) inside a graphite
  rounded square. Reads as a growth chart *and* as motion/speed lines. No circles (avoids any roundel association).
- **Wordmark** (`beemer-wordmark.svg`): BEEMER in Inter Tight SemiBold, all caps, wide tracking (+0.28em), led by the tri-bar mark.
- Clear space = height of the tallest bar. Min size 20px (mark) / 110px (wordmark). Never recolour the bars, never add gradients/glows to the mark.

## 3. Colour palette (dark-first)
| Role | Name | Hex |
|---|---|---|
| App background | Carbon | `#07090D` |
| Surface / cards | Graphite | `#0E121A` |
| Raised surface / inputs | Gunmetal | `#141A24` |
| Hairlines / borders | Hairline | `#1F2733` |
| Primary text | Frost | `#E8ECF3` |
| Secondary text | Titanium | `#8B95A7` |
| Tertiary / disabled | Slate Dim | `#5B6577` |
| Primary accent, links, focus, main series | Electric Blue | `#1F8FFF` |
| Tri-stripe 1 / series 2 | Ice | `#6CC4FF` |
| Tri-stripe 2 | Cobalt | `#2A4BD7` |
| Tri-stripe 3 / alerts (sparingly) | Signal Red | `#F0303F` |
| Positive | Volt Green | `#34D399` |
| Caution / neutral score | Amber | `#F5B83D` |
| Negative | Ember | `#FF4D5E` |
| Tertiary series | Violet | `#8B7CF6` |

Score scale (Buffett Score): `0–39` Ember · `40–59` Amber · `60–74` Electric Blue · `75–100` Volt Green.
Accent discipline: ≤10% of any screen is coloured; colour = meaning.

## 4. Typography
- **Display / headings:** Inter Tight 600 — tight, engineered, high-precision. H1 40/44 (−0.02em), H2 26/32, H3 18/24.
- **Kickers / labels:** Inter Tight 600, ALL CAPS, 11–12px, +0.14em tracking, Titanium colour (instrument-panel labels).
- **Body:** Inter 400/500, 15/24.
- **Data & tickers:** JetBrains Mono 500 for symbols, timestamps and small numeric labels (cockpit read-out feel).
- **KPI numerals:** Inter Tight 600, 30px, tabular figures.

## 5. Chart styling (Plotly template `beemer`)
- Transparent background on Carbon; horizontal gridlines only in `#1A212C`; no axis lines; ticks in Titanium 12px.
- Colorway: Electric Blue, Ice, Amber, Volt Green, Violet, Ember.
- 1.6–2px lines; area fills ≤12% opacity; drawdown (underwater) charts in Ember at 22%.
- Benchmark lines dotted Titanium. Log scale for long price histories with 1-2-5 ₹ ticks (₹1k, ₹1 L, ₹1 Cr).
- Legends below the plot; titles left-aligned in Inter Tight; unified hover with Graphite tooltip and hairline border.
- Every chart has a **"What you're looking at"** caption.

## 6. Components
- **Cards:** Graphite, 1px Hairline, 12px radius, 18–20px padding, no drop shadows; optional 2px top tri-stripe for hero/feature cards.
- **Hero / header bar:** Carbon→Graphite gradient, tri-stripe hairline along the top edge, kicker in caps mono.
- **KPI tiles (instrument cluster):** caps label → big tabular numeral (coloured only when it carries meaning) → one-line explanation.
- **Score gauge:** 270° thin-arc gauge (iDrive-style) with numeric read-out in the centre; also compact pill badges (`82 · STRONG`) with 1px coloured outline + 12% tint.
- **Checklist rows:** status glyph · test name · thin progress rail (4px) · finding · "Why Buffett cares".
- **Tables:** Graphite rows, Hairline separators, mono tickers, progress-rail score columns in Electric Blue.
- **Callouts:** Gunmetal panel, 2px Electric Blue left rule, "💡 In plain English".
- **Disclaimer bar:** Slate Dim micro-copy in every page footer.

## 7. Tone of voice
- Precise, calm, premium. Short sentences. Explain, don't sell.
- Plain English first, the term second: "ROE — profit earned for every ₹100 shareholders put in."
- Honest about uncertainty and short histories: "Listed in 2024 — too young for 10-year tests."
- Never: "multibagger", "rocket", "guaranteed", buy/sell calls, target prices.
- Indian context: ₹, lakh/crore, Nifty IT, SIPs.

## 8. Iconography
Minimal line-style emoji set used consistently as instrument glyphs:
⚙️ Quality/ROE · 🛡️ Debt · 📈 Growth · 🏰 Moat · 💵 Cash · 🏷️ Price · 🤖 AI & data · ☁️ SaaS · 🖥️ IT services · 🛰️ ER&D · 📱 Internet · 💳 Fintech · 🔌 Electronics.
Status: ✅ pass · ⚠️ partial · ❌ fail · — n/a.

## 9. Product narrative (pages)
1. **Cockpit** — India tech at a glance: Nifty IT vs Nifty 50 vs Sensex, sub-sector heat, IPO-era tracker, crashes, SIP simulator.
2. **Screener** — 60+ tech names ranked by Buffett Score; filter by sub-sector, profitability, listing age.
3. **Company** — one-page story: verdict → gauge → checklist → returns → business → valuation.
4. **Academy** — 10 short lessons on investing (and on tech specifically).

*Beemer is an educational tool, not investment advice.*
