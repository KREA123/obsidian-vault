#!/usr/bin/env bash
# quick preview: ./prev.sh shot tag [extra blender args]  -> $SP/<shot>_<tag>.png  (half res, few samples)
SP=${SP:-/tmp/soul_v3_preview}
mkdir -p "$SP"
shot=$1; tag=$2; shift 2
cd "$(dirname "$0")"
blender -b --factory-startup --python soul_scene.py -- --shot $shot --preview --tmp $SP/r "$@" 2>&1 | grep -E "RENDERED|Error|Traceback|File \"" | grep -v "Not freed" | cut -c1-300
python3 post.py $SP/r/${shot}_preview --out $SP/${shot}_$tag.png
