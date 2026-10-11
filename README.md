<p align="center">
  <img src="design/beemer-wordmark.svg" alt="Beemer" width="320">
</p>

<h3 align="center">Precision research for India's tech stocks</h3>

<p align="center">
Buffett-style insights on Indian AI, SaaS and tech companies, explained simply.<br>
Up to 30 years of NSE/BSE price history · 12 years of fundamentals · a transparent 0–100 Buffett Score · refreshed every trading day.
</p>

<p align="center">
  <img src="screenshots/01-cockpit.png" alt="Beemer Cockpit" width="900">
</p>

> **Educational tool, not investment advice.** Read [Data licensing](#data-licensing--read-before-selling) before selling this publicly.

The app on Streamlit Community Cloud is the **legacy** UI (`app/main.py`). A Spring Boot API and React frontend live in `backend/` and `frontend/` and do not replace that deployment. Run the new stack with `./start-new.sh` (API on port 8080, app on port 5173; `./start-new.sh --status` / `--stop`, logs in `logs/api.log` and `logs/web.log`). It keeps running after the terminal closes. See [ARCHITECTURE.md](ARCHITECTURE.md) and [DEPLOYMENT.md](DEPLOYMENT.md).

## Why Beemer
Most stock screeners throw 50 ratios at you and leave you to figure out what they mean. Beemer covers **64 Indian-listed tech companies**, from IT services, ER&D, SaaS and AI to internet platforms, fintech and chip design. It scores each one against the questions Warren Buffett asks, and explains every number in one plain-English line.

## Getting started

### 1. Prerequisites
- macOS or Linux
- Python 3.11+ (macOS: `brew install python@3.12`; `start.sh` picks the best version automatically)
- Git, and an internet connection. **No API keys needed.**

### 2. Clone and run
```bash
git clone git@github.com:RamBagga/Beemer.git
cd Beemer
./start.sh
```
Then open **http://localhost:8501**.

The first run creates a virtual environment, installs dependencies and downloads the latest data snapshot that GitHub Actions publishes every weekday, which takes about a minute. If no snapshot is available, it builds the data from scratch instead (8 to 10 minutes). After that, the app starts in seconds.

### Deploy it (free)
Beemer is set up to deploy to **Streamlit Community Cloud**: sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub, choose repo `RamBagga/Beemer`, branch `main`, main file `app/main.py`, Python 3.12, then click Deploy. Render (`render.yaml`) and Docker (`Dockerfile`) configs are included too. See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the comparison of free hosts, how data reaches the cloud, and the licensing caveats.

### 3. Everyday commands
| Command | What it does |
|---|---|
| `./start.sh` | Start the app in the background |
| `./start.sh --fg` | Run in the foreground (see logs live) |
| `./start.sh --status` | Is it running, and on which port? |
| `./start.sh --stop` | Stop the app |
| `./start.sh --cron` | Install the weekday auto-refresh (3:45 PM and 6:30 PM IST) |
| `.venv/bin/python update_data.py` | Refresh data manually right now |
| `make help` | Every other task: `make test` (render all pages), `make publish` (upload data for the cloud), `make docker-build` … |

### 4. Troubleshooting
- **Port 8501 is busy:** `start.sh` automatically uses the next free port. Run `./start.sh --status` to see which one.
- **The app won't start:** check `logs/streamlit.log`.
- **Data looks old:** run `.venv/bin/python update_data.py`, or install the schedule with `./start.sh --cron`. Cron jobs only run while the Mac is awake.
- **Start from scratch:** delete `data/market.db`, `data/metrics.parquet` and `.venv`, then run `./start.sh`.

### 5. Learn the codebase
Read [ARCHITECTURE.md](ARCHITECTURE.md) for the data flow diagram and module map, and [design/beemer-design-board.md](design/beemer-design-board.md) for the design system.

## Screenshots
| Screener | Company | Academy |
|---|---|---|
| <img src="screenshots/02-screener.png" width="300"> | <img src="screenshots/03-company-infosys.png" width="300"> | <img src="screenshots/05-academy.png" width="300"> |

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

**All tech** (`universe_all`, ~200 names): the core 64 plus every NSE-listed name tagged Information Technology or
Telecommunication by NSE, every Nifty India Digital internet and fintech name, NSE legacy industries such as
Computers - Software / Hardware, Electronics and Telecom equipment, a short hand-checked list of EMS, fintech and
platform names filed under other industries, and small untagged names whose company name is clearly tech.
Built by `sources/universe.py`; `class_source` records why each name is in. The Screener has a Core 64 / All tech
toggle; the Cockpit and the Picks belts stay on the core 64.

## Buffett Score (0–100)
Six transparent tests, rescaled when a test lacks data:
consistent ROE > 15% (20) · low debt (15) · steady profit growth (20) · moat proxy: high & stable operating margins (15) ·
free cash flow (15) · valuation: P/E vs own 10-yr median + margin of safety vs a simple intrinsic value (15).
Intrinsic value = 10 yrs of EPS growing at the median of (10y sales CAGR, 10y & 5y profit CAGR, capped 18%), dividends at the usual payout,
terminal P/E 15 (or the historical median if lower), discounted at 12%. Deliberately simple — a sanity check, not a target price.

## Data pipeline
- `update_data.py` — idempotent & incremental. Prices: last 10 days re-fetched and upserted; if a split/dividend adjustment is detected
  on overlap, that symbol's full history is reloaded. Fundamentals: refreshed when older than 7 days, 1 request / ~4–5 s, raw HTML cached in `data/screener_cache/`.
- `analytics.py` — price cleaning (drops one-day Yahoo glitches; rescales unadjusted splits/demergers: single-day moves > ±30% while the market moved < 8%), metrics and score.
- `expand_data.py` — NSE datasets for every tracked name (delivery %, index valuations, corporate actions, board meetings,
  shareholding, insider trades, bulk/block deals, official quarterly results), a split/bonus audit of Yahoo prices, and
  enrichment of `company_metrics`. `update_data.py` calls it after the metrics; `--core-only` or `--skip-feeds` turn it off.
  Run alone: `python expand_data.py --steps delivery,feeds`. Tests: `python -m pytest tests`.
- Storage: SQLite `data/market.db` (prices, fundamentals, universe, run log, NSE datasets) + `data/metrics.parquet` (one row per core company, read by Streamlit).

### Schedule (weekdays, IST)
| Time | Job | Command |
|---|---|---|
| 15:45 | Close snapshot: prices + metrics | `scripts/run_update.sh snapshot` (`update_data.py --prices-only`) |
| 18:30 | End-of-day: prices + fundamentals if stale + metrics | `scripts/run_update.sh eod` |

`scripts/install_cron.sh` writes both cron lines (auto-converts to a UTC machine clock: 10:15 / 13:00 UTC) and starts `cron` if needed (Linux; on macOS cron is built in, jobs run only while the Mac is awake).
Logs: `logs/update_snapshot.log`, `logs/update_eod.log`. The app re-reads data every 10 minutes.

## Data sources

Every source below is free and public. Beemer reads them the way a browser would: normal headers, no logins,
no captchas, no paywalls, nothing that gets around a block. Each host has a minimum gap between requests,
immutable files (archives, XBRL filings) are cached in `data/cache/`, and a host that refuses repeatedly is
skipped for the rest of the run while stored data is kept (`sources/http.py`).

| Source | Data | History | Update cadence | Terms / licence | Reliability |
|---|---|---|---|---|---|
| Yahoo Finance via `yfinance` | Daily OHLCV, split- and dividend-adjusted close, for every tracked name (`.NS`) and 10 indices (Nifty 50, Nifty IT, Sensex, Nifty 100, Nifty 500, Bank, Midcap 50, Smallcap 250, Pharma, India VIX) | From 1996 for the oldest names; indices from 1997–2011 | Every run (incremental, last 10 days re-checked) | Yahoo terms: personal use only | Medium. Pre-2006 glitches and some unadjusted demergers, repaired by `analytics.clean_prices` and checked against NSE split records (`price_audit`) |
| screener.in public company pages | Annual and quarterly P&L, balance sheet, cash flow, ratios, shareholding | 10–12 years annual, ~12 quarters | Core 64 weekly; extended names monthly, 40 a run | Personal, non-commercial use; robots.txt allows company pages | High for listed names; no API, layout can change |
| NSE `EQUITY_L.csv` + index constituent CSVs (Total Market, Microcap 250, IT, India Digital, New Age Consumption, 50, 500, Midcap 150, Smallcap 250) | Every listed equity (symbol, ISIN, listing date, face value), NSE industry tags and index membership | Current snapshot | Every run; committed copy in `data/universe_all.csv` | NSE website terms: information only, no commercial redistribution without a licence | High |
| NSE board-meetings feed | Legacy industry tags for small names; board meetings and results dates | ~2 years per company | Every 3 days per company | As above | High |
| NSE `sec_bhavdata_full` daily archive | Official EOD OHLC, VWAP, trades, delivery quantity and delivery % | 2020 onward (earlier files are not on the archive host) | Daily | As above | High (one 2022 file is corrupt on NSE's side and is skipped) |
| NSE `ind_close_all` daily archive | Every NSE index: OHLC, turnover, P/E, P/B, dividend yield | 2015 onward | Daily | As above | High |
| NSE corporate actions feed | Dividends, splits, bonuses, rights, buybacks, with ex and record dates | From the 1990s for older names | Weekly per company | As above | High; free-text subjects parsed into kind, amount and ratio |
| NSE shareholding feed + SHP XBRL | Promoter / public % every quarter; XBRL breakdown into foreign, domestic institutions, mutual funds, insurance, retail, HNI, pledge flag | ~5 years summary; XBRL for the last 12 quarters (core) or 4 (others) | Fortnightly per company | As above | High |
| NSE insider trading (SEBI PIT) feed | Promoter, director and KMP trades with mode, value and holding after | 3 years | Weekly per company | As above | High |
| NSE bulk and block deals feed | Client, side, quantity, price | 2 years per company; last 5 days market-wide | Weekly per company, daily market-wide | As above; NSE caps a call at 70 rows, so history is pulled per company | High |
| NSE financial results (Ind-AS XBRL to Dec 2024, integrated filings from 2025) | Official quarterly revenue, other income, costs, PBT, tax, net profit, profit to owners, EPS, consolidated and standalone | Ind-AS filings from ~2017; all filings for the core 64, the last 8 for others | Weekly per company | As above | High; older pre-Ind-AS formats are listed but not parsed |

Not used, and why:
- **BSE APIs** (`api.bseindia.com`): refused with HTTP 403 from both a home and a cloud network, so not used. BSE's bhavcopy file downloads work, but without a BSE industry list there is no clean way to find BSE-only tech names.
- **NSE quote and historical-price APIs**: refused (403). Delivery and prices come from the archive files instead.
- **AMFI / AMC monthly portfolios**: each fund house publishes its own spreadsheet with no shared format. The mutual-fund share of each company comes from the shareholding XBRL instead.
- **jugaad-data / nselib**: wrap the same NSE endpoints (including the refused historical one), so they would add a dependency without adding data.

Row counts and the last run of each source: `GET /api/data/inventory`, or the `source_runs` table.

### Earlier research
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

**What Beemer uses today:** see the Data sources table above.

## Data licensing — read before selling
Yahoo, NSE (website, archives and corporate-filing feeds) and screener.in all limit their free data to personal / non-commercial use. For a paid public product you will need
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
.streamlit/config.toml   dark theme (repo root, as Streamlit Cloud requires)
bootstrap.py             downloads the published data snapshot on fresh hosts
Dockerfile · render.yaml · Procfile · Makefile · .env.example   deployment configs
.github/workflows/       update-data.yml (weekday data refresh → data-latest release) · ci.yml
design/                  design board (md/html/png), logo & wordmark SVGs
scripts/                 cron wrapper + installer, publish_data.sh, smoke_test.py, healthcheck.sh, check_pages.py (headless render check + screenshots), shot.py
requirements-dev.txt     playwright + pillow for the screenshot scripts
data/universe_tech.csv   curated universe
```

## Roadmap
- Licensed data feeds for a commercial launch
- Public deployment (configs ready, see DEPLOYMENT.md)
- Bigger universe (Nifty 500), watchlists and alerts

## License
See [LICENSE](LICENSE).
