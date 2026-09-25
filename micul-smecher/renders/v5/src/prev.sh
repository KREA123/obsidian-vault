#!/usr/bin/env bash
# quick preview: ./prev.sh shot tag [extra args] -> $SP/v5_<shot>_<tag>.png (half res, few samples)
SP=${SP:-/tmp/soul_v5_preview}; mkdir -p "$SP"
shot=$1; tag=$2; shift 2
cd "$(dirname "$0")"
blender -b --factory-startup --python soul_v5.py -- --shot $shot --preview --tmp $SP/r5 "$@" 2>&1 | grep -E "RENDERED|Error|Traceback|File \"|WARNING|  [a-z].*[0-9]s" | grep -v "Not freed" | cut -c1-240
python3 post.py $SP/r5/${shot}_preview --out $SP/v5_${shot}_$tag.png | tail -1
