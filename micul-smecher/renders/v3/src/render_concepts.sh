#!/usr/bin/env bash
# Render the SOUL concept round -> ../concepts/concept_<shot>.png
# Usage: ./render_concepts.sh [shot ...]   (default: all)   PREVIEW=1 for half-res quick passes into $TMP_DIR
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$SRC/.." && pwd)/concepts"
TMP="${TMP_DIR:-/tmp/soul_concepts_render}"
mkdir -p "$TMP" "$OUT"
SHOTS=("$@"); [ ${#SHOTS[@]} -eq 0 ] && SHOTS=(A_lens B_orb C_eve D_soul D_back D_dock A_desk B_desk C_desk lineup)
[ -f "$SRC/tex/eyes_cream_look.png" ] || python3 "$SRC/eyes.py"
[ -f "$SRC/tex/caseback_engrave.png" ] || python3 "$SRC/engrave.py"
EXTRA=(); [ "${PREVIEW:-0}" = 1 ] && EXTRA=(--preview)
for s in "${SHOTS[@]}"; do
  echo "== $s  $(date +%T)"
  blender -b --factory-startup --python "$SRC/concepts.py" -- --shot "$s" --tmp "$TMP" "${EXTRA[@]}" | grep -E "RENDERED|Error:|Traceback" | cut -c1-160 || true
  stem="$s"; [ "${PREVIEW:-0}" = 1 ] && stem="${s}_preview"
  dest="$OUT"; [ "${PREVIEW:-0}" = 1 ] && dest="$TMP"
  python3 "$SRC/post.py" "$TMP/$stem" --out "$dest/concept_$stem.png"
  [ "$s" = lineup ] && python3 "$SRC/annotate.py" "$TMP/$stem.json" "$dest/concept_$stem.png"
done
echo "ALL DONE $(date +%T)"
