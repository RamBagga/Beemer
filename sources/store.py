"""SQLite schema for the expanded datasets plus run bookkeeping."""
import datetime as dt, json, sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS universe_all(
    symbol TEXT PRIMARY KEY, name TEXT, isin TEXT, series TEXT, listing_date TEXT, face_value REAL,
    macro_industry TEXT, legacy_industry TEXT, subsector TEXT, tier TEXT, indices TEXT, class_source TEXT,
    updated_at TEXT);
CREATE TABLE IF NOT EXISTS index_eod(
    index_name TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, pct_change REAL,
    volume REAL, turnover_cr REAL, pe REAL, pb REAL, div_yield REAL, PRIMARY KEY(index_name, date));
CREATE TABLE IF NOT EXISTS delivery(
    symbol TEXT, date TEXT, series TEXT, prev_close REAL, open REAL, high REAL, low REAL, close REAL,
    avg_price REAL, volume REAL, turnover_lacs REAL, trades REAL, deliv_qty REAL, deliv_pct REAL,
    PRIMARY KEY(symbol, date, series));
CREATE TABLE IF NOT EXISTS archive_days(source TEXT, date TEXT, status TEXT, rows INTEGER, PRIMARY KEY(source, date));
CREATE TABLE IF NOT EXISTS corp_actions(
    symbol TEXT, ex_date TEXT, record_date TEXT, subject TEXT, kind TEXT, amount REAL, ratio TEXT,
    face_value REAL, series TEXT, PRIMARY KEY(symbol, ex_date, subject));
CREATE TABLE IF NOT EXISTS board_meetings(
    symbol TEXT, meeting_date TEXT, purpose TEXT, description TEXT, announced_at TEXT,
    PRIMARY KEY(symbol, meeting_date, purpose));
CREATE TABLE IF NOT EXISTS shareholding(
    symbol TEXT, period TEXT, promoter REAL, public REAL, fii REAL, dii REAL, mf REAL, insurance REAL,
    retail REAL, hni REAL, employee_trusts REAL, other REAL, pledge_flag TEXT, source TEXT, filed_at TEXT,
    xbrl TEXT, PRIMARY KEY(symbol, period));
CREATE TABLE IF NOT EXISTS insider_trades(
    symbol TEXT, record_id TEXT, person TEXT, category TEXT, txn_type TEXT, mode TEXT, security TEXT,
    qty REAL, value REAL, before_pct REAL, after_pct REAL, from_date TEXT, to_date TEXT, intimated TEXT,
    disclosed_at TEXT, PRIMARY KEY(symbol, record_id));
CREATE TABLE IF NOT EXISTS deals(
    kind TEXT, date TEXT, symbol TEXT, name TEXT, client TEXT, side TEXT, qty REAL, price REAL,
    remarks TEXT, PRIMARY KEY(kind, date, symbol, client, side, qty, price));
CREATE TABLE IF NOT EXISTS results_filings(
    symbol TEXT, period_end TEXT, basis TEXT, audited TEXT, filed_at TEXT, url TEXT, parsed INTEGER,
    PRIMARY KEY(symbol, period_end, basis));
CREATE TABLE IF NOT EXISTS results_xbrl(
    symbol TEXT, period_end TEXT, basis TEXT, item TEXT, value REAL, PRIMARY KEY(symbol, period_end, basis, item));
CREATE TABLE IF NOT EXISTS feed_meta(symbol TEXT, feed TEXT, fetched_at TEXT, rows INTEGER, PRIMARY KEY(symbol, feed));
CREATE TABLE IF NOT EXISTS price_audit(
    symbol TEXT, ex_date TEXT, kind TEXT, ratio TEXT, factor REAL, day_move REAL, status TEXT,
    PRIMARY KEY(symbol, ex_date, kind));
CREATE TABLE IF NOT EXISTS source_runs(ts TEXT, source TEXT, status TEXT, rows INTEGER, detail TEXT);
CREATE INDEX IF NOT EXISTS ix_deals_symbol ON deals(symbol, date);
CREATE INDEX IF NOT EXISTS ix_delivery_date ON delivery(date);
"""


def ensure(con: sqlite3.Connection):
    con.executescript(SCHEMA)
    con.commit()


def log_run(con, source, status, rows=0, detail=""):
    con.execute("INSERT INTO source_runs VALUES (?,?,?,?,?)",
                (dt.datetime.now().isoformat(timespec="seconds"), source, status, int(rows or 0),
                 detail if isinstance(detail, str) else json.dumps(detail)))
    con.commit()


def iso(d, fmts=("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%Y-%m-%d")):
    """NSE dates ('10-Jun-2026', '30-JUN-2026', '09-10-2026') to ISO; None if unparseable."""
    if not d or d in ("-", "NA", "null"):
        return None
    d = d.strip()
    for f in fmts:
        try:
            x = dt.datetime.strptime(d.title() if "%b" in f or "%B" in f else d, f)
            return x.strftime("%Y-%m-%d %H:%M" if ("%H" in f) else "%Y-%m-%d")
        except ValueError:
            continue
    return None


def num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace(",", "").strip()
    if s in ("", "-", "Nil", "NA", "nil", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None
