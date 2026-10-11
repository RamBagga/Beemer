"""NSE corporate-filing feeds (public JSON behind nseindia.com pages, plus XBRL files on the archive host).

Per company: corporate actions, board meetings, shareholding pattern (summary + XBRL breakdown),
insider (PIT) trades, quarterly financial results (XBRL / integrated-filing tables).
Market-wide: bulk and block deals.

Requests carry the headers a browser sends on the matching nseindia.com page. When NSE refuses a network
(common for cloud IPs), :class:`sources.http.Refused` stops the feed for the run and stored data is kept.
"""
import datetime as dt, logging, re

from bs4 import BeautifulSoup

from . import store
from .http import Refused, session

log = logging.getLogger("sources.nse")
API = "https://www.nseindia.com/api/"
FMT = "%d-%m-%Y"


def _stale(con, sym, feed, max_age_days):
    r = con.execute("SELECT fetched_at FROM feed_meta WHERE symbol=? AND feed=?", (sym, feed)).fetchone()
    return r is None or (dt.datetime.now() - dt.datetime.fromisoformat(r[0])).days >= max_age_days


def _mark(con, sym, feed, n):
    con.execute("INSERT OR REPLACE INTO feed_meta VALUES (?,?,?,?)", (sym, feed, dt.datetime.now().isoformat(), n))


# ---------------- corporate actions ----------------
_RS = re.compile(r"(?:rs\.?|re\.?|inr|₹)\s*([0-9]+(?:\.[0-9]+)?)", re.I)
_PCT = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*%")
_RATIO = re.compile(r"(\d+)\s*:\s*(\d+)")
_SPLIT = re.compile(r"(?:from|rs\.?)\s*(?:rs\.?\s*)?([0-9.]+).*?to\s*(?:rs\.?|re\.?)\s*([0-9.]+)", re.I)


def classify_action(subject, face_value=None):
    """'Interim Dividend - Rs 15 Per Share' -> ('dividend', 15.0, None). Amount = rupees per share."""
    s = (subject or "").strip()
    low = s.lower()
    if "split" in low or "sub-division" in low or "subdivision" in low:
        m = _SPLIT.search(s)
        return "split", None, (f"{m.group(1)}:{m.group(2)}" if m else None)
    if "bonus" in low and "div" not in low:
        m = _RATIO.search(s)
        return "bonus", None, (f"{m.group(1)}:{m.group(2)}" if m else None)
    if "div" in low:
        amts = [float(x) for x in _RS.findall(s)]
        if not amts and face_value:
            amts = [float(p) / 100 * face_value for p in _PCT.findall(s)]
        kind = "dividend"
        if "bonus" in low:
            kind = "dividend+bonus"
        return kind, (round(sum(amts), 4) if amts else None), None
    if "rights" in low:
        m = _RATIO.search(s)
        return "rights", None, (f"{m.group(1)}:{m.group(2)}" if m else None)
    if "buy back" in low or "buyback" in low:
        return "buyback", None, None
    if "demerger" in low or "scheme of arrangement" in low:
        return "demerger", None, None
    if "agm" in low or "annual general meeting" in low:
        return "agm", None, None
    return "other", None, None


def corp_actions(con, sym):
    url = f"{API}corporates-corporateActions?index=equities&symbol={sym}&from_date=01-01-1990&to_date={dt.date.today():{FMT}}"
    rows = session().json(url) or []
    out = []
    for r in rows:
        fv = store.num(r.get("faceVal"))
        kind, amt, ratio = classify_action(r.get("subject"), fv)
        ex = store.iso(r.get("exDate"))
        if not ex:
            continue
        out.append((sym, ex, store.iso(r.get("recDate")), " ".join((r.get("subject") or "").split()), kind, amt,
                    ratio, fv, r.get("series")))
    con.execute("DELETE FROM corp_actions WHERE symbol=?", (sym,))
    con.executemany("INSERT OR REPLACE INTO corp_actions VALUES (?,?,?,?,?,?,?,?,?)", out)
    return len(out)


# ---------------- board meetings ----------------
def board_meetings(con, sym):
    url = f"{API}corporate-board-meetings?index=equities&symbol={sym}"
    rows = session().json(url) or []
    out = [(sym, store.iso(r.get("bm_date")), (r.get("bm_purpose") or "").strip(), " ".join((r.get("bm_desc") or "").split()),
            store.iso(r.get("bm_timestamp"))) for r in rows if store.iso(r.get("bm_date"))]
    con.executemany("INSERT OR REPLACE INTO board_meetings VALUES (?,?,?,?,?)", out)
    return len(out)


# ---------------- shareholding ----------------
SHP_CTX = {  # column -> XBRL context holding "% of total shares"
    "promoter": "ShareholdingOfPromoterAndPromoterGroup_ContextI",
    "public": "PublicShareholding_ContextI",
    "fii": "InstitutionsForeign_ContextI",
    "dii": "InstitutionsDomestic_ContextI",
    "mf": "MutualFundsOrUTI_ContextI",
    "insurance": "InsuranceCompanies_ContextI",
    "retail": "ResidentIndividualShareholdersHoldingNominalShareCapitalUpToRsTwoLakh_ContextI",
    "hni": "ResidentIndividualShareholdersHoldingNominalShareCapitalInExcessOfRsTwoLakh_ContextI",
    "employee_trusts": "EmployeeBenefitsTrusts_ContextI",
}


def parse_shp_xbrl(xml):
    out = {}
    for col, ctx in SHP_CTX.items():
        m = re.search(r'<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares\s+contextRef="%s"[^>]*>([^<]*)<' % ctx, xml)
        if m:
            v = store.num(m.group(1))
            out[col] = None if v is None else round(v * 100, 4)
    m = re.search(r'<in-bse-shp:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged\w*\s+contextRef="[^"]*"[^>]*>([^<]*)<', xml)
    out["pledge_flag"] = m.group(1).strip() if m else None
    return out


def shareholding(con, sym, xbrl_quarters=4):
    sess = session()
    rows = sess.json(f"{API}corporate-share-holdings-master?index=equities&symbol={sym}") or []
    have = {r[0]: r[1] for r in con.execute("SELECT period, fii FROM shareholding WHERE symbol=?", (sym,))}
    n = 0
    seen = set()
    for i, r in enumerate(rows):
        period = store.iso(r.get("date"))
        if not period or period in seen:
            continue          # keep the latest revision per quarter (feed is newest first)
        seen.add(period)
        rec = {"promoter": store.num(r.get("pr_and_prgrp")), "public": store.num(r.get("public_val")),
               "employee_trusts": store.num(r.get("employeeTrusts"))}
        url = r.get("xbrl") if r.get("xbrl") not in (None, "-", "") else None
        src = "nse_summary"
        if url and len(seen) <= xbrl_quarters and have.get(period) is None:
            try:
                xml = sess.get(url, timeout=60).decode("utf-8", "ignore")
                rec.update({k: v for k, v in parse_shp_xbrl(xml).items() if v is not None})
                src = "nse_xbrl"
            except (Refused, IOError) as e:
                log.info("SHP XBRL %s %s: %s", sym, period, e)
        elif have.get(period) is not None:
            continue          # already have the XBRL breakdown for this quarter
        other = None
        if rec.get("public") is not None:
            parts = [rec.get(k) for k in ("fii", "dii", "retail", "hni")]
            if all(p is not None for p in parts):
                other = round(rec["public"] - sum(parts), 4)
        con.execute("""INSERT OR REPLACE INTO shareholding(symbol, period, promoter, public, fii, dii, mf, insurance,
                       retail, hni, employee_trusts, other, pledge_flag, source, filed_at, xbrl)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sym, period, rec.get("promoter"), rec.get("public"), rec.get("fii"), rec.get("dii"), rec.get("mf"),
                     rec.get("insurance"), rec.get("retail"), rec.get("hni"), rec.get("employee_trusts"), other,
                     rec.get("pledge_flag"), src, store.iso(r.get("submissionDate")) or store.iso((r.get("broadcastDate") or "")[:11]), url))
        n += 1
    return n


# ---------------- insider trades (SEBI PIT) ----------------
def insider(con, sym, years=3):
    fr = dt.date.today() - dt.timedelta(days=365 * years)
    url = f"{API}corporates-pit?index=equities&symbol={sym}&from_date={fr:{FMT}}&to_date={dt.date.today():{FMT}}"
    js = session().json(url, timeout=60) or {}
    out = []
    for r in js.get("data", []):
        buy, sell = store.num(r.get("buyQuantity")) or 0, store.num(r.get("sellquantity")) or 0
        t = (r.get("tdpTransactionType") or "").strip()
        if t in ("", "-"):
            t = "Buy" if buy > 0 and sell == 0 else "Sell" if sell > 0 and buy == 0 else (r.get("acqMode") or "Other")
        out.append((sym, str(r.get("did") or r.get("pid")), r.get("acqName"), r.get("personCategory"), t, r.get("acqMode"),
                    r.get("secType"), store.num(r.get("secAcq")), store.num(r.get("secVal")),
                    store.num(r.get("befAcqSharesPer")), store.num(r.get("afterAcqSharesPer")),
                    store.iso(r.get("acqfromDt")), store.iso(r.get("acqtoDt")), store.iso(r.get("intimDt")),
                    store.iso(r.get("date"))))
    con.executemany("INSERT OR REPLACE INTO insider_trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
    return len(out)


# ---------------- quarterly results (official XBRL) ----------------
XML_TAGS = {
    "revenue": ["RevenueFromOperations"], "other_income": ["OtherIncome"], "total_income": ["Income"],
    "employee_cost": ["EmployeeBenefitExpense"], "finance_cost": ["FinanceCosts"],
    "depreciation": ["DepreciationDepletionAndAmortisationExpense"], "total_expenses": ["Expenses"],
    "pbt": ["ProfitBeforeTax"], "tax": ["TaxExpense"], "net_profit": ["ProfitLossForPeriod"],
    "profit_owners": ["ProfitOrLossAttributableToOwnersOfParent"],
    "eps": ["BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations"],
    "paid_up_capital": ["PaidUpValueOfEquityShareCapital"],
}
HTML_LABELS = {
    "revenue": "revenue from operations", "other_income": "other income", "total_income": "total income",
    "employee_cost": "employee benefit expense", "finance_cost": "finance costs",
    "depreciation": "depreciation, depletion and amortisation expense", "total_expenses": "total expenses",
    "pbt": "total profit before tax", "tax": "total tax expenses", "net_profit": "total profit (loss) for period",
    "profit_owners": "profit or loss, attributable to owners of parent",
    "eps": "basic earnings (loss) per share from continuing and discontinued operations",
    "paid_up_capital": "paid-up equity share capital",
}
ROUND = {"rupees": 1e-7, "thousands": 1e-4, "lakhs": 1e-2, "lakh": 1e-2, "millions": 0.1, "crores": 1.0, "crore": 1.0,
         "billions": 100.0}
NOT_MONEY = {"eps"}


def parse_results_xml(xml):
    """Ind-AS results XBRL. Values are in rupees; returns {item: value in ₹ crore (EPS in ₹)}."""
    out = {}
    for item, tags in XML_TAGS.items():
        for t in tags:
            m = re.search(r'<[\w-]+:%s\s+contextRef="OneD"[^>]*>([^<]*)<' % t, xml)
            if m and store.num(m.group(1)) is not None:
                v = store.num(m.group(1))
                out[item] = v if item in NOT_MONEY else v / 1e7
                break
    return out


def _clean_num(s):
    s = (s or "").replace(",", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    v = store.num(s.strip("()"))
    return None if v is None else (-v if neg else v)


def parse_results_html(html):
    """Integrated-filing results table (2025+). First value column = the quarter."""
    soup = BeautifulSoup(html, "lxml")
    label_val, scale = {}, None
    for tr in soup.select("tr"):
        ths = tr.select("th"); tds = tr.select("td")
        if not ths or not tds:
            continue
        lab = " ".join(ths[-1].get_text(" ", strip=True).lower().split())
        val = tds[0].get_text(" ", strip=True)
        if lab.startswith("level of rounding"):
            scale = ROUND.get(val.strip().lower())
        label_val.setdefault(lab, val)
    if scale is None:
        return {}
    out = {}
    for item, lab in HTML_LABELS.items():
        v = _clean_num(label_val.get(lab))
        if v is not None:
            out[item] = v if item in NOT_MONEY else v * scale
    for k in ("date of end of reporting period",):
        if k in label_val:
            out["_period_end"] = store.iso(label_val[k])
    return out


def results(con, sym, max_new=8):
    """List result filings (old XBRL feed to Dec-2024, integrated filings from 2025) and parse up to max_new
    filings that are not parsed yet. Prefers consolidated; standalone kept too."""
    sess = session()
    filings = []
    try:
        old = sess.json(f"{API}corporates-financial-results?index=equities&symbol={sym}&period=Quarterly") or []
        for f in old:
            url = f.get("xbrl")
            if url and url.endswith(".xml") and "INDAS" in url.upper():
                basis = "consolidated" if f.get("consolidated", "").lower().startswith("consol") else "standalone"
                filings.append((store.iso(f.get("toDate")), basis, f.get("audited"), store.iso(f.get("filingDate")), url))
    except IOError as e:
        log.info("results list %s: %s", sym, e)
    try:
        new = sess.json(f"{API}integrated-filing-results?index=equities&symbol={sym}&period_ended=all"
                        f"&type=Integrated%20Filing-%20Financials") or {}
        for f in new.get("data", []):
            url = f.get("ixbrl")
            if url and url.endswith(".html"):
                basis = "consolidated" if (f.get("consolidated") or "").lower().startswith("consol") else "standalone"
                filings.append((store.iso(f.get("qe_Date")), basis, f.get("audited"), store.iso(f.get("broadcast_Date")), url))
    except IOError as e:
        log.info("integrated filings %s: %s", sym, e)
    for pe, basis, aud, filed, url in filings:
        if pe:
            con.execute("INSERT OR IGNORE INTO results_filings VALUES (?,?,?,?,?,?,?)", (sym, pe, basis, aud, filed, url, 0))
    todo = con.execute("""SELECT period_end, basis, url FROM results_filings WHERE symbol=? AND parsed=0
                          ORDER BY period_end DESC, basis""", (sym,)).fetchall()
    n = 0
    for pe, basis, url in todo[:max_new]:
        try:
            body = sess.get(url, timeout=60).decode("utf-8", "ignore")
        except (Refused, IOError) as e:
            log.info("results file %s: %s", url, e)
            if isinstance(e, Refused):
                raise
            continue
        vals = parse_results_html(body) if url.endswith(".html") else parse_results_xml(body)
        vals.pop("_period_end", None)
        con.executemany("INSERT OR REPLACE INTO results_xbrl VALUES (?,?,?,?,?)",
                        [(sym, pe, basis, k, v) for k, v in vals.items()])
        con.execute("UPDATE results_filings SET parsed=? WHERE symbol=? AND period_end=? AND basis=?",
                    (1 if vals else -1, sym, pe, basis))
        n += len(vals)
    return n


# ---------------- bulk / block deals ----------------
# The public deals feed returns at most 70 rows per call, so market-wide pulls only work for a day or two.
# Per company, a window of up to one year is complete; that is what the history uses.
def _deal_rows(js, kind):
    return [(kind, store.iso(r.get("BD_DT_DATE")), r.get("BD_SYMBOL"), r.get("BD_SCRIP_NAME"), r.get("BD_CLIENT_NAME"),
             r.get("BD_BUY_SELL"), store.num(r.get("BD_QTY_TRD")), store.num(r.get("BD_TP_WATP")), r.get("BD_REMARKS"))
            for r in (js or {}).get("data", [])]


def deals_symbol(con, sym, years=2):
    sess = session()
    r = con.execute("SELECT fetched_at FROM feed_meta WHERE symbol=? AND feed='deals'", (sym,)).fetchone()
    start = (dt.date.fromisoformat(r[0][:10]) - dt.timedelta(days=7)) if r else dt.date.today() - dt.timedelta(days=365 * years)
    n = 0
    for kind in ("bulk_deals", "block_deals"):
        d = start
        while d <= dt.date.today():
            e = min(d + dt.timedelta(days=364), dt.date.today())
            try:
                js = sess.json(f"{API}historicalOR/bulk-block-short-deals?optionType={kind}&symbol={sym}"
                               f"&from={d:{FMT}}&to={e:{FMT}}", retries=2)
            except IOError as ex:   # NSE answers 500 for some symbols with no deals
                log.debug("deals %s %s: %s", sym, kind, ex); js = None
            rows = _deal_rows(js, "bulk" if kind == "bulk_deals" else "block")
            con.executemany("INSERT OR REPLACE INTO deals VALUES (?,?,?,?,?,?,?,?,?)", rows)
            n += len(rows)
            d = e + dt.timedelta(days=1)
    return n


def deals(con, days=5):
    """Market-wide bulk and block deals for the last few days (every symbol, capped at 70 a day by NSE)."""
    sess = session()
    total = 0
    for i in range(days):
        d = dt.date.today() - dt.timedelta(days=i)
        if d.weekday() >= 5:
            continue
        for kind in ("bulk_deals", "block_deals"):
            js = sess.json(f"{API}historicalOR/bulk-block-short-deals?optionType={kind}&from={d:{FMT}}&to={d:{FMT}}")
            rows = _deal_rows(js, "bulk" if kind == "bulk_deals" else "block")
            con.executemany("INSERT OR REPLACE INTO deals VALUES (?,?,?,?,?,?,?,?,?)", rows)
            total += len(rows)
    con.commit()
    store.log_run(con, "deals", "ok", total, f"market-wide, last {days} days")
    return total


# ---------------- per-company driver ----------------
FEEDS = {  # feed -> (function, refresh every N days)
    "corp_actions": (corp_actions, 7),
    "board_meetings": (board_meetings, 3),
    "shareholding": (shareholding, 14),
    "insider": (insider, 7),
    "results": (results, 7),
    "deals": (deals_symbol, 7),
}


def update_companies(con, symbols, feeds=None, core=(), force=False, budget=None):
    """Run per-company feeds. Core names get deeper history (all result filings, 12 quarters of SHP XBRL)."""
    store.ensure(con)
    feeds = feeds or list(FEEDS)
    stats = {f: [0, 0] for f in feeds}   # rows, companies
    calls = 0
    for f in feeds:
        fn, age = FEEDS[f]
        for sym in symbols:
            if not force and not _stale(con, sym, f, age):
                continue
            if budget and calls >= budget:
                break
            kw = {}
            if f == "shareholding":
                kw["xbrl_quarters"] = 12 if sym in core else 4
            if f == "results":
                kw["max_new"] = 60 if sym in core else 8
            try:
                n = fn(con, sym, **kw)
                _mark(con, sym, f, n); con.commit()
                stats[f][0] += n; stats[f][1] += 1; calls += 1
            except Refused as e:
                log.warning("%s: NSE refused (%s); keeping stored data", f, e)
                store.log_run(con, f, "refused", stats[f][0], str(e))
                break
            except Exception as e:  # one bad company never stops the run
                log.warning("%s %s failed: %s", f, sym, e)
        store.log_run(con, f, "ok", stats[f][0], f"{stats[f][1]} companies")
        log.info("%s: %d rows from %d companies", f, *stats[f])
    return stats
