#!/usr/bin/env bash
# SOUL Cloud end to end on this machine, no real keys (docs/07-CONNECT-AI.md §0.1 steps 3-7).
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
  for p in "${pids[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null || true; done
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
    SUFLET_API_TOKEN="$DEV_TOKEN" SOUL_DEV_MAILBOX="$WORK/mailbox.txt" SOUL_ALLOWANCE_TURNS=4 \
    SOUL_ANTHROPIC_KEY=sk-ant-fake-service-ok-0123456789 SOUL_OPENAI_KEY=sk-fake-service-ok-0123456789 \
    ANTHROPIC_BASE_URL="$LLM" OPENAI_BASE_URL="$LLM/v1" \
    "$PY" -m suflet_ai.app serve --host 127.0.0.1 --port "$APP_PORT" >"$WORK/app.log" 2>&1 &
pids+=("$!")
wait_http "$BASE/healthz"

echo
echo "== 1/2 tools/fake_device.py (CLI): pair through the dev claim route, ask, receive the push"
"$PY" tools/fake_device.py --base "$BASE" --host "127.0.0.1:$APP_PORT" --key "$WORK/dev1.pem" \
    --claim --api-token "$DEV_TOKEN" --confirm yes \
    --ask "remind me tomorrow at 9 to call the bank" --listen 3 | sed 's/^/   device> /' | tee "$WORK/dev1.out"
grep -q "PUSH #.* reminder.create" "$WORK/dev1.out" || { echo "FAIL fake_device CLI: no reminder push"; exit 1; }
grep -q "SAY \[claude/cloud\]" "$WORK/dev1.out" || { echo "FAIL fake_device CLI: no Claude reply"; exit 1; }
echo "PASS  fake_device.py CLI paired, asked (fake Claude), got and acked the reminder push"

echo
echo "== 2/2 tools/e2e_connect.py: connector OAuth + tools + relay + error codes + offline queue"
"$PY" tools/e2e_connect.py --base "$BASE" --llm "$LLM" --llm-pid "$LLM_PID" \
    --mailbox "$WORK/mailbox.txt" --api-token "$DEV_TOKEN" --allowance 4

if grep -E "sk-ant-|sk-fake-|sdt_|sat_|srt_" "$WORK/app.log" >/dev/null; then
  echo "FAIL  a key or token appears in the server log"; exit 1
fi
echo "PASS  server log holds no key or token"
echo
echo "e2e demo: OK"
