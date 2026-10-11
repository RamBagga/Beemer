"""NSE daily archive files (official end-of-day data, static public files).

* sec_bhavdata_full_DDMMYYYY.csv - every traded security: OHLC, VWAP, volume, trades and DELIVERY quantity / %
  (available from 2020 on the archive host). Stored for universe_all symbols only, to keep the DB small.
* ind_close_all_DDMMYYYY.csv     - every NSE index: OHLC, turnover and index P/E, P/B, dividend yield
  (available from 2015).
Days are tracked in archive_days so each file is fetched once; holidays (404) are remembered too.
"""
import datetime as dt, io, logging

import pandas as pd

from . import store
from .http import Refused, session

log = logging.getLogger("sources.archives")
HOST = "https://nsearchives.nseindia.com"
SOURCES = {
    "delivery": (HOST + "/products/content/sec_bhavdata_full_{d:%d%m%Y}.csv", dt.date(2020, 1, 1)),
    "index_eod": (HOST + "/content/indices/ind_close_all_{d:%d%m%Y}.csv", dt.date(2015, 1, 1)),
}


def _days(con, source, since):
    done = {r[0]: r[1] for r in con.execute("SELECT date, status FROM archive_days WHERE source=?", (source,))}
    today = dt.date.today()
    d = since
    while d <= today:
        if d.weekday() < 5:
            st = done.get(d.isoformat())
            # retry recent misses (files appear after ~6 PM IST); older holidays stay skipped
            if st is None or (st != "ok" and (today - d).days <= 5):
                yield d
        d += dt.timedelta(days=1)


def _parse_delivery(body, symbols):
    df = pd.read_csv(io.BytesIO(body), skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    df["SERIES"] = df["SERIES"].astype(str).str.strip()
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip()
    df = df[df.SYMBOL.isin(symbols) & df.SERIES.isin(["EQ", "BE", "BZ", "SM", "ST"])]
    out = []
    for r in df.itertuples(index=False):
        d = store.iso(str(r.DATE1).strip())
        out.append((r.SYMBOL, d, r.SERIES, store.num(r.PREV_CLOSE), store.num(r.OPEN_PRICE), store.num(r.HIGH_PRICE),
                    store.num(r.LOW_PRICE), store.num(r.CLOSE_PRICE), store.num(r.AVG_PRICE),
                    store.num(r.TTL_TRD_QNTY), store.num(r.TURNOVER_LACS), store.num(r.NO_OF_TRADES),
                    store.num(r.DELIV_QTY), store.num(r.DELIV_PER)))
    return out


def _parse_index(body):
    df = pd.read_csv(io.BytesIO(body))
    df.columns = [c.strip() for c in df.columns]
    out = []
    for r in df.itertuples(index=False):
        out.append((str(r[0]).strip(), store.iso(str(r[1]).strip()), store.num(r[2]), store.num(r[3]),
                    store.num(r[4]), store.num(r[5]), store.num(r[7]), store.num(r[8]), store.num(r[9]),
                    store.num(r[10]), store.num(r[11]), store.num(r[12])))
    return out


def update(con, source, since=None, symbols=None, max_days=None):
    """Fetch missing days for one archive source. Returns rows written."""
    store.ensure(con)
    tmpl, first = SOURCES[source]
    since = since or first
    if source == "delivery" and symbols is None:
        symbols = {r[0] for r in con.execute("SELECT symbol FROM universe_all")}
    sess = session()
    n_rows = n_days = misses = 0
    for d in _days(con, source, since):
        if max_days and n_days >= max_days:
            break
        try:
            body = sess.get(tmpl.format(d=d), ok404=True, timeout=60)
        except Refused as e:
            log.warning("%s: NSE archives refused us (%s); stopping, will resume next run", source, e)
            store.log_run(con, source, "refused", n_rows, str(e))
            return n_rows
        except IOError as e:
            log.warning("%s %s: %s", source, d, e); misses += 1
            if misses > 10:
                break
            continue
        n_days += 1
        if body is None:
            con.execute("INSERT OR REPLACE INTO archive_days VALUES (?,?,?,?)", (source, d.isoformat(), "none", 0))
            continue
        try:
            rows = _parse_delivery(body, symbols) if source == "delivery" else _parse_index(body)
        except Exception as e:
            log.warning("%s %s: unparseable (%s)", source, d, e)
            con.execute("INSERT OR REPLACE INTO archive_days VALUES (?,?,?,?)", (source, d.isoformat(), "bad", 0))
            continue
        if source == "delivery":
            con.executemany("INSERT OR REPLACE INTO delivery VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        else:
            con.executemany("INSERT OR REPLACE INTO index_eod VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.execute("INSERT OR REPLACE INTO archive_days VALUES (?,?,?,?)", (source, d.isoformat(), "ok", len(rows)))
        n_rows += len(rows)
        if n_days % 50 == 0:
            con.commit(); log.info("%s: %d days, %d rows so far (at %s)", source, n_days, n_rows, d)
    con.commit()
    store.log_run(con, source, "ok", n_rows, f"{n_days} days")
    log.info("%s: %d new days, %d rows", source, n_days, n_rows)
    return n_rows
