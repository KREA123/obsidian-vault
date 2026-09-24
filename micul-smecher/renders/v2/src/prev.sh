#!/usr/bin/env bash
# quick preview: ./prev.sh shot tag [extra blender args]  -> $SP/<shot>_<tag>.png
SP=/tmp/claude-0/-home-user-obsidian-vault/ed786c2e-2b4e-5bb0-b0e8-a62c849e07d8/scratchpad
shot=$1; tag=$2; shift 2
cd "$(dirname "$0")"
blender -b --factory-startup --python soul_scene.py -- --shot $shot --preview --tmp $SP/r "$@" 2>&1 | grep -E "RENDERED|Error:|Traceback|File \"|Error" | grep -v "Not freed" | cut -c1-300
python3 post.py $SP/r/${shot}_preview --out $SP/${shot}_$tag.png
