"""Polite HTTP for public market-data sources.

* one session per process, browser-like headers (what a normal visitor sends)
* minimum gap between requests to the same host
* retries with back-off on 429 / 5xx; 401/403 are treated as "refused" and never retried around
* optional on-disk cache for immutable files (archives, XBRL filings)
* a per-host circuit breaker: after N refusals in a row the host is skipped for the rest of the run
"""
import gzip, hashlib, logging, os, random, threading, time
from urllib.parse import urlparse

import requests

log = logging.getLogger("sources")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE, "data", "cache")

# seconds between requests per host (be gentle: these are public, free services)
MIN_GAP = {
    "www.nseindia.com": 0.8,
    "nsearchives.nseindia.com": 0.35,
    "archives.nseindia.com": 0.35,
    "www.bseindia.com": 1.0,
    "portal.amfiindia.com": 1.0,
}
DEFAULT_GAP = 0.5
MAX_REFUSALS = int(os.environ.get("BEEMER_MAX_REFUSALS", "6"))


class Refused(Exception):
    """The host refused us (403/401/blocked page). Do not try to get around it."""


class Polite:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9",
                               "Accept": "*/*"})
        self._last = {}
        self._refusals = {}
        self._warmed = set()
        self._slow = {}          # host -> extra gap after timeouts / 429s (adaptive back-off)
        self._lock = threading.Lock()

    # -- bookkeeping --
    def _wait(self, host):
        gap = MIN_GAP.get(host, DEFAULT_GAP) + self._slow.get(host, 0)
        with self._lock:
            dt_ = time.monotonic() - self._last.get(host, 0)
            if dt_ < gap:
                time.sleep(gap - dt_ + random.random() * 0.1)
            self._last[host] = time.monotonic()

    def blocked(self, host):
        return self._refusals.get(host, 0) >= MAX_REFUSALS

    def _refused(self, host, url, code):
        self._refusals[host] = self._refusals.get(host, 0) + 1
        n = self._refusals[host]
        if n == MAX_REFUSALS:
            log.warning("%s refused %d requests in a row (last HTTP %s) - skipping it for this run", host, n, code)
        raise Refused(f"{code} {url}")

    def warm_nse(self):
        """Visit the NSE home page once, as a browser would, so the API sees normal session cookies.
        If the home page itself is refused we simply carry on without cookies."""
        if "nse" in self._warmed:
            return
        self._warmed.add("nse")
        try:
            self._wait("www.nseindia.com")
            self.s.get("https://www.nseindia.com/", timeout=20)
        except requests.RequestException:
            pass

    # -- main entry --
    def get(self, url, *, headers=None, timeout=40, cache=None, retries=3, ok404=False):
        """GET a URL. ``cache`` = relative path under data/cache to keep the body forever (immutable files).
        Returns bytes, or None for 404 when ok404. Raises Refused when the host says no."""
        host = urlparse(url).netloc
        if cache:
            path = os.path.join(CACHE, cache)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    raw = f.read()
                return gzip.decompress(raw) if path.endswith(".gz") else raw
        if self.blocked(host):
            raise Refused(f"{host} blocked for this run")
        if host == "www.nseindia.com":
            self.warm_nse()
            headers = dict({"Referer": "https://www.nseindia.com/", "Accept": "application/json, text/plain, */*"},
                           **(headers or {}))
        err = None
        for attempt in range(retries):
            self._wait(host)
            try:
                r = self.s.get(url, headers=headers, timeout=timeout)
            except requests.RequestException as e:
                # the host is slow or shedding load: widen the gap for the rest of the run
                self._slow[host] = min(self._slow.get(host, 0) * 2 or 1.0, 8.0)
                log.info("%s slow (%s); gap now %.1fs", host, type(e).__name__, MIN_GAP.get(host, DEFAULT_GAP) + self._slow[host])
                err = e; time.sleep(5 * (attempt + 1)); continue
            if r.status_code == 200:
                body = r.content
                if b"Access Denied" in body[:600] and b"edgesuite" in body[:2000]:
                    self._refused(host, url, "denied-page")
                self._refusals[host] = 0
                if cache:
                    path = os.path.join(CACHE, cache)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "wb") as f:
                        f.write(gzip.compress(body) if path.endswith(".gz") else body)
                return body
            if r.status_code == 404 and ok404:
                self._refusals[host] = 0
                return None
            if r.status_code in (401, 403):
                self._refused(host, url, r.status_code)
            if r.status_code in (429, 500, 502, 503, 504):
                if r.status_code in (429, 503):
                    self._slow[host] = min(self._slow.get(host, 0) * 2 or 1.0, 8.0)
                err = f"HTTP {r.status_code}"
                time.sleep((10 if r.status_code == 429 else 3) * (attempt + 1))
                continue
            err = f"HTTP {r.status_code}"
            break
        raise IOError(f"{url}: {err}")

    def json(self, url, **kw):
        import json as _j
        body = self.get(url, **kw)
        return None if body is None else _j.loads(body)


_SESSION = None


def session():
    global _SESSION
    if _SESSION is None:
        _SESSION = Polite()
    return _SESSION


def cache_key(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]
