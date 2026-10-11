#!/usr/bin/env bash
# Spring Boot API + React dev server (macOS + Linux). Streamlit (./start.sh) is left alone.
#   ./start-new.sh            build the jar if needed, start API and web in the background
#   ./start-new.sh --stop     stop both
#   ./start-new.sh --status   show whether they are running
# Logs: logs/api.log and logs/web.log. Processes are detached, so closing the terminal does not stop them.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
D="$(cd "$(dirname "$0")" && pwd)"; cd "$D"; mkdir -p logs data
APIPID="logs/api.pid"; WEBPID="logs/web.pid"
JAR="backend/target/beemer-api-1.0.0.jar"
API_PORT="${API_PORT:-8080}"; WEB_PORT="${WEB_PORT:-5173}"

running() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

stop_one() {
  local pidf="$1" name="$2"
  if running "$pidf"; then
    local P; P="$(cat "$pidf")"
    kill "$P" 2>/dev/null || true
    # session leader from the setsid detach: take the group with it (vite/java children)
    kill -TERM -"$P" 2>/dev/null || true
    local _
    for _ in $(seq 1 20); do kill -0 "$P" 2>/dev/null || break; sleep 0.5; done
    if kill -0 "$P" 2>/dev/null; then kill -KILL "$P" 2>/dev/null || true; kill -KILL -"$P" 2>/dev/null || true; fi
    echo "✓ stopped $name"
  fi
  rm -f "$pidf"
}
stop() { stop_one "$WEBPID" "web"; stop_one "$APIPID" "api"; }

status() {
  if running "$APIPID"; then echo "api running (pid $(cat "$APIPID")) → http://127.0.0.1:$API_PORT"; else echo "api not running"; fi
  if running "$WEBPID"; then echo "web running (pid $(cat "$WEBPID")) → http://127.0.0.1:$WEB_PORT"; else echo "web not running"; fi
}

# openjdk version "21.0.2" / java version "1.8.0_392" → 21 / 8
java_major() { "$1" -version 2>&1 | awk -F'[".]' '/version/ { if ($2=="1") print $3; else print $2; exit }'; }

# Prefer a JDK 21 even when `java` on PATH is 17. Prints the java binary.
pick_java() {
  local c major seen="" jh
  local -a candidates=()
  if [[ -n "${JAVA_HOME:-}" && -x "${JAVA_HOME}/bin/java" ]]; then candidates+=("${JAVA_HOME}/bin/java"); fi
  [[ -x /opt/homebrew/opt/openjdk@21/bin/java ]] && candidates+=("/opt/homebrew/opt/openjdk@21/bin/java")
  [[ -x /usr/local/opt/openjdk@21/bin/java ]] && candidates+=("/usr/local/opt/openjdk@21/bin/java")
  if [[ -x /usr/libexec/java_home ]]; then
    jh="$(/usr/libexec/java_home -v 21 2>/dev/null || true)"
    [[ -n "$jh" && -x "$jh/bin/java" ]] && candidates+=("$jh/bin/java")
  fi
  if command -v java >/dev/null 2>&1; then candidates+=("$(command -v java)"); fi
  # ${#a[@]} is safe on macOS bash 3.2; expanding an empty "${a[@]}" under set -u is not
  if [[ ${#candidates[@]} -gt 0 ]]; then
    for c in "${candidates[@]}"; do
      case " $seen " in *" $c "*) continue ;; esac
      seen="$seen $c"
      major="$(java_major "$c" || true)"
      if [[ "$major" == "21" ]]; then printf '%s\n' "$c"; return 0; fi
    done
  fi
  local found="no java on PATH"
  if command -v java >/dev/null 2>&1; then found="Java $(java_major "$(command -v java)" || echo '?') at $(command -v java)"; fi
  echo "Java 21 is required to run the API ($found)." >&2
  echo "On macOS: brew install openjdk@21" >&2
  echo "Or set JAVA_HOME to a JDK 21 install." >&2
  return 1
}

jar_stale() {
  [[ ! -f "$JAR" ]] && return 0
  local f
  f="$(find backend/pom.xml backend/src -type f -newer "$JAR" -print 2>/dev/null | head -n 1 || true)"
  [[ -n "$f" ]]
}

# $1 pidfile  $2 logfile  $3 working directory  $4... command
# macOS has no setsid(1). A short Python process starts a new session, then execs the command
# so the pid file is the real server and it outlives this shell.
detach() {
  local pidf="$1" logf="$2" dir="$3"
  shift 3
  nohup .venv/bin/python -c 'import os,sys; os.chdir(sys.argv[1]); os.setsid(); os.execv(sys.argv[2], sys.argv[2:])' \
    "$dir" "$@" > "$logf" 2>&1 < /dev/null &
  echo $! > "$pidf"
}

for a in "$@"; do
  case "$a" in
    --stop) stop; exit 0 ;;
    --status) status; exit 0 ;;
    *) echo "unknown option: $a"; exit 1 ;;
  esac
done

if [[ ! -x .venv/bin/python ]]; then
  PY=""
  for c in python3.12 python3.13 python3.11 python3; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
  [[ -z "$PY" ]] && { echo "Python 3.11+ not found (macOS: brew install python@3.12)"; exit 1; }
  echo "→ creating virtualenv with $($PY --version)"
  "$PY" -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

JAVA_BIN="$(pick_java)" || exit 1
JAVA_HOME="$(cd "$(dirname "$JAVA_BIN")/.." && pwd -P)"
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"
echo "→ Java $(java_major "$JAVA_BIN") ($JAVA_HOME)"

# Fills company_metrics from metrics.parquet when the local db predates that table.
.venv/bin/python bootstrap.py || echo "data bootstrap did not refresh; continuing with whatever is on disk"

if [[ ! -x frontend/node_modules/.bin/vite ]]; then
  command -v npm >/dev/null 2>&1 || { echo "Node.js is required (macOS: brew install node)"; exit 1; }
  echo "→ installing frontend dependencies"
  (cd frontend && npm install)
fi

stop >/dev/null
if port_busy "$API_PORT"; then echo "✗ port $API_PORT is already in use"; exit 1; fi
if port_busy "$WEB_PORT"; then echo "✗ port $WEB_PORT is already in use"; exit 1; fi

if jar_stale; then
  command -v mvn >/dev/null 2>&1 || { echo "Maven is required to build the API (macOS: brew install maven)"; exit 1; }
  echo "→ building the API jar (Java $(java_major "$JAVA_BIN"))"
  (cd backend && mvn -q -DskipTests package)
fi
[[ -f "$JAR" ]] || { echo "✗ $JAR was not produced — see the Maven output above"; exit 1; }

export BEEMER_DATA_DIR="$D/data"
detach "$APIPID" logs/api.log "$D" "$JAVA_BIN" -jar "$D/$JAR"
detach "$WEBPID" logs/web.log "$D/frontend" "$D/frontend/node_modules/.bin/vite" --host 127.0.0.1 --port "$WEB_PORT"

api_code="000"
for _ in $(seq 1 90); do
  api_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$API_PORT/actuator/health" || true)"
  [[ "$api_code" == "200" || "$api_code" == "503" ]] && break
  sleep 1
done
web_ok=0
for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:$WEB_PORT" >/dev/null 2>&1 && { web_ok=1; break; }
  sleep 1
done

ok=1
if [[ "$api_code" == "200" ]]; then
  echo "✓ API  http://127.0.0.1:$API_PORT   (Swagger http://127.0.0.1:$API_PORT/swagger-ui.html)"
elif [[ "$api_code" == "503" ]]; then
  echo "✗ API is up but has no usable market data — see logs/api.log"; ok=0
else
  echo "✗ API did not come up — see logs/api.log"; ok=0
fi
if [[ "$web_ok" == "1" ]]; then
  echo "✓ App  http://127.0.0.1:$WEB_PORT"
else
  echo "✗ web did not come up — see logs/web.log"; ok=0
fi
echo "  logs: logs/api.log · logs/web.log · stop: ./start-new.sh --stop"
[[ "$ok" == "1" ]]
