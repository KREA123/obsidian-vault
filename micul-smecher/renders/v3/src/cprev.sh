#!/usr/bin/env bash
# concept preview: ./cprev.sh shot tag [extra args] -> $SP/c_<shot>_<tag>.png
SP=${SP:-/tmp/soul_v3_preview}; mkdir -p "$SP"
shot=$1; tag=$2; shift 2
cd "$(dirname "$0")"
blender -b --factory-startup --python ${SCRIPT:-concepts.py} -- --shot $shot --preview --tmp $SP/r "$@" 2>&1 | grep -E "RENDERED|Error:|Traceback|File \"|Error" | grep -v "Not freed" | cut -c1-250
python3 post.py $SP/r/${shot}_preview --out $SP/c_${shot}_$tag.png | tail -1
