#!/usr/bin/env bash
# Re-render the SOUL v5 frames (Blender 4.x Cycles, CPU, one at a time) + OIDN/AgX (post.py) -> ../soul_v5_<shot>.png
# Usage:  ./render_all.sh [shot ...]      default: every required frame (1-10b) + the optional F (ou_day)
#         PREVIEW=1 ./render_all.sh hero  (half resolution, few samples; PNGs go to $TMP_DIR)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v5_render}"
mkdir -p "$TMP"
SHOTS=("$@"); [ ${#SHOTS[@]} -eq 0 ] && SHOTS=(hero front_00 front_15 check1_pearl_0 check1_ember_0 check1_pearl_9 \
  check1_ember_9 side back bottom ou_night ou_closed hand family cocon unbox boxback ou_day)
[ -f "$SRC/tex/eyes_soul_front.png" ] || python3 "$SRC/eyes.py"
[ -f "$SRC/tex/sole_engrave.png" ] || python3 "$SRC/textures_v5.py"
EXTRA=(); [ "${PREVIEW:-0}" = 1 ] && EXTRA=(--preview)
for s in "${SHOTS[@]}"; do
  echo "== $s  $(date +%T)"
  blender -b --factory-startup --python "$SRC/soul_v5.py" -- --shot "$s" --tmp "$TMP" "${EXTRA[@]}" \
    | grep -E "RENDERED|Error|Traceback" | cut -c1-200 || true
  stem="$s"; [ "${PREVIEW:-0}" = 1 ] && stem="${s}_preview"
  dest="$OUT"; [ "${PREVIEW:-0}" = 1 ] && dest="$TMP"
  python3 "$SRC/post.py" "$TMP/$stem" --out "$TMP/$stem.png"
  python3 "$SRC/compose_v5.py" "$s" "$TMP/$stem.png" "$dest"
done
echo "ALL DONE $(date +%T)"
