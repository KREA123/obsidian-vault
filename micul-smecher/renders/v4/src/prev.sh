#!/usr/bin/env bash
# quick preview: ./prev.sh shot tag [extra args] -> $SP/v4_<shot>_<tag>.png (half res, few samples)
SP=${SP:-/tmp/soul_v4_preview}; mkdir -p "$SP"
shot=$1; tag=$2; shift 2
cd "$(dirname "$0")"
blender -b --factory-startup --python soul_v4.py -- --shot $shot --preview --tmp $SP/r4 "$@" 2>&1 | grep -E "RENDERED|Error:|Traceback|File \"|Error|WARNING" | grep -v "Not freed" | cut -c1-200
python3 post.py $SP/r4/${shot}_preview --out $SP/v4_${shot}_$tag.png | tail -1
