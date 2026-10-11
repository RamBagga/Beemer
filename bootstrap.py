#!/usr/bin/env python3
"""Data bootstrap — make sure data/market.db + data/metrics.parquet exist (and stay fresh) on any host.

Cloud hosts start from a fresh git checkout, and the data files are gitignored (≈21 MB, ~10 min to build).
So the GitHub Actions workflow (.github/workflows/update-data.yml) rebuilds the data every weekday and
publishes it as assets on a rolling GitHub Release (tag `data-latest`). This module downloads it.

Order of preference:
  1. Data already on disk that was built locally (no manifest) → used as is, never overwritten.
  2. Published data from the GitHub Release → downloaded if missing, re-checked every BEEMER_DATA_MAX_AGE_HOURS.
  3. Nothing published / no network → run the pipeline here (BEEMER_BOOTSTRAP_FALLBACK=prices|full|none).

Usage:
  python bootstrap.py               # ensure data (what Docker/Render run before starting the app)
  python bootstrap.py --force       # re-download published data even if present
  python bootstrap.py --download-only   # download if published; never run the pipeline (used by CI)
  python bootstrap.py --check       # verify the local data files; exit 1 if unusable

Environment (all optional — see .env.example):
  BEEMER_DATA_REPO            owner/repo hosting the release   (default RamBagga/Beemer)
  BEEMER_DATA_TAG             release tag                       (default data-latest)
  BEEMER_DATA_URL             override base URL for the three files (any static host / S3 / R2)
  BEEMER_DATA_MAX_AGE_HOURS   how often a running host re-checks for new data (default 6)
  BEEMER_BOOTSTRAP_FALLBACK   prices (default) | full | none
  GITHUB_TOKEN / BEEMER_GITHUB_TOKEN   only needed if the repo is private
"""
import argparse, datetime as dt, gzip, json, logging, os, shutil, sqlite3, subprocess, sys, tempfile, threading, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "market.db")
METRICS = os.path.join(DATA, "metrics.parquet")
MANIFEST = os.path.join(DATA, ".published_manifest.json")   # present only when data came from a release

REPO = os.environ.get("BEEMER_DATA_REPO", "RamBagga/Beemer")
TAG = os.environ.get("BEEMER_DATA_TAG", "data-latest")
BASE_URL = os.environ.get("BEEMER_DATA_URL", "").rstrip("/")
MAX_AGE_H = float(os.environ.get("BEEMER_DATA_MAX_AGE_HOURS", "6"))
FALLBACK = os.environ.get("BEEMER_BOOTSTRAP_FALLBACK", "prices").lower()
TOKEN = os.environ.get("BEEMER_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
FILES = ("manifest.json", "market.db.gz", "metrics.parquet")
UA = "beemer-bootstrap/1.0"

log = logging.getLogger("bootstrap")
_lock = threading.Lock()


# ---------------- download helpers ----------------
def _asset_urls():
    """Return {filename: (url, headers)} for the published files."""
    if BASE_URL:
        return {f: (f"{BASE_URL}/{f}", {"User-Agent": UA}) for f in FILES}
    if not TOKEN:   # public repo: plain release download links (redirect to a CDN, no auth)
        return {f: (f"https://github.com/{REPO}/releases/download/{TAG}/{f}", {"User-Agent": UA}) for f in FILES}
    # private repo: resolve asset ids through the API, then download them as octet-stream
    h = {"User-Agent": UA, "Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}", headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        assets = {a["name"]: a["url"] for a in json.load(r)["assets"]}
    dl = dict(h, Accept="application/octet-stream")
    return {f: (assets[f], dl) for f in FILES if f in assets}


def _fetch(url, headers, dest):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)


def _read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def check(db=DB, metrics=METRICS):
    """True if both files exist and look sane."""
    try:
        if not (os.path.exists(db) and os.path.exists(metrics)):
            return False
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        con.close()
        return n > 0 and os.path.getsize(metrics) > 0
    except Exception as e:
        log.warning("data check failed: %s", e)
        return False


def download(force=False):
    """Download published data. Returns True if new data was installed, False if already current."""
    urls = _asset_urls()
    if "manifest.json" not in urls:
        raise RuntimeError(f"no published data found for {REPO}@{TAG}")
    os.makedirs(DATA, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DATA) as tmp:
        man_path = os.path.join(tmp, "manifest.json")
        _fetch(*urls["manifest.json"], man_path)
        remote = _read_json(man_path) or {}
        local = _read_json(MANIFEST) or {}
        if not force and check() and local.get("generated_at") == remote.get("generated_at"):
            local["checked_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            with open(MANIFEST, "w") as f:
                json.dump(local, f, indent=1)
            log.info("published data unchanged (%s)", remote.get("generated_at"))
            return False
        gz, db_tmp, met_tmp = (os.path.join(tmp, n) for n in ("market.db.gz", "market.db", "metrics.parquet"))
        _fetch(*urls["market.db.gz"], gz)
        with gzip.open(gz, "rb") as src, open(db_tmp, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        _fetch(*urls["metrics.parquet"], met_tmp)
        if not check(db_tmp, met_tmp):
            raise RuntimeError("downloaded data failed validation")
        os.replace(db_tmp, DB)          # atomic swap; open connections keep reading the old inode
        os.replace(met_tmp, METRICS)
        remote["checked_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        with open(MANIFEST, "w") as f:
            json.dump(remote, f, indent=1)
    log.info("installed published data generated at %s (last price %s)", remote.get("generated_at"), remote.get("last_price_date"))
    return True


def run_pipeline(mode=FALLBACK):
    args = [sys.executable, os.path.join(BASE, "update_data.py")]
    if mode == "prices":
        args.append("--prices-only")
    log.info("building data locally: %s", " ".join(args[1:]))
    subprocess.run(args, cwd=BASE, check=True)


def _stale():
    m = _read_json(MANIFEST)
    if not m:
        return False            # locally built data: the local scheduler owns it
    try:
        last = dt.datetime.fromisoformat(m.get("checked_at") or m["generated_at"])
    except Exception:
        return True
    return (dt.datetime.now(dt.timezone.utc) - last).total_seconds() > MAX_AGE_H * 3600


def ensure_data(force=False, allow_pipeline=True):
    """Make sure usable data is on disk. Returns a small status dict (safe to call often)."""
    with _lock:
        have = check()
        status = {"source": "local" if have and not os.path.exists(MANIFEST) else "release", "updated": False}
        if have and not force and not _stale():
            status["version"] = (_read_json(MANIFEST) or {}).get("generated_at", "local")
            return status
        try:
            status["updated"] = download(force=force)
            status["source"] = "release"
        except Exception as e:
            log.warning("could not download published data: %s", e)
            if not check():
                if allow_pipeline and FALLBACK in ("prices", "full"):
                    run_pipeline(FALLBACK)
                    status.update(source="pipeline", updated=True)
                else:
                    status["source"] = "missing"
        status["version"] = (_read_json(MANIFEST) or {}).get("generated_at", status["source"])
        return status


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true", help="re-download published data even if present")
    ap.add_argument("--download-only", action="store_true", help="never fall back to the pipeline")
    ap.add_argument("--check", action="store_true", help="only verify local data")
    a = ap.parse_args()
    if a.check:
        ok = check()
        print("data OK" if ok else "data missing or invalid")
        sys.exit(0 if ok else 1)
    s = ensure_data(force=a.force, allow_pipeline=not a.download_only)
    print(json.dumps(s))
    sys.exit(0 if check() else 1)


if __name__ == "__main__":
    main()
