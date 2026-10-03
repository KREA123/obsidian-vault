#!/usr/bin/env bash
# SOUL Cloud end to end on this machine, no real keys: docs/07-CONNECT-AI.md §0.1 steps 3-7 against fakes.
# Steps 1-2 use the Python fake device and brain A (SOUL_BUILTIN_AI=1, kept as a tested code path); step 3 runs
# the FIRMWARE's own protocol code (the SoulOS simulator, `pio run -e sim`) against a fresh cloud with the
# default product (SOUL_BUILTIN_AI=0: no AI paid by SOUL): /pair + email code + tap on the simulated glass,
# "Connect my Claude" + own key, connector OAuth, tools -> pushes applied by SoulOS, a text turn, item.add /
# inbox.add. The OAuth client is the MCP SDK with a loopback redirect (Claude Code style), not claude.ai.
# Step 4 is SOUL Bridge through SOUL Cloud (docs/08 §4): the simulator -> /v1/bridge -> the real `soul-bridge`
# (Node) -> a MOCKED Claude Code (no model is called) -> reply + alarm back on the simulated SOUL; then the same on
# the home network (the simulator serves ws://127.0.0.1:<port>/bridge with the firmware's BridgeServer).
#
#   tools/e2e_demo.sh            # from ai/ ; exit code 0 = every step passed
#
# Starts three processes on 127.0.0.1 and stops them on exit:
#   1. tools/fake_llm.py         stands in for api.anthropic.com + api.openai.com (SDK base-URL env vars)
#   2. python -m suflet_ai.app   the real cloud app (device gateway + relay + connector + OAuth), dev mode
#   3. tools/fake_device.py      a fake SOUL (CLI): signs in, shows a code, is paired, asks, listens
# then tools/e2e_connect.py drives the full story: connector OAuth (MCP SDK) + pairing code + device ✓,
# tools -> pushes on the device socket, device turns -> fake Claude / fake OpenAI, allowance metering,
# bad_key / rate_limited / quota / network codes, offline queue + replay.
set -euo pipefail

cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/soul-e2e.XXXXXX")"
chmod 700 "$WORK"
pids=()
cleanup() {
  for p in "${pids[@]:-}"; do if [ -n "$p" ]; then kill "$p" 2>/dev/null || true; fi; done
  wait 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

port() { "$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])'; }
wait_http() {  # url
  for _ in $(seq 1 100); do
    if "$PY" -c "import httpx,sys; sys.exit(0 if httpx.get('$1', timeout=0.5).status_code < 500 else 1)" 2>/dev/null; then
      return 0
    fi
    sleep 0.1
  done
  echo "timeout waiting for $1" >&2; return 1
}

LLM_PORT="$(port)"; APP_PORT="$(port)"
LLM="http://127.0.0.1:$LLM_PORT"; BASE="http://127.0.0.1:$APP_PORT"
DEV_TOKEN="dev-$("$PY" -c 'import secrets; print(secrets.token_hex(8))')"

echo "== fake LLM on $LLM"
"$PY" tools/fake_llm.py --port "$LLM_PORT" &
LLM_PID=$!; pids+=("$LLM_PID")
wait_http "$LLM/__fake/requests"

echo "== SOUL Cloud on $BASE (data in $WORK)"
env SOUL_ENV=dev SOUL_DATA_DIR="$WORK/data" SUFLET_TZ=Europe/Bucharest \
    SOUL_PUBLIC_HOST="127.0.0.1:$APP_PORT" SOUL_PUBLIC_SCHEME=http SOUL_ENROL_POLICY=pending \
    SUFLET_API_TOKEN="$DEV_TOKEN" SOUL_DEV_MAILBOX="$WORK/mailbox.txt" SOUL_ALLOWANCE_TURNS=4 SOUL_BUILTIN_AI=1 \
    SOUL_ANTHROPIC_KEY=sk-ant-fake-service-ok-0123456789 SOUL_OPENAI_KEY=sk-fake-service-ok-0123456789 \
    ANTHROPIC_BASE_URL="$LLM" OPENAI_BASE_URL="$LLM/v1" \
    "$PY" -m suflet_ai.app serve --host 127.0.0.1 --port "$APP_PORT" >"$WORK/app.log" 2>&1 &
pids+=("$!")
wait_http "$BASE/healthz"

echo
echo "== 1/4 tools/fake_device.py (CLI): pair through the dev claim route, ask, receive the push"
"$PY" tools/fake_device.py --base "$BASE" --host "127.0.0.1:$APP_PORT" --key "$WORK/dev1.pem" \
    --claim --api-token "$DEV_TOKEN" --confirm yes \
    --ask "remind me tomorrow at 9 to call the bank" --listen 3 | sed 's/^/   device> /' | tee "$WORK/dev1.out"
grep -q "PUSH #.* reminder.create" "$WORK/dev1.out" || { echo "FAIL fake_device CLI: no reminder push"; exit 1; }
grep -q "SAY \[claude/cloud\]" "$WORK/dev1.out" || { echo "FAIL fake_device CLI: no Claude reply"; exit 1; }
echo "PASS  fake_device.py CLI paired, asked (fake Claude), got and acked the reminder push"

echo
echo "== 2/4 tools/e2e_connect.py: connector OAuth + tools + relay + error codes + offline queue"
"$PY" tools/e2e_connect.py --base "$BASE" --llm "$LLM" --llm-pid "$LLM_PID" \
    --mailbox "$WORK/mailbox.txt" --api-token "$DEV_TOKEN" --allowance 4

echo
SIM="${SOUL_SIM:-../firmware/.pio/build/sim/program}"
if [ -x "$SIM" ]; then
  echo "== 3/4 tools/e2e_sim.py: the firmware simulator as the device (default product: no AI paid by SOUL)"
  LLM2_PORT="$(port)"; APP2_PORT="$(port)"
  LLM2="http://127.0.0.1:$LLM2_PORT"; BASE2="http://127.0.0.1:$APP2_PORT"
  "$PY" tools/fake_llm.py --port "$LLM2_PORT" &
  pids+=("$!")
  wait_http "$LLM2/__fake/requests"
  env SOUL_ENV=dev SOUL_DATA_DIR="$WORK/data2" SUFLET_TZ=Europe/Bucharest \
      SOUL_PUBLIC_HOST="127.0.0.1:$APP2_PORT" SOUL_PUBLIC_SCHEME=http SOUL_ENROL_POLICY=pending \
      SOUL_DEV_MAILBOX="$WORK/mailbox2.txt" ANTHROPIC_BASE_URL="$LLM2" OPENAI_BASE_URL="$LLM2/v1" \
      "$PY" -m suflet_ai.app serve --host 127.0.0.1 --port "$APP2_PORT" >"$WORK/app2.log" 2>&1 &
  pids+=("$!")
  wait_http "$BASE2/healthz"
  "$PY" tools/e2e_sim.py --base "$BASE2" --mailbox "$WORK/mailbox2.txt" --sim "$SIM"
else
  echo "== 3/4 SKIPPED: no simulator at $SIM (cd ../firmware && pio run -e sim)"
fi

echo
if [ -x "$SIM" ] && [ -d ../bridge/node_modules ] && command -v node >/dev/null 2>&1; then
  echo "== 4/4 tools/e2e_bridge.py: SOUL Bridge, simulator -> cloud /v1/bridge -> soul-bridge -> mocked Claude Code"
  APP3_PORT="$(port)"; BASE3="http://127.0.0.1:$APP3_PORT"
  env SOUL_ENV=dev SOUL_DATA_DIR="$WORK/data3" SUFLET_TZ=Europe/Bucharest \
      SOUL_PUBLIC_HOST="127.0.0.1:$APP3_PORT" SOUL_PUBLIC_SCHEME=http SOUL_ENROL_POLICY=pending \
      SOUL_DEV_MAILBOX="$WORK/mailbox3.txt" \
      "$PY" -m suflet_ai.app serve --host 127.0.0.1 --port "$APP3_PORT" >"$WORK/app3.log" 2>&1 &
  pids+=("$!")
  wait_http "$BASE3/healthz"
  "$PY" tools/e2e_bridge.py --base "$BASE3" --mailbox "$WORK/mailbox3.txt" --sim "$SIM" --bridge ../bridge
  if grep -q "sbt_" "$WORK/app3.log"; then echo "FAIL  a bridge token appears in the server log"; exit 1; fi
  echo "   ... and on the home network (no cloud): the simulator serves /bridge, soul-bridge pairs with 6 digits"
  "$PY" tools/e2e_bridge.py --lan --sim "$SIM" --bridge ../bridge
else
  echo "== 4/4 SKIPPED: needs the simulator, node and ../bridge/node_modules (cd ../bridge && npm install)"
fi

if grep -hE "sk-ant-|sk-fake-|sk-proj-|sdt_|sat_|srt_" "$WORK"/app*.log >/dev/null; then
  echo "FAIL  a key or token appears in the server log"; exit 1
fi
echo "PASS  server log holds no key or token"
echo
echo "e2e demo: OK"
