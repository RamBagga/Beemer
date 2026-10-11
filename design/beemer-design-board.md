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

## 3. Colour palettes — Studio (light, default) and Night drive (dark)

Beemer opens in **Studio**: a bright, precise light theme that feels like a car-configurator showroom, with porcelain floors,
brushed-silver surfaces, crisp ink type and one electric-blue accent. **Night drive** is the original dark cockpit; viewers switch
with the Studio / Night switch in the sidebar, and the choice is remembered per browser. Tokens live in `app/beemer.py` (`PALETTES`)
and `.streamlit/config.toml`; never hard-code a hex in a view.

### 3a. Studio (light, default)
| Role | Name | Hex |
|---|---|---|
| App background | Porcelain | `#F4F6F9` |
| Cards / surfaces | Paper | `#FFFFFF` |
| Raised surface / inputs / table header | Mist | `#EEF2F7` |
| Sidebar | Brushed Silver | `#EDF0F4` |
| Hairlines / borders | Silver | `#DDE3EB` |
| Chart gridlines | Frost Line | `#E9EDF2` |
| Primary text / headings | Ink | `#0B1220` |
| Body copy | Graphite | `#2B3444` |
| Secondary text | Steel | `#5B6577` |
| Tertiary / disclaimers | Pewter | `#8A94A6` |
| Primary accent, focus, main series | Electric Blue | `#1F8FFF` (same as dark) |
| Accent text, tickers, links | Deep Ice | `#0A72D1` (Ice darkened for AA contrast on white) |
| Positive | Volt Green (deep) | `#0E9F6E` |
| Caution / neutral score | Amber (deep) | `#B7791F` |
| Negative | Ember (deep) | `#E0364A` |
| Tertiary series | Violet (deep) | `#6D5AE6` |
| Neutral bars (e.g. sales) | Steel Blue Tint | `#BFD3EE` |

- **Elevation:** light needs depth, so cards, hero and lessons get one soft two-layer shadow:
  `0 1px 2px rgba(15,23,42,.04), 0 12px 28px -16px rgba(15,23,42,.22)`. No other shadows.
- **Hero:** Paper → Mist diagonal gradient (`#FFFFFF → #F3F6FA → #E8EDF4`), with the tri-stripe hairline along the top edge.
- **Picks belts:** the conveyor is a brushed-aluminium belt (slats `#AEB8C6` / `#D9DFE7`) with polished-silver rollers under a soft
  studio spotlight. Cards are white; outside the spotlight they fade and desaturate rather than darken.
- **Wordmark:** `beemer-wordmark-light.svg` uses Ink text. The tri-bar mark and its graphite tile are unchanged.
- **Brand tri-stripe is theme-independent:** Ice `#6CC4FF` · Cobalt `#2A4BD7` · Signal Red `#F0303F`.

### 3b. Night drive (dark)
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
- Transparent background (Porcelain in Studio, Carbon in Night drive); horizontal gridlines only (`#E9EDF2` light / `#1A212C` dark); no axis lines; ticks in Steel / Titanium 12px. Two Plotly templates: `beemer_light` (default) and `beemer_dark`.
- Colorway: Electric Blue, Ice, Amber, Volt Green, Violet, Ember.
- 1.6–2px lines; area fills ≤12% opacity; drawdown (underwater) charts in Ember at 22%.
- Benchmark lines dotted Titanium. Log scale for long price histories with 1-2-5 ₹ ticks (₹1k, ₹1 L, ₹1 Cr).
- Legends below the plot; titles left-aligned in Inter Tight; unified hover with Graphite tooltip and hairline border.
- Every chart has a **"What you're looking at"** caption.

## 6. Components
- **Cards:** Graphite, 1px Hairline, 12px radius, 18–20px padding, no drop shadows; optional 2px top tri-stripe for hero/feature cards.
- **Hero / header bar:** Paper→Mist gradient with a soft shadow in Studio (Graphite→Carbon in Night drive), tri-stripe hairline along the top edge, kicker in caps mono.
- **KPI tiles (instrument cluster):** caps label → big tabular numeral (coloured only when it carries meaning) → one-line explanation.
- **Score gauge:** 270° thin-arc gauge (iDrive-style) with numeric read-out in the centre; also compact pill badges (`82 · STRONG`) with 1px coloured outline + 12% tint.
- **Checklist rows:** status tag (`PASS` green · `WATCH` amber · `FAIL` ember, mono caps, 1px outline) · test name · 4px progress rail · finding · one-line reason.
- **Tables:** Graphite rows, Hairline separators, mono tickers, progress-rail score columns in Electric Blue.
- **Callouts:** raised panel, 2px Electric Blue left rule. One or two sentences, key figures in bold. No label, no icon.
- **Disclaimer bar:** one compact disclaimer in the footer of every page, then "Made with ❤️ by baggak8s" (the only emoji in the product).

## 7. Tone of voice — automotive precision
Write like a performance-car product page: short, declarative, confident. Every word earns its place.

**Rules**
- **No emoji, no decorative symbols.** Not in headings, buttons, labels, badges, tables or docs. The single exception is the footer
  credit "Made with ❤️ by baggak8s". Functional data glyphs are allowed: ▲ ▼ for price direction, · as a separator, × for multiples.
- **Sentence length:** headings 2–5 words. Hero lines under 8 words. Body sentences under 15 words. Captions: one line.
  Callouts: at most two sentences. If it needs a paragraph, it belongs in an expander or the Academy.
- **No exclamation marks. No questions as headings.** State, don't tease ("Drawdowns", not "Every big crash — and the recovery?").
- **Numbers carry the message.** Bold the figure, not the adjective: "Held 10 years: **0%** lost money."
- **Plain English stays.** Define a term in one line, the first time: "ROE. Profit per ₹100 of shareholders' capital."
- **Honest by default.** State limits plainly: "Treat the score as provisional." "Not backtested."
- **Compliance line, verbatim:** "Data signals, not recommendations." Never "buy", "sell", "prediction", "target", "multibagger",
  "rocket", "guaranteed", "don't miss".
- **Indian context:** ₹, lakh, crore, Nifty IT, SIP. Dates as `09 Oct 2026`. Times in IST.

**Vocabulary**
| Use | Avoid |
|---|---|
| Cockpit · Screener · Company · Academy | Dashboard, Home, Learn |
| Beemer Picks · belts: Momentum, Compounders, Movers | Top picks, hot stocks, predictions |
| Buffett Score (0–100) · test · pass / watch / fail | Rating, grade, stars |
| Value estimate · margin of safety | Fair value, target price |
| Loss-making · young listing | Risky bet, hype stock |
| Select a card / row | Click here, tap now |

**Before / after**
- "Which tech companies would Buffett look at twice?" → "Quality first. Then price."
- "Does holding longer help — even in tech?" → "Time in the market"
- Bulb-icon callout, "In plain English: buy the Nifty IT index in a random month and hold 1 year — you lost money 36% of the time…" →
  "Held 1 year, Nifty IT lost money **36%** of the time. Held 10 years: **0%**."

## 8. Iconography
No emoji. Identity comes from type, the tri-stripe, mono kickers and colour-as-meaning.
- Page navigation: text labels only.
- Status: `PASS` / `WATCH` / `FAIL` tags (see Components).
- Sub-sectors: plain names (IT services, ER&D, SaaS & software, AI & data, Internet, Fintech, Electronics).
- Theme switch: text pills `Studio` / `Night`.
- Favicon and page icon: the tri-bar mark (`app/static/beemer-logo.svg`).

## 9. Product narrative (pages)
1. **Cockpit** — India tech, measured. Beemer Picks belts, index growth, sub-sectors, new-age listings, drawdowns, SIP simulator.
2. **Screener** — Quality first. Then price. Ranked by Buffett Score, with compact Picks belts and filters.
3. **Company** — verdict, gauge, Buffett checklist, returns, fundamentals, key metrics.
4. **Academy** — Engineered understanding. Ten lessons, how Picks work, glossary, pre-buy checklist.

*Beemer is an educational tool, not investment advice.*
