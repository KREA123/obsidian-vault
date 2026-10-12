#!/usr/bin/env bash
# Rebuild the PoC 1.1 drafts (DOCX + PDF) from data.py. Usage: bash build.sh [workdir]
# Needs: python3 + python-docx + lxml, LibreOffice (soffice) for the PDFs.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DRAFT="$(dirname "$HERE")"
APEL="$(cd "$DRAFT/../../apel/28ce899f-Apel_1.1_Proof_of_Concept" && pwd)"
WORK="${1:-$(mktemp -d)}"
mkdir -p "$WORK/out"
cp "$HERE"/*.py "$WORK/"
cp "$APEL/Anexa 3_Plan_Afaceri_PoC 1.1_03.06.2026.docx" "$WORK/a3.docx"
cp "$APEL/Anexa_16_Model_Raport_Stiintific__PoC 1.1_03.06.2026.docx" "$WORK/a16.docx"
cd "$WORK"
python3 build_a3.py out/Anexa_3_Plan_Afaceri_SOUL_DRAFT.docx
python3 build_a16.py out/Anexa_16_Raport_Stiintific_SOUL_DRAFT.docx
python3 build_models.py out
cd out
soffice --headless --convert-to pdf *.docx >/dev/null
cp *.docx "$DRAFT/"
cp Anexa_3_Plan_Afaceri_SOUL_DRAFT.pdf "$DRAFT/out_a3.pdf"
cp Anexa_16_Raport_Stiintific_SOUL_DRAFT.pdf "$DRAFT/out_a16.pdf"
cp Scrisoare_de_intentie_MODEL.pdf Declaratie_cesiune_drepturi_MODEL.pdf "$DRAFT/"
echo "built in $WORK, copied to $DRAFT"
