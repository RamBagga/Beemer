# BEEMER — Precision research for India's tech stocks

Beginner-friendly, Buffett-style research dashboard for **Indian-listed tech companies**: IT services, ER&D,
SaaS/software products, AI & data, internet platforms, fintech and electronics/semicon design.
Every metric comes with a one-line plain-English explanation and "why Buffett cares".

> Educational tool, not investment advice. See **Data licensing** before selling this publicly.

## Quick start (localhost)

```bash
cd beemer
./start.sh            # first run: creates .venv, installs deps, downloads data (~8–10 min), starts the app
# → http://localhost:8501
./start.sh --cron     # optional: also install the weekday refresh schedule
./start.sh --fg       # run in the foreground
./start.sh --status   # running? which port?
./start.sh --stop     # stop
```
Requirements: Python 3.11–3.13 recommended (macOS: `brew install python@3.12`; `start.sh` picks it automatically), macOS or Linux, internet access. No API keys.
If port 8501 is taken, `start.sh` uses the next free port. Architecture overview: [ARCHITECTURE.md](ARCHITECTURE.md).

## Pages
| Page | What it shows |
|---|---|
| **Cockpit** | Nifty IT vs Nifty 50 vs Sensex, sub-sector instrument panel, new-age listing tracker, rolling returns, crash & recovery history, SIP vs lump-sum simulator (indices or any stock) |
| **Screener** | All companies ranked by Buffett Score with six sub-scores; filters for sub-sector, P/E, debt, ROE, profitability, listing age, margin of safety; quality-vs-price map |
| **Company** | Verdict, score gauge, Buffett checklist with explanations, 1/3/5/10/20-yr returns, drawdowns, sales/profit, ROE/ROCE/margins, P/E vs own history, FCF vs profit, rough intrinsic value with assumptions, data notes |
| **Academy** | 10 short lessons (incl. tech-specific ones), glossary, pre-buy checklist |

## Universe
`data/universe_tech.csv` — 64 curated companies tagged by sub-sector and theme. Edit the CSV to add/remove names
(NSE symbol, name, subsector, theme, note) and re-run `update_data.py`. Other universes: `--universe nifty50|nifty100|nifty500`.
Notes: LTIMindtree trades as **LTM** (formerly LTIM); Unicommerce is **UNIECOM**; MosChip has NSE data only from 2025 (BSE-listed before).

## Buffett Score (0–100)
Six transparent tests, rescaled when a test lacks data:
⚙️ consistent ROE > 15% (20) · 🛡️ low debt (15) · 📈 steady profit growth (20) · 🏰 moat proxy: high & stable operating margins (15) ·
💵 free cash flow (15) · 🏷️ valuation: P/E vs own 10-yr median + margin of safety vs a simple intrinsic value (15).
Intrinsic value = 10 yrs of EPS growing at the median of (10y sales CAGR, 10y & 5y profit CAGR, capped 18%), dividends at the usual payout,
terminal P/E 15 (or the historical median if lower), discounted at 12%. Deliberately simple — a sanity check, not a target price.

## Data pipeline
- `update_data.py` — idempotent & incremental. Prices: last 10 days re-fetched and upserted; if a split/dividend adjustment is detected
  on overlap, that symbol's full history is reloaded. Fundamentals: refreshed when older than 7 days, 1 request / ~4–5 s, raw HTML cached in `data/screener_cache/`.
- `analytics.py` — price cleaning (drops one-day Yahoo glitches; rescales unadjusted splits/demergers: single-day moves > ±30% while the market moved < 8%), metrics and score.
- Storage: SQLite `data/market.db` (prices, fundamentals, universe, run log) + `data/metrics.parquet` (one row per company).

### Schedule (weekdays, IST)
| Time | Job | Command |
|---|---|---|
| 15:45 | Close snapshot: prices + metrics | `scripts/run_update.sh snapshot` (`update_data.py --prices-only`) |
| 18:30 | End-of-day: prices + fundamentals if stale + metrics | `scripts/run_update.sh eod` |

`scripts/install_cron.sh` writes both cron lines (auto-converts to a UTC machine clock: 10:15 / 13:00 UTC) and starts `cron` if needed (Linux; on macOS cron is built in, jobs run only while the Mac is awake).
Logs: `logs/update_snapshot.log`, `logs/update_eod.log`. The app re-reads data every 10 minutes.

## Free / public Indian market data sources — what we found
| Source | What | Pros | Cons |
|---|---|---|---|
| **yfinance** (Yahoo Finance) — github.com/ranaroussi/yfinance | Daily OHLCV for `.NS`/`.BO`, indices (`^NSEI` from 2007, `^BSESN` from 1997, `^CNXIT` from 2007) | No key, long history (some NSE stocks from 1996), split/dividend-adjusted series, easy | Unofficial; pre-2006 NSE data has glitches and some unadjusted demergers (we clean them); Yahoo terms = personal use |
| **NSE archives / bhavcopy** — nseindia.com/all-reports, archives.nseindia.com | Official daily EOD files, index constituent CSVs | Official, complete EOD per day | One file per day; needs browser-like headers/cookies for some endpoints; NSE terms restrict commercial use |
| **jugaad-data** — github.com/jugaad-py/jugaad-data | Python lib for NSE stock/index history, bhavcopies, live quotes, niftyindices.com index data | Free, caching built-in, popular on r/IndiaInvestments & r/algotrading | Scrapes NSE website; breaks when NSE changes; rate limits |
| **nsepython / nselib / nsefeed / pybhav** | Similar NSE wrappers (nsefeed = yfinance-style; pybhav = bulk bhavcopy with caching) | Free, active | Unofficial; NSE deprecated some historical index endpoints |
| **NSE MCP (mcp.nseindia.in)** | ~5 yrs EOD bhavcopy + delayed live snapshot via MCP, no auth | Official, no key | Only ~5 years; NSE disclaimer: informational, non-commercial use |
| **BSE public APIs** — api.bseindia.com (undocumented) | Quotes, corporate actions, announcements, results filings | Free, broad coverage incl. BSE-only names | Undocumented, can change; terms apply |
| **XBRL filings (NSE/BSE)** — e.g. `india-xbrl-filings`, `nse-xbrl` on PyPI | Company-filed financial results in machine-readable XBRL | Primary source — the cleanest legal base for fundamentals | Must parse/normalise yourself; Integrated Filing format only since 2024/25 |
| **screener.in** (public company pages) | 10–12 yrs P&L, balance sheet, cash flow, ratios, shareholding | Best free fundamentals for Indian cos; robots.txt allows company pages | **No API**; ToS = personal, non-commercial use; we fetch politely (1 req/4–5 s, cached, weekly) |
| **Tickertape / Trendlyne** | Research UIs, screeners, scores | Great UX reference | No public API (Tickertape web endpoints are undocumented; Trendlyne sells a paid MCP connector) — not used |

**What Beemer uses today:** yfinance (prices, indices), NSE archives (index lists), screener.in public pages (fundamentals).

## Data licensing — read before selling
Yahoo, NSE and screener.in all limit their free data to personal / non-commercial use. For a paid public product you will need
licensed data: e.g. an NSE/BSE market-data licence or a licensed vendor (CMOTS, Accord Fintech, ACE Equity/Capitaline, Drishti, DalalOS, etc.)
for prices, and XBRL filings parsed in-house or a licensed fundamentals feed. The pipeline is modular (`update_data.py` fetchers) so sources can be swapped.
Also review SEBI's Research Analyst / Investment Adviser rules — scores and "margin of safety" displays should stay clearly educational.

## Project layout
```
start.sh                 one-command setup + run
update_data.py           data pipeline (cron entry point)
analytics.py             metrics, price cleaning, Buffett Score
app/main.py              Streamlit entry (navigation)
app/beemer.py            design system: CSS, Plotly template, components, copy
app/views/*.py           Cockpit, Screener, Company, Academy
app/.streamlit/config.toml  dark theme
design/                  design board (md/html/png), logo & wordmark SVGs
scripts/                 cron wrapper + installer, check_pages.py (headless render check + screenshots), shot.py
requirements-dev.txt     playwright + pillow for the screenshot scripts
data/universe_tech.csv   curated universe
```
