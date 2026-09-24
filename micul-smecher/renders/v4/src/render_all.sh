#!/usr/bin/env bash
# Re-render the SOUL v4 family images (Blender 4.x Cycles, CPU) + denoise/tone-map (post.py) -> ../soul_v4_<shot>.png
# Usage:  ./render_all.sh [shot ...]   default: family pebble cloud drop amulet hand scale capsule
#         PREVIEW=1 ./render_all.sh pebble   (half resolution, few samples; PNG goes to $TMP_DIR)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v4_render}"
mkdir -p "$TMP"
SHOTS=("$@"); [ ${#SHOTS[@]} -eq 0 ] && SHOTS=(family pebble cloud drop amulet hand scale capsule)
[ -f "$SRC/tex/eyes_cream_look.png" ] || python3 "$SRC/eyes.py"
EXTRA=(); [ "${PREVIEW:-0}" = 1 ] && EXTRA=(--preview)
for s in "${SHOTS[@]}"; do
  echo "== $s  $(date +%T)"
  blender -b --factory-startup --python "$SRC/soul_v4.py" -- --shot "$s" --tmp "$TMP" "${EXTRA[@]}" | grep -E "RENDERED|Error:|Traceback" | cut -c1-160 || true
  stem="$s"; [ "${PREVIEW:-0}" = 1 ] && stem="${s}_preview"
  dest="$OUT"; [ "${PREVIEW:-0}" = 1 ] && dest="$TMP"
  python3 "$SRC/post.py" "$TMP/$stem" --out "$dest/soul_v4_$stem.png"
  [ "$s" = scale ] && python3 "$SRC/annotate.py" "$TMP/$stem.json" "$dest/soul_v4_$stem.png"
done
echo "ALL DONE $(date +%T)"
