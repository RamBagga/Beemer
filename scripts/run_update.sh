#!/usr/bin/env bash
# Wrapper used by cron. Usage: run_update.sh [snapshot|eod]
# Portable lock (macOS has no flock): a lock directory; stale locks older than 3 h are cleared.
D="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-eod}"
ARGS=""; [ "$MODE" = "snapshot" ] && ARGS="--prices-only"
mkdir -p "$D/logs"; LOCK="$D/logs/update.lockdir"
if [ -d "$LOCK" ] && [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180 2>/dev/null)" ]; then rmdir "$LOCK" 2>/dev/null; fi
mkdir "$LOCK" 2>/dev/null || { echo "$(date) another update is running, skipping" >> "$D/logs/update_$MODE.log"; exit 0; }
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
cd "$D" && "$D/.venv/bin/python" "$D/update_data.py" $ARGS >> "$D/logs/update_$MODE.log" 2>&1
