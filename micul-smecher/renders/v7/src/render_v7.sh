#!/usr/bin/env bash
# SOUL v7 (size study) -- CGI concept renders. Blender 4.x Cycles CPU, 4 threads, ONE render at a time, then the v5
# post.py (OIDN + bloom + AgX) and compose_v7.py (triptych / labels) -> ../soul_v7_<name>.png
# Usage:  ./render_v7.sh [shot ...]        default: hands_S hands_M hands_L lineup typing  (then compose)
#         PREVIEW=1 ./render_v7.sh lineup  (half resolution, few samples -> $TMP/<shot>_preview.png)
#         extra Blender args after --:  ./render_v7.sh lineup -- --set lu_d=950 --samples 64
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
V5="$(cd "$SRC/../../v5/src" && pwd)"
V6="$(cd "$SRC/../../v6/src" && pwd)"
OUT="$(cd "$SRC/.." && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v7_render}"
mkdir -p "$TMP"
SHOTS=(); EXTRA=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--" ]; then shift; EXTRA=("$@"); break; fi
  SHOTS+=("$1"); shift
done
[ ${#SHOTS[@]} -eq 0 ] && SHOTS=(hands_S hands_M hands_L lineup typing)
[ -f "$V6/tex/sole_engrave.png" ] || python3 "$V6/tex_v6.py"
[ "${PREVIEW:-0}" = 1 ] && EXTRA+=(--preview)
for s in "${SHOTS[@]}"; do
  echo "== $s  $(date +%T)"
  blender -b --factory-startup --python "$SRC/soul_v7.py" -- --tmp "$TMP" --threads 4 --shot "$s" "${EXTRA[@]}" 2>&1 \
    | grep -E "RENDERED|Error|Traceback|File \"|size |rest gap" | cut -c1-240 || true
  stem="$s"; [ "${PREVIEW:-0}" = 1 ] && stem="${s}_preview"
  python3 "$V5/post.py" "$TMP/$stem" --out "$TMP/$stem.png" | tail -1
done
[ "${PREVIEW:-0}" = 1 ] || python3 "$SRC/compose_v7.py" "$TMP" "$OUT"
echo "ALL DONE $(date +%T)"
