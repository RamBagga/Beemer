#!/usr/bin/env bash
# Usage: scripts/healthcheck.sh [base-url]   e.g. scripts/healthcheck.sh https://beemer.streamlit.app
# Checks the Streamlit health endpoint and the app shell; exits non-zero if either fails.
URL="${1:-http://localhost:${PORT:-8501}}"; URL="${URL%/}"
h=$(curl -fsS --max-time 20 "$URL/_stcore/health" 2>/dev/null) || { echo "✗ $URL/_stcore/health unreachable"; exit 1; }
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$URL/")
[ "$h" = "ok" ] && [ "$code" = "200" ] && echo "✓ $URL healthy (health=$h, page=$code)" && exit 0
echo "✗ $URL unhealthy (health=$h, page=$code)"; exit 1
