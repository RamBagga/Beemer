"""Universe builder: every NSE-listed tech name, tagged by sub-sector.

Inputs (all public NSE archive files, no login):
  * EQUITY_L.csv                 - every listed equity: symbol, name, series, listing date, ISIN, face value
  * index constituent CSVs       - NSE's industry tag (2023 taxonomy) for ~1,000 Total Market + Microcap names,
                                   plus membership of Nifty IT / India Digital / New Age Consumption / 500 / Midcap / Smallcap
  * board-meetings API           - NSE's legacy industry tag (e.g. "Computers - Software") for smaller names
The curated 64 in data/universe_tech.csv stay as tier 'core'; everything else found here is tier 'ext'.
The result is written to the universe_all table and to data/universe_all.csv (committed), so runs on
networks that NSE refuses still have the list.
"""
import datetime as dt, io, json, logging, os, re

import pandas as pd

from . import store
from .http import Refused, session

log = logging.getLogger("sources.universe")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SNAPSHOT = os.path.join(DATA, "universe_all.csv")
ARCH = "https://nsearchives.nseindia.com/content/indices/"

INDEX_FILES = {
    "NIFTY TOTAL MARKET": "ind_niftytotalmarket_list.csv",
    "NIFTY MICROCAP 250": "ind_niftymicrocap250_list.csv",
    "NIFTY 50": "ind_nifty50list.csv",
    "NIFTY 500": "ind_nifty500list.csv",
    "NIFTY MIDCAP 150": "ind_niftymidcap150list.csv",
    "NIFTY SMALLCAP 250": "ind_niftysmallcap250list.csv",
    "NIFTY IT": "ind_niftyitlist.csv",
    "NIFTY INDIA DIGITAL": "ind_niftyindiadigital_list.csv",
    "NIFTY INDIA NEW AGE CONSUMPTION": "ind_niftyIndiaNewAgeConsumption_list.csv",
}
TECH_MACRO = {"Information Technology": "IT services", "Telecommunication": "Telecom & networks"}
TECH_LEGACY = {
    "Computers - Software": "IT services",
    "Computers - Hardware": "Electronics & semicon design",
    "Electronics - Industrial": "Electronics & semicon design",
    "Electronics - Components": "Electronics & semicon design",
    "Telecommunication - Services": "Telecom & networks",
    "Telecommunication - Equipment": "Telecom & networks",
    "Cables - Telecom": "Telecom & networks",
}
# well-known listed electronics / EMS / fintech / platform names that NSE files under other industries
CURATED_EXTRAS = {
    "Electronics & semicon design": ["DIXON", "KAYNES", "SYRMA", "AMBER", "PGEL", "AVALON", "CYIENTDLM", "CENTUM",
                                     "DATAPATTNS", "MTARTECH", "MOSCHIP", "ASTRAMICRO", "ZENTEC", "APOLLO", "BEL",
                                     "SPEL", "SFL", "ELIN", "IKIO", "RIR", "HBLENGINE", "PARAS"],
    "Fintech": ["PAYTM", "POLICYBZR", "PINELABS", "GROWW", "ANGELONE", "CAMS", "KFINTECH", "CDSL", "BSE", "MCX",
                "MOBIKWIK", "INFIBEAM", "NSDL", "FINOPB"],
    "Internet & consumer tech": ["ETERNAL", "SWIGGY", "NYKAA", "NAUKRI", "INDIAMART", "JUSTDIAL", "CARTRADE",
                                 "EASEMYTRIP", "IXIGO", "MEESHO", "FIRSTCRY", "URBANCO", "LENSKART", "TBOTEK",
                                 "MATRIMONY", "NAZARA", "IRCTC", "ZAGGLE", "AFFLE", "ROUTE", "YATRA"],
}
# tagged by NSE as electronics but really pumps / fans / printing presses
NOT_TECH = {"SHAKTIPUMP", "VGUARD", "MANUGRAPH"}
# name matching is only used for small names NSE has not tagged at all; generic words such as "tech" or
# "technologies" catch pipes, prefab and chemicals makers, so those count only for names checked by hand
NAME_RX = re.compile(r"\b(infotech|infosys(tems)?|info ?systems|software|softech|softwares|telecom|teleservices|"
                     r"semiconductors?|computers?|cyber|infoway|digital|internet|online|e-?gov)\b", re.I)
NAME_TECH_OK = {"QUICKHEAL", "TRACXN", "PROTEAN", "SILVERTUC", "INFOBEAN", "INTENTECH", "KELLTONTEC", "IDEAFORGE",
                "DIGISPICE", "63MOONS", "SECURKLOUD", "ORIENTTECH", "XELPMOC", "PALREDTEC", "ACSTECH", "AAATECH",
                "CSM", "CURAA", "EXCELSOFT", "EQUIPPP", "AVANCE", "GATECH", "STYL", "NPST", "CEINSYS", "ALLDIGI",
                "TAALTECH", "XTRANET", "MICEL", "ONIDA", "RELIABLE", "UNIINFO", "STLNETWORK", "KAVDEFENCE",
                "PROSTARM", "XTGLOBAL", "DCI", "DEVIT", "GVPTECH", "ADROITINFO", "ARMEE", "BLUECLOUDS", "CGVAK",
                "ESDS", "LEENEE", "TERASOFT", "3IINFOLTD", "INTENTECH"}


def _csv(sess, url, cache=None):
    body = sess.get(url, cache=cache)
    df = pd.read_csv(io.BytesIO(body))
    df.columns = [c.strip() for c in df.columns]
    return df


def _legacy_industry(sess, days=210):
    """symbol -> NSE legacy industry, from the public board-meetings feed (every company meets quarterly)."""
    to = dt.date.today(); fr = to - dt.timedelta(days=days)
    url = (f"https://www.nseindia.com/api/corporate-board-meetings?index=equities"
           f"&from_date={fr:%d-%m-%Y}&to_date={to:%d-%m-%Y}")
    rows = sess.json(url, timeout=90) or []
    out = {}
    for r in rows:
        ind = (r.get("sm_indusrty") or "").strip()
        if ind and ind != "-":
            out[r.get("bm_symbol")] = ind
    return out


def build(con, core_csv):
    """Rebuild universe_all. Falls back to the committed snapshot when NSE is unreachable."""
    store.ensure(con)
    sess = session()
    core = pd.read_csv(core_csv).fillna("")
    try:
        eq = _csv(sess, "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv")
        members, macro = {}, {}
        for name, f in INDEX_FILES.items():
            try:
                d = _csv(sess, ARCH + f)
            except (Refused, IOError) as e:
                log.warning("index list %s unavailable: %s", name, e); continue
            for s, ind in zip(d["Symbol"], d.get("Industry", [None] * len(d))):
                members.setdefault(s, []).append(name)
                if ind and isinstance(ind, str):
                    macro.setdefault(s, ind)
        try:
            legacy = _legacy_industry(sess)
        except (Refused, IOError, ValueError) as e:
            log.warning("legacy industry feed unavailable (%s); using index tags only", e); legacy = {}
    except (Refused, IOError) as e:
        log.warning("NSE equity list unavailable (%s); using %s", e, SNAPSHOT)
        return _load_snapshot(con)

    extras = {s: sub for sub, syms in CURATED_EXTRAS.items() for s in syms}
    core_map = {r.symbol: r for r in core.itertuples()}
    rows = []
    for r in eq.itertuples(index=False):
        sym, name, series = r[0], r[1], r[2]
        if series not in ("EQ", "BE") and sym not in core_map:
            continue
        mi, li, idx = macro.get(sym), legacy.get(sym), members.get(sym, [])
        sub, src = None, None
        if sym in core_map:
            sub, src, tier = core_map[sym].subsector, "core", "core"
        else:
            tier = "ext"
            digital = "NIFTY INDIA DIGITAL" in idx or "NIFTY IT" in idx
            if mi in TECH_MACRO:
                sub, src = TECH_MACRO[mi], "nse_industry"
            elif sym in extras:
                sub, src = extras[sym], "curated"
            elif digital and mi == "Consumer Services":
                sub, src = "Internet & consumer tech", "nifty_digital"
            elif digital and mi == "Financial Services":
                sub, src = "Fintech", "nifty_digital"
            elif li in TECH_LEGACY:
                sub, src = TECH_LEGACY[li], "nse_legacy_industry"
            elif not mi and not li and (sym in NAME_TECH_OK or NAME_RX.search(name or "")):
                sub, src = "Other tech", "name_match"
        if not sub or (tier == "ext" and sym in NOT_TECH):
            continue
        rows.append(dict(symbol=sym, name=name, isin=r[6], series=series, listing_date=store.iso(r[3]),
                         face_value=store.num(r[7]), macro_industry=mi, legacy_industry=li, subsector=sub,
                         tier=tier, indices="|".join(idx), class_source=src,
                         updated_at=dt.date.today().isoformat()))
    # core names that are not in EQUITY_L any more (renamed / delisted) stay in, flagged
    have = {x["symbol"] for x in rows}
    for s, c in core_map.items():
        if s not in have:
            rows.append(dict(symbol=s, name=c.name, isin=None, series=None, listing_date=None, face_value=None,
                             macro_industry=None, legacy_industry=None, subsector=c.subsector, tier="core",
                             indices="", class_source="core", updated_at=dt.date.today().isoformat()))
    df = pd.DataFrame(rows).sort_values(["tier", "symbol"])
    df.to_csv(SNAPSHOT, index=False)
    _write(con, df)
    log.info("universe_all: %d names (%d core, %d ext)", len(df), (df.tier == "core").sum(), (df.tier == "ext").sum())
    store.log_run(con, "universe", "ok", len(df), df.class_source.value_counts().to_dict())
    return df


def _write(con, df):
    con.execute("DELETE FROM universe_all")
    cols = ["symbol", "name", "isin", "series", "listing_date", "face_value", "macro_industry", "legacy_industry",
            "subsector", "tier", "indices", "class_source", "updated_at"]
    con.executemany(f"INSERT OR REPLACE INTO universe_all({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                    [tuple(None if pd.isna(v) else v for v in rec) for rec in df[cols].itertuples(index=False)])
    con.commit()


def _load_snapshot(con):
    if not os.path.exists(SNAPSHOT):
        log.warning("no universe snapshot; extended universe empty")
        store.log_run(con, "universe", "failed", 0, "no network and no snapshot")
        return pd.DataFrame()
    df = pd.read_csv(SNAPSHOT)
    _write(con, df)
    store.log_run(con, "universe", "snapshot", len(df), "NSE unreachable, used committed snapshot")
    return df


def load(con, tier=None):
    q = "SELECT * FROM universe_all" + (" WHERE tier=?" if tier else "")
    try:
        return pd.read_sql(q, con, params=(tier,) if tier else None)
    except Exception:
        return pd.DataFrame()
