#!/usr/bin/env bash
# ./film2_render.sh <shot> [blender args]  -> ../film/v2/<shot>/f####.png (every 2nd frame, OIDN + AgX)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TMP="${TMP_DIR:-/tmp/soul_v9_film2}"; mkdir -p "$TMP"
shot=$1; shift
blender -b --factory-startup --python "$SRC/film2_v9.py" -- --tmp "$TMP" --threads 4 --shot "$shot" "$@" 2>&1 \
  | grep -E "Error|Traceback|File \"|RENDERED" | grep -v "Not freed" | cut -c1-200 || true
OUT="${OUT_DIR:-$SRC/../film/v2}/$shot"; mkdir -p "$OUT"
python3 - "$TMP" "$shot" "$OUT" <<'PY'
import glob, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('.')), '..', 'v5', 'src'))
sys.path.insert(0, '/home/user/obsidian-vault/micul-smecher/renders/v5/src')
import post
tmp, shot, out = sys.argv[1:]
base = os.path.join(tmp, shot)
for pre in ('', '_preview'):
    if os.path.exists(base + pre + '.json'):
        base = base + pre
        break
meta = json.load(open(base + '.json'))
fr = sorted({int(m.group(1)) for p in glob.glob(base + '_color_*.exr') for m in [re.search(r'_(\d{4})\.exr$', p)] if m})
for f in fr:
    o = os.path.join(out, 'f%04d.png' % f)
    if not os.path.exists(o):
        post.process(base, f, o, meta.get('exposure', 0.0), meta.get('bloom', 0.04), meta.get('look', 'AgX - Medium High Contrast'), True)
print('post', len(fr), 'frames ->', out)
PY
