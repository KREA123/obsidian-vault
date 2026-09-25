#!/usr/bin/env bash
# SOUL v6 (aluminium, flat base) -- CGI concept renders. Blender 4.x Cycles CPU, ONE render at a time, then the v5
# post.py (OIDN denoise + bloom + AgX) -> ../soul_v6_<shot>.png
# Usage:  ./render_v6.sh [shot ...]              default: hero family side back bottom ou_night hand macro
#         PREVIEW=1 ./render_v6.sh hero          (half resolution, few samples -> $TMP_DIR/<shot>_preview.png)
#         ./render_v6.sh alive                   (5 s clip: ../soul_v6_alive.mp4 + .gif)
#         extra Blender args after --:  ./render_v6.sh hero -- --set kick=2.0 --samples 64
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
V5="$(cd "$SRC/../../v5/src" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v6_render}"
mkdir -p "$TMP"
SHOTS=(); EXTRA=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--" ]; then shift; EXTRA=("$@"); break; fi
  SHOTS+=("$1"); shift
done
[ ${#SHOTS[@]} -eq 0 ] && SHOTS=(hero family side back bottom ou_night hand macro)
[ -f "$SRC/tex/sole_engrave.png" ] || python3 "$SRC/tex_v6.py"
[ "${PREVIEW:-0}" = 1 ] && EXTRA+=(--preview)
blend() { blender -b --factory-startup --python "$SRC/soul_v6.py" -- --tmp "$TMP" "$@" 2>&1 \
          | grep -E "RENDERED|Error|Traceback|File \"|v6 body" | cut -c1-220 || true; }

for s in "${SHOTS[@]}"; do
  echo "== $s  $(date +%T)"
  if [ "$s" = alive ]; then
    python3 "$SRC/alive_eyes.py" /tmp/soul_v6_cache/alive_eyes | tail -1
    # only the eye texture changes: render each unique eye state once (static camera, fixed seed -> no flicker)
    mapfile -t ROWS < /tmp/soul_v6_cache/alive_eyes/alive_frames.txt
    declare -A FIRST=()
    for r in "${ROWS[@]}"; do f=${r%% *}; h=${r##* }; [ -n "${FIRST[$h]:-}" ] || FIRST[$h]=$f; done
    mkdir -p "$TMP/alive/png"
    for h in "${!FIRST[@]}"; do
      f=${FIRST[$h]}
      [ -f "$TMP/alive/png/u_$h.png" ] && continue
      blend --shot alive --tag "f$f" --set alive_frame=$f "${EXTRA[@]}"
      stem="alive"; [ "${PREVIEW:-0}" = 1 ] && stem="alive_preview"
      python3 "$V5/post.py" "$TMP/${stem}_f$f" --out "$TMP/alive/png/u_$h.png" | tail -1
    done
    for r in "${ROWS[@]}"; do f=${r%% *}; h=${r##* }; cp "$TMP/alive/png/u_$h.png" "$(printf "$TMP/alive/png/f%04d.png" "$f")"; done
    ffmpeg -y -loglevel error -framerate 24 -i "$TMP/alive/png/f%04d.png" -c:v libx264 -preset slow -crf 18 \
      -pix_fmt yuv420p -movflags +faststart "$OUT/soul_v6_alive.mp4"
    ffmpeg -y -loglevel error -framerate 24 -i "$TMP/alive/png/f%04d.png" \
      -vf "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
      -loop 0 "$OUT/soul_v6_alive.gif"
    ls -la "$OUT/soul_v6_alive.mp4" "$OUT/soul_v6_alive.gif"
    continue
  fi
  blend --shot "$s" "${EXTRA[@]}"
  if [ "${PREVIEW:-0}" = 1 ]; then
    python3 "$V5/post.py" "$TMP/${s}_preview" --out "$TMP/${s}_preview.png" | tail -1
  else
    python3 "$V5/post.py" "$TMP/$s" --out "$OUT/soul_v6_$s.png" | tail -1
  fi
done
echo "ALL DONE $(date +%T)"
