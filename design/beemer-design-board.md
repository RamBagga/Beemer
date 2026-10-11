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

## 3. Colour palettes — Studio (light, default) and Night (dark)

Deep ink, one electric blue, cool gradients, and colour that means something at a glance. Studio opens by default; Night is one tap
away in the menu drawer and remembered per browser. Tokens live in `app/beemer.py` (`PALETTES`, `SUBSECTOR_COLORS`) and
`.streamlit/config.toml`; never hard-code a hex in a view.

### 3a. Core tokens
| Role | Token | Studio | Night |
|---|---|---|---|
| App background | `bg` | `#F5F7FB` | `#06080E` |
| Cards / surfaces | `surface` | `#FFFFFF` | `#0C111B` |
| Raised / inputs | `raised` | `#F0F3F8` | `#121926` |
| Drawer | `sidebar` | `#FBFCFE` | `#0A0E17` |
| Hairlines | `line` | `#E2E7EF` | `#1C2433` |
| Gridlines (dotted) | `grid` | `#ECEFF5` | `#151C29` |
| Headings, prices | `text` (deep ink) | `#0A1022` | `#EAEFF7` |
| Body copy | `body` | `#283145` | `#C3CBD9` |
| Secondary text (AA on cards) | `muted` | `#556073` | `#97A1B4` |
| Decorative only, never body text | `dim` | `#828CA0` | `#6E788E` |
| Primary accent, main series | `blue` (electric) | `#2D6BFF` | `#5B8CFF` |
| Accent text, links | `ice` | `#2563C9` | `#7DB8FF` |
| Second series | `violet` | `#7466E8` | `#A08FFF` |
| Third series, Compounders belt | `teal` | `#14B8A6` | `#2DD4BF` |
| Neutral bars (sales, P/E history) | `bar` | `#D3DDF1` | `#22355C` |

### 3b. Semantic colour (gain, loss, watch)
| Meaning | Fill / line | Text on cards (WCAG AA) |
|---|---|---|
| Gain, pass | Emerald `#10B981` / `#34D399` | `#047857` / `#6EE7B7` |
| Loss, fail | Rose `#F43F5E` / `#FB7185` | `#BE123C` / `#FDA4AF` |
| Watch, mixed | Amber `#F59E0B` / `#FBBF24` | `ink(amber)` |

- **Change chips:** `▲ 3.62%` / `▼ 2.95%` in a 6px-radius chip, 13% tint of the fill, AA text tone, tabular numerals.
- **`ink(colour)`:** badge and pill text is the accent mixed toward the text colour (58% in Studio, 70% in Night), so it clears 4.5:1.
- **Score scale (Buffett Score, Signal, test cells):** `0–39` Rose · `40–59` Amber · `60–74` Teal · `75–100` Emerald.
  Badges use 12% tint + 55% border + `ink()` text. Screener test cells are heat cells: 16% tint, `ink()` text.
- **Heat for signed numbers** (returns, margin of safety): emerald or rose, tint 6–28% scaled by size, bold AA text.

### 3c. Sub-sector identity (categorical; never gain or loss)
| Sub-sector | Hex |
|---|---|
| IT services | `#3B82F6` |
| SaaS & software products | `#8B5CF6` |
| AI & data | `#06B6D4` |
| Engineering & design R&D | `#6366F1` |
| Electronics & semicon design | `#0EA5A4` |
| Fintech | `#D946EF` |
| Internet & consumer tech | `#F97316` |

Same hue everywhere: sub-sector bars, coloured names in tables, the dot on belt cards and in the Company kicker.

### 3d. Charts
- No default Plotly colours: templates `beemer_light` / `beemer_dark`, colourway blue → violet → teal → amber → rose → ice.
- Lines 1.1–2px; the main series is blue and heaviest, benchmarks are `dim` dotted.
- Area fills: vertical gradient from 0% to 16–28% of the line colour (`B.area`); on log axes a flat 7% wash (`B.soft`).
- Gridlines: horizontal only, dotted, `grid`. No zero lines, no tick marks, a single hairline x-axis.
- Bars: 4px corner radius, 30–40% gap, no outlines.
- Hover: unified x, a dotted spike line, surface-coloured label with a hairline border, values formatted (₹, %, cr).

### 3e. Surfaces and hardware
- **Elevation (Studio):** `0 1px 2px rgba(10,16,34,.04), 0 12px 28px -16px rgba(10,16,34,.20)`. Night uses borders, not shadows.
- **Hero:** `#FFFFFF → #F4F7FC → #E9EEF8` (Studio), `#0E1424 → #06080E` (Night), tri-stripe along the top edge.
- **Picks belts:** brushed-aluminium (Studio) or graphite (Night) conveyor. Belt accents: Momentum blue, Compounders teal,
  Movers violet. Cards outside the spotlight stay at 90%+ opacity; the spotlight adds glow, not legibility.
- **Brand tri-stripe is theme-independent:** Ice `#6CC4FF` · Cobalt `#2A4BD7` · Signal Red `#F0303F`.

Accent discipline: colour carries meaning (gain, loss, score, sub-sector). Everything else is ink, surface and hairline.

### 3f. Menu drawer
- Collapsed by default. A 38px burger (top left, on the page body so it never re-mounts) morphs to an X in 300ms.
- The 300px drawer overlays content; it animates `transform` only, `cubic-bezier(0.22,1,0.36,1)`, 300ms, GPU-composited.
- A fading backdrop (ink at 30% Studio, 55% Night, 2px blur). Closes on backdrop click, Escape, or after picking a page.
- `prefers-reduced-motion`: no transitions.

## 4. Typography
- **Display / headings:** Inter Tight 600 — tight, engineered, high-precision. H1 40/44 (−0.02em), H2 26/32, H3 18/24.
- **Kickers / labels:** Inter Tight 600, ALL CAPS, 11–12px, +0.14em tracking, Titanium colour (instrument-panel labels).
- **Body:** Inter 400/500, 15/24.
- **Data:** JetBrains Mono 500 only for kickers and timestamps. Tickers on cards are Inter Tight 700; numbers use tabular figures.
- **Card hierarchy:** ticker (16px, 700) > price (23px, 650) > change chip (13px, 600) > stat line (12px) > reason (12.5px, 1.45 line-height).
- **KPI tiles:** label Inter Tight 600 12px caps; numeral 29px 650 tabular; note 14px, 1.5 line-height.

## 5. Chart styling (Plotly templates `beemer_light` / `beemer_dark`)
See 3d. Legends below the plot, titles left-aligned in Inter Tight 14px, log scale for long price histories with 1-2-5 ₹ ticks.
Captions only when they add a fact the chart cannot show (period, exclusions, data limits).

## 6. Components
- **Cards:** `surface`, 1px `line`, 12px radius, 16–20px padding; Studio adds the soft elevation shadow.
- **Top bar:** translucent `bg` at 82% with 14px backdrop blur and a hairline; burger left, wordmark, menu right.
- **Hero:** see 3e; kicker in caps mono with the sub-sector dot on Company.
- **KPI tiles (instrument cluster):** caps label → big tabular numeral (coloured only when it carries meaning) → one-line explanation.
- **Score gauge:** 270° thin-arc gauge (iDrive-style) with numeric read-out in the centre; also compact pill badges (`82 · STRONG`) with 1px coloured outline + 12% tint.
- **Checklist rows:** status tag (`PASS` emerald · `WATCH` amber · `FAIL` rose; 10% tint, 50% outline, `ink()` text) · test name · 4px progress rail · finding · one-line reason.
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
