#!/usr/bin/env bash
# Render the ALT A / ALT B frames + the decision board (Blender 4.x Cycles, CPU, one at a time) -> ../soul_v5_<shot>.png
# Usage:  ./render_alt.sh [shot ...]     default: altA_piatra altA_nest altB_margaritar altB_scrin choices
#         PREVIEW=1 ./render_alt.sh altA_nest   (half resolution, few samples; PNGs stay in $TMP_DIR)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v5_render}"
mkdir -p "$TMP"
SHOTS=("$@"); [ ${#SHOTS[@]} -eq 0 ] && SHOTS=(altA_piatra altA_nest altB_margaritar altB_scrin choices)
[ -f "$SRC/tex/eyes_soul_front.png" ] || python3 "$SRC/eyes.py"
EXTRA=(); [ "${PREVIEW:-0}" = 1 ] && EXTRA=(--preview)
for s in "${SHOTS[@]}"; do
  echo "== $s  $(date +%T)"
  blender -b --factory-startup --python "$SRC/alt_v5.py" -- --shot "$s" --tmp "$TMP" "${EXTRA[@]}" ${ALT_ARGS:-} \
    | grep -E "RENDERED|Error|Traceback|alt .* mesh|File \"" | cut -c1-240 || true
  stem="$s"; [ "${PREVIEW:-0}" = 1 ] && stem="${s}_preview"
  python3 "$SRC/post.py" "$TMP/$stem" --out "$TMP/$stem.png" | tail -1
  [ "$s" = choices ] && python3 "$SRC/annotate.py" "$TMP/$stem.json" "$TMP/$stem.png"
  [ "${PREVIEW:-0}" = 1 ] || python3 "$SRC/compose_v5.py" "$s" "$TMP/$stem.png" "$OUT"
done
echo "ALL DONE $(date +%T)"
