#!/usr/bin/env bash
# Rebuild the Expedo trailer end to end: UI capture → frames → mp4s → soundtrack/VO mux → contact sheet → checks.
#
#   ./build.sh                                                        # UI from the frozen snapshot (default)
#   ./build.sh --app /home/user/obsidian-vault/P/apps/expedo --port 3302   # UI from the current app (English UI)
#   SKIP_CAPTURE=1 ./build.sh                                         # keep ui/ as it is
#   VERSIONS="en:h en:v" ./build.sh ...                               # only some cuts (default: all four)
#
# All arguments go to capture.py (--app, --port, --db, --locale, --loc-order, --track-order).
# Frames go to $FRAMES_DIR (default /tmp/claude-0/expedo_frames) and are deleted at the end.
set -euo pipefail
cd "$(dirname "$0")"
export FRAMES_DIR="${FRAMES_DIR:-/tmp/claude-0/expedo_frames}"
VERSIONS="${VERSIONS:-en:h en:v ro:h ro:v}"

[ -n "${SKIP_CAPTURE:-}" ] || python3 capture.py "$@"
for v in $VERSIONS; do
  rm -rf "$FRAMES_DIR/${v%%:*}${v##*:}"
  WORKERS="${WORKERS:-4}" python3 render.py video "${v%%:*}" "${v##*:}"
done
langs=$(for v in $VERSIONS; do echo "${v%%:*}"; done | sort -u | tr '\n' ' ')
python3 audio.py $langs
python3 render.py contact
for f in expedo_trailer_*.mp4; do
  printf '%s  ' "$f"
  ffmpeg -hide_banner -nostats -i "$f" -af ebur128=peak=true -f null - 2>&1 | grep -E '^\s+(I|True peak|Peak):' | tr -s ' ' | tr '\n' ' '
  echo
done
rm -rf "$FRAMES_DIR"
