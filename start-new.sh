#!/usr/bin/env bash
# One-command local run of the Spring Boot API and the React app.
# The Streamlit app (./start.sh) is left alone.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
pids=()
cleanup() { for p in "${pids[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/python bootstrap.py || echo "data bootstrap did not refresh; continuing with whatever is on disk"

if ! curl -fsS http://127.0.0.1:8080/actuator/health >/dev/null 2>&1; then
  (cd backend && mvn -q -DskipTests spring-boot:run) &
  pids+=($!)
fi
if ! curl -fsS http://127.0.0.1:5173 >/dev/null 2>&1; then
  (cd frontend && npm install && npm run dev -- --host 127.0.0.1 --port 5173) &
  pids+=($!)
fi

echo "API   http://127.0.0.1:8080   (Swagger http://127.0.0.1:8080/swagger-ui.html)"
echo "App   http://127.0.0.1:5173"
if [[ ${#pids[@]} -eq 0 ]]; then
  echo "Both were already running."
  trap - EXIT
  exit 0
fi
wait
