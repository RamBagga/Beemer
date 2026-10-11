#!/bin/sh
# Download the published snapshot, then refresh on the same clock as GitHub Actions
# (15:45 and 18:30 IST = 10:15 and 13:00 UTC, weekdays).
cd /app
python bootstrap.py || echo "bootstrap failed; will retry next cycle"
while true; do
  dow=$(date -u +%u)
  hm=$(date -u +%H%M)
  if [ "$dow" -le 5 ] && [ "$hm" = "1015" ]; then
    python update_data.py --prices-only || true
    sleep 70
  elif [ "$dow" -le 5 ] && [ "$hm" = "1300" ]; then
    python update_data.py || true
    sleep 70
  fi
  sleep 20
done
