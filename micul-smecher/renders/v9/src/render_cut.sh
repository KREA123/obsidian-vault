#!/usr/bin/env bash
# SOUL v9 trailer cut-outs: one Blender render at a time (nice'd), then post_cut.py -> trailer/assets/*.webp
# usage: ./render_cut.sh [shot ...]   (default: all cut_* shots)   PREVIEW=1 for half-res tests
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$SRC/../../../trailer" && pwd)/assets"
TMP="${TMP_DIR:-/tmp/soul_cut}"
mkdir -p "$TMP" "$OUT"
SHOTS=("$@")
[ ${#SHOTS[@]} -eq 0 ] && SHOTS=(cut_front cut_l cut_r cut_ou cut_c_silver cut_c_graphite cut_c_midnight cut_c_ember cut_c_champagne)
EXTRA=(); [ "${PREVIEW:-0}" = 1 ] && EXTRA+=(--preview)
for s in "${SHOTS[@]}"; do
  echo "== $s $(date +%T)"
  nice -n 10 blender -b --factory-startup --python "$SRC/soul_v9.py" -- --shot "$s" --tmp "$TMP" --threads 4 "${EXTRA[@]}" 2>&1 \
    | grep -E "RENDERED|Error:|Traceback|v9 cut" | grep -v "Not freed" | cut -c1-200 || true
  stem="$s"; [ "${PREVIEW:-0}" = 1 ] && stem="${s}_preview"
  name="${s#cut_}"; name="soul_${name#c_}"
  [ "$s" = cut_ou ] && name="soul_ou"
  [[ "$s" == cut_c_* ]] && name="soul_col_${s#cut_c_}"
  python3 "$SRC/post_cut.py" "$TMP/$stem" --out "$OUT/$name.webp" ${POST_ARGS:-}
  rm -f "$TMP/${stem}"_*_????.exr
done
echo "ALL DONE $(date +%T)"
