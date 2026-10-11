#!/usr/bin/env bash
# Installs the weekday refresh schedule (macOS + Linux). Times are converted from IST to the machine's clock:
#   15:45 IST snapshot (prices + metrics) and 18:30 IST end-of-day run (prices + fundamentals if >7 days old + metrics).
# Remove with: crontab -l | grep -v beemer-update | crontab -
D="$(cd "$(dirname "$0")/.." && pwd)"
Z=$(date +%z)                                  # e.g. +0530, +0000, -0700
SIGN=${Z:0:1}; ZH=$((10#${Z:1:2})); ZM=$((10#${Z:3:2}))
LOCAL_OFF=$((ZH*60+ZM)); [ "$SIGN" = "-" ] && LOCAL_OFF=$((-LOCAL_OFF))
conv() {  # $1 = IST minutes since midnight → "MM HH" on this machine (assumes same weekday after shift)
  local m=$(( ($1 - 330 + LOCAL_OFF + 1440) % 1440 )); echo "$((m%60)) $((m/60))"; }
S=$(conv $((15*60+45))); E=$(conv $((18*60+30)))
( crontab -l 2>/dev/null | grep -v "beemer-update" ;
  echo "$S * * 1-5 $D/scripts/run_update.sh snapshot # beemer-update snapshot 15:45 IST";
  echo "$E * * 1-5 $D/scripts/run_update.sh eod # beemer-update eod 18:30 IST" ) | crontab -
if [ "$(uname)" = "Linux" ]; then
  pgrep -x cron >/dev/null || (sudo -n /usr/sbin/cron 2>/dev/null || /usr/sbin/cron 2>/dev/null) || echo "WARNING: start the cron daemon (sudo service cron start)"
else
  echo "note (macOS): cron jobs only run while the Mac is awake; the first install may prompt for permission."
fi
crontab -l | grep beemer-update
