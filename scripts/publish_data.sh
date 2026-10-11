#!/usr/bin/env bash
# Publish data/market.db + data/metrics.parquet as assets on the rolling GitHub Release `data-latest`,
# which cloud deployments download on startup (see bootstrap.py).
# Used by .github/workflows/update-data.yml; can also be run by hand from a machine with `gh` signed in
# (e.g. to seed the release from a full local build:  ./scripts/publish_data.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${BEEMER_DATA_TAG:-data-latest}"
PY="${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}"
OUT="$(mktemp -d)"; trap 'rm -rf "$OUT"' EXIT

"$PY" - "$OUT" <<'PY'
import datetime as dt, json, os, sqlite3, sys
out = sys.argv[1]
src = sqlite3.connect("data/market.db")
src.execute(f"VACUUM INTO '{os.path.join(out, 'market.db')}'")      # consistent, compact snapshot
q = lambda sql: src.execute(sql).fetchone()[0]
m = {
    "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    "last_price_date": q("SELECT MAX(date) FROM prices WHERE symbol NOT LIKE '^%'"),
    "price_rows": q("SELECT COUNT(*) FROM prices"),
    "companies": q("SELECT COUNT(*) FROM universe"),
    "companies_all": q("SELECT COUNT(*) FROM company_metrics"),
    "fundamentals_rows": q("SELECT COUNT(*) FROM fundamentals"),
    "fundamentals_oldest_fetch": q("SELECT MIN(fetched_at) FROM fund_meta"),
    "fundamentals_newest_fetch": q("SELECT MAX(fetched_at) FROM fund_meta"),
    "built_by": os.environ.get("GITHUB_WORKFLOW") and f"github-actions run {os.environ.get('GITHUB_RUN_ID')}" or "manual",
    "license_note": "Derived from free public sources (Yahoo Finance, NSE archives and corporate filings, screener.in) for personal, non-commercial use.",
}
json.dump(m, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(json.dumps(m, indent=1))
PY
gzip -9 "$OUT/market.db"
cp data/metrics.parquet "$OUT/metrics.parquet"
ls -lh "$OUT"

if ! gh release view "$TAG" >/dev/null 2>&1; then
  gh release create "$TAG" --title "Beemer data (rolling)" --prerelease --latest=false \
    --notes "Machine-generated data snapshot, refreshed every weekday by the 'Update data' workflow. Downloaded automatically by deployed apps (bootstrap.py). Built from free public sources for personal, non-commercial use - see DEPLOYMENT.md."
fi
# data files first, manifest last: hosts only switch to a new snapshot once the manifest changes
gh release upload "$TAG" "$OUT/market.db.gz" "$OUT/metrics.parquet" --clobber
gh release upload "$TAG" "$OUT/manifest.json" --clobber
echo "✓ published to release $TAG"
