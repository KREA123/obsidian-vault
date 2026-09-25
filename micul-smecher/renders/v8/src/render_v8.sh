#!/usr/bin/env bash
# SOUL v8 (size M) -- CGI concept renders. Blender 4.x Cycles CPU, 4 threads, ONE render at a time, then the v5
# post.py (OIDN denoise + bloom + AgX) -> ../soul_v8_<shot>.png
# Usage:  ./render_v8.sh [shot ...]        default: hero family side hand desk typing ou_night
#         PREVIEW=1 ./render_v8.sh hero    (half resolution, few samples -> $TMP/<shot>_preview.png)
#         ./render_v8.sh alive             (5 s loop: ../soul_v8_alive.gif + .mp4; each unique eye state rendered once)
#         extra Blender args after --:  ./render_v8.sh desk -- --set dk_d=820 --samples 64
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
V5="$(cd "$SRC/../../v5/src" && pwd)"
V6="$(cd "$SRC/../../v6/src" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v8_render}"
mkdir -p "$TMP"
SHOTS=(); EXTRA=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--" ]; then shift; EXTRA=("$@"); break; fi
  SHOTS+=("$1"); shift
done
[ ${#SHOTS[@]} -eq 0 ] && SHOTS=(hero family side hand desk typing ou_night)
[ -f "$V6/tex/sole_engrave.png" ] || python3 "$V6/tex_v6.py"
[ -f "$SRC/tex/kbd_soulos3.png" ] || python3 "$SRC/tex_v8.py"
[ "${PREVIEW:-0}" = 1 ] && EXTRA+=(--preview)
blend() { blender -b --factory-startup --python "$SRC/soul_v8.py" -- --tmp "$TMP" --threads 4 "$@" 2>&1 \
          | grep -E "RENDERED|Error|Traceback|File \"|v8 depth|v6 body|wrote" | cut -c1-240 || true; }

for s in "${SHOTS[@]}"; do
  echo "== $s  $(date +%T)"
  if [ "$s" = alive ]; then
    [ -f /tmp/soul_v6_cache/alive_eyes/alive_frames.txt ] || python3 "$V6/alive_eyes.py" /tmp/soul_v6_cache/alive_eyes | tail -1
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
      -pix_fmt yuv420p -movflags +faststart "$OUT/soul_v8_alive.mp4"
    ffmpeg -y -loglevel error -framerate 24 -i "$TMP/alive/png/f%04d.png" \
      -vf "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
      -loop 0 "$OUT/soul_v8_alive.gif"
    ls -la "$OUT/soul_v8_alive.mp4" "$OUT/soul_v8_alive.gif"
    continue
  fi
  blend --shot "$s" "${EXTRA[@]}"
  if [ "${PREVIEW:-0}" = 1 ]; then
    python3 "$V5/post.py" "$TMP/${s}_preview" --out "$TMP/${s}_preview.png" | tail -1
  else
    python3 "$V5/post.py" "$TMP/$s" --out "$OUT/soul_v8_$s.png" | tail -1
  fi
done
echo "ALL DONE $(date +%T)"
