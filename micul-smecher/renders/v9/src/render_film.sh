#!/usr/bin/env bash
# One film key frame: ./render_film.sh <shot> <tag> <eyes> [--set k=v ...]  -> ../film/keys/<shot>_<tag>.png
# (Cycles CPU, 4 threads, one render at a time; then the v5 post.py: OIDN + AgX)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
V5="$(cd "$SRC/../../v5/src" && pwd)"
KEYS="$SRC/../film/keys"; mkdir -p "$KEYS"
TMP="${TMP_DIR:-/tmp/soul_v9_film}"; mkdir -p "$TMP"
shot=$1; tag=$2; eyes=$3; shift 3
EXTRA=(); [ "${PREVIEW:-0}" = 1 ] && EXTRA+=(--preview)
FILM_EYES=$eyes blender -b --factory-startup --python "$SRC/film_v9.py" -- --tmp "$TMP" --threads 4 --shot "$shot" \
  --tag "$tag" "${EXTRA[@]}" "$@" 2>&1 | grep -E "Error|Traceback|File \"" | grep -v "Not freed" | cut -c1-200 || true
stem="$shot"; [ "${PREVIEW:-0}" = 1 ] && stem="${shot}_preview"
python3 "$V5/post.py" "$TMP/${stem}_$tag" --out "$KEYS/${shot}_$tag.png" | tail -1
