#!/usr/bin/env bash
# Re-render all SUFLET product images (Blender 4.x Cycles, CPU) + denoise/tone-map (post.py).
# Usage:  ./render_all.sh [shot ...]        default: hero lineup night desk bag social turntable
#         PREVIEW=1 ./render_all.sh hero    (half resolution, few samples; PNG goes to $TMP_DIR, not to renders/)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/suflet_render}"
mkdir -p "$TMP"
SHOTS=("$@"); [ ${#SHOTS[@]} -eq 0 ] && SHOTS=(hero lineup night desk bag social turntable)
[ -f "$SRC/tex/eyes_cream.png" ] || python3 "$SRC/eyes.py"
EXTRA=(); [ "${PREVIEW:-0}" = 1 ] && EXTRA=(--preview)
for s in "${SHOTS[@]}"; do
  echo "== $s"
  blender -b --factory-startup --python "$SRC/suflet_scene.py" -- --shot "$s" --tmp "$TMP" "${EXTRA[@]}" | grep -E "RENDERED|Error" || true
  stem="$s"; [ "${PREVIEW:-0}" = 1 ] && stem="${s}_preview"
  if [ "$s" = turntable ]; then
    python3 "$SRC/post.py" "$TMP/$stem" --outdir "$TMP/turntable_png"
    ffmpeg -y -loglevel error -framerate 30 -i "$TMP/turntable_png/f%04d.png" -c:v libx264 -pix_fmt yuv420p \
      -crf 18 -movflags +faststart "$OUT/suflet_turntable.mp4"
    echo "wrote $OUT/suflet_turntable.mp4"
  else
    dest="$OUT"; [ "${PREVIEW:-0}" = 1 ] && dest="$TMP"
    python3 "$SRC/post.py" "$TMP/$stem" --out "$dest/suflet_$stem.png"
  fi
done
