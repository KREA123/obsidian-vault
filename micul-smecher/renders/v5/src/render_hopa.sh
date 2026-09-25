#!/usr/bin/env bash
# HOPA animation (CGI concept): soul_v5.py --shot hopa -> ../soul_v5_hopa.mp4 (720x720, 24 fps, 7 s, h264),
# ../soul_v5_hopa.gif (480 px, 15 fps, <= 6 MB) and three 1600x1600 stills. Cycles CPU, one Blender at a time.
# Usage:  ./render_hopa.sh [anim|stills|all]      (default all)
#         PREVIEW=1 ./render_hopa.sh anim           (the first 2 s at 360 px, 16 spp -> $TMP/prev2s.mp4)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v5_hopa}"
what="${1:-all}"
mkdir -p "$TMP"
blend() { blender -b --factory-startup --python "$SRC/soul_v5.py" -- --shot hopa "$@" | grep -E "RENDERED|Error|Traceback" | cut -c1-160 || true; }

if [ "$what" = anim ] || [ "$what" = all ]; then
  if [ "${PREVIEW:-0}" = 1 ]; then
    blend --tmp "$TMP/prev" --frames 1:48 --preview --samples 16
    python3 "$SRC/post.py" "$TMP/prev/hopa_preview" --outdir "$TMP/prev/png" | tail -1
    ffmpeg -y -loglevel error -framerate 24 -i "$TMP/prev/png/f%04d.png" -c:v libx264 -pix_fmt yuv420p "$TMP/prev2s.mp4"
    echo "preview: $TMP/prev2s.mp4"; exit 0
  fi
  blend --tmp "$TMP/anim" --samples 32                       # 168 frames, ~27 s each on 4 cores
  python3 "$SRC/post.py" "$TMP/anim/hopa" --outdir "$TMP/anim/png" | tail -1
  ffmpeg -y -loglevel error -framerate 24 -i "$TMP/anim/png/f%04d.png" -c:v libx264 -preset slow -crf 18 \
    -pix_fmt yuv420p -movflags +faststart "$OUT/soul_v5_hopa.mp4"
  ffmpeg -y -loglevel error -framerate 24 -i "$TMP/anim/png/f%04d.png" \
    -vf "fps=15,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
    -loop 0 "$OUT/soul_v5_hopa.gif"
  ls -la "$OUT/soul_v5_hopa.mp4" "$OUT/soul_v5_hopa.gif"
fi
if [ "$what" = stills ] || [ "$what" = all ]; then
  # 18 = the tip (~20 deg, eyes level), 72 = the dizzy flutter, 112 = the half-lidded side-glance
  for fn in 18:tip 72:dizzy 112:glance; do
    f=${fn%%:*}; name=${fn##*:}
    blend --tmp "$TMP/still_$name" --frames $f:$f --w 1600 --h 1600 --samples 128
    python3 "$SRC/post.py" "$TMP/still_$name/hopa" --out "$OUT/soul_v5_hopa_$name.png" | tail -1
  done
fi
echo "HOPA DONE $(date +%T)"
