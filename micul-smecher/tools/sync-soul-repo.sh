#!/usr/bin/env bash
# Mirror SOUL (micul-smecher/ + the SOUL notes from the vault) into the separate repo krea123/soul.
# The vault stays the source of truth; run this after each push:  bash micul-smecher/tools/sync-soul-repo.sh
set -euo pipefail
VAULT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${SOUL_REPO_DIR:-$VAULT/../soul}"
REMOTE="${SOUL_REMOTE:-https://github.com/krea123/soul.git}"
[ -d "$WORK/.git" ] || git clone "$REMOTE" "$WORK" || { mkdir -p "$WORK"; git -C "$WORK" init -b main; git -C "$WORK" remote add origin "$REMOTE"; }
rsync -a --delete --exclude .git --exclude notes/ \
  --exclude 'prototip/cad/cache/' --exclude 'prototip/step/**/*.step' --exclude 'firmware/.pio/' \
  --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude 'dist/' \
  "$VAULT/micul-smecher/" "$WORK/"
mkdir -p "$WORK/notes"
rsync -a --delete "$VAULT/01 Afaceri/Micul Șmecher/" "$WORK/notes/"
# only the SOUL decisions from the vault's decision log (the rest is private business)
{ echo "# Jurnal decizii — SOUL (extras din vault)"; echo; grep -E "SOUL|Micul|Șmecher|SoulOS|MĂRGĂRITAR|HOPA|PoC" "$VAULT/03 Decizii/Jurnal decizii.md" | grep -v -i "mundishop" || true; } > "$WORK/notes/Jurnal decizii SOUL.md"
cd "$WORK"
git add -A
git diff --cached --quiet && { echo "soul repo: nothing to sync"; exit 0; }
git commit -qm "Sync from vault $(git -C "$VAULT" rev-parse --short HEAD)"
git push -u origin HEAD:main
