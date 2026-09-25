# SOUL-P0 mărimea S (1,75″), oprită

Aceasta este prima variantă a kitului de prototip, pentru placa Waveshare **ESP32-S3-Touch-AMOLED-1.75**:

- corp **63 × 75 × 29,5 mm**;
- baterie LiPo **503035** (~500 mAh), montată înclinat;
- difuzor 1511;
- 4 × M2.

Fondatorul a oprit-o pe 2026-09-25 și a trecut la mărimea **M** (placa 2.8C, vezi `../README.md`). Fișierele au rămas aici pentru referință.

| Ce | Unde | Stare |
|---|---|---|
| CAD (CadQuery) | `cad/soul_p0.py` + `cad/soul_geom.py` (geometria S, independentă de cea M) | complet |
| Verificarea plastic | `cad/report_plastic.json` | 60 de perechi verificate. Suprapuneri doar de 0,02 mm³, pe muchia dintre carcase. Jocuri: bateria 0,13 față de carcasa din spate, sticla 0,04 (contact cu buza) |
| STL plastic | `stl/plastic/` + `stl/assembly/` | complet |
| STEP plastic | `step/plastic/*.step.gz` | complet |
| Aluminiu | `step/alu/soul_p0_alu_front_shell.step.gz`, `stl/alu/` | **doar carcasa din față**. Restul se regenerează cu `python3 cad/soul_p0.py alu`, în ~50 min |
| Planșe / randări S | `cad/blueprints_p0.py`, `cad/render_p0.py` | scripturile există. Planșele finale sunt făcute doar pentru M |

Firmware-ul pentru S: `pio run -e amoled175 -t upload`.
