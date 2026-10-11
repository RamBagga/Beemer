#!/usr/bin/env bash
# BEEMER — one-command start (macOS + Linux).
#   ./start.sh            set up (first run), load data if missing, start the app in the background
#   ./start.sh --fg       same, but run the app in the foreground
#   ./start.sh --stop     stop the app
#   ./start.sh --status   show whether it is running and where
#   ./start.sh --cron     also install the weekday refresh schedule (15:45 + 18:30 IST) — optional
#   PORT=8600 ./start.sh  use a specific port (default: 8501, or the next free one)
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
D="$(cd "$(dirname "$0")" && pwd)"; cd "$D"; mkdir -p logs data
PIDF="logs/streamlit.pid"; PORTF="logs/streamlit.port"

running() { [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }
stop() {
  if running; then kill "$(cat "$PIDF")" 2>/dev/null || true; echo "✓ stopped"; fi
  rm -f "$PIDF" "$PORTF"
}
port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

FG=0; CRON=0
for a in "$@"; do
  case "$a" in
    --stop) stop; exit 0 ;;
    --status) if running; then echo "running (pid $(cat "$PIDF")) → http://localhost:$(cat "$PORTF" 2>/dev/null || echo 8501)"; else echo "not running"; fi; exit 0 ;;
    --fg) FG=1 ;;
    --cron) CRON=1 ;;
    *) echo "unknown option: $a"; exit 1 ;;
  esac
done

# 1. virtualenv (prefer a mature Python; 3.11–3.13 have wheels for every dependency)
if [ ! -x .venv/bin/python ]; then
  PY=""
  for c in python3.12 python3.13 python3.11 python3; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
  [ -z "$PY" ] && { echo "Python 3.11+ not found (macOS: brew install python@3.12)"; exit 1; }
  echo "→ creating virtualenv with $($PY --version)"
  "$PY" -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

# 2. data
if [ ! -f data/metrics.parquet ]; then
  echo "→ first run: downloading prices + fundamentals (≈8–10 min, polite rate limits)…"
  .venv/bin/python update_data.py
fi

# 3. optional schedule
[ "$CRON" = 1 ] && ./scripts/install_cron.sh

# 4. app
stop >/dev/null
PORT="${PORT:-8501}"
while port_busy "$PORT"; do PORT=$((PORT+1)); done
cd app
if [ "$FG" = 1 ]; then echo "$PORT" > "../$PORTF"; exec ../.venv/bin/streamlit run main.py --server.port "$PORT"; fi
# detach into its own session so it survives the terminal / parent process exiting (macOS has no `setsid` binary)
nohup ../.venv/bin/python -c 'import os,sys; os.setsid(); os.execv(sys.argv[1], sys.argv[1:])' \
  ../.venv/bin/streamlit run main.py --server.port "$PORT" > ../logs/streamlit.log 2>&1 < /dev/null &
echo $! > "../$PIDF"; echo "$PORT" > "../$PORTF"
cd ..
for i in $(seq 1 45); do curl -sf "http://localhost:$PORT/_stcore/health" >/dev/null 2>&1 && break; sleep 1; done
if curl -sf "http://localhost:$PORT/_stcore/health" >/dev/null 2>&1; then
  echo "✓ BEEMER is running → http://localhost:$PORT   (logs: logs/streamlit.log · stop: ./start.sh --stop)"
else
  echo "✗ app did not come up — see logs/streamlit.log"; exit 1
fi
