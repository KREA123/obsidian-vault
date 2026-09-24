# SOUL · planșe tehnice (blueprint), rev A · 2026-09-24

Patru planșe A3 (proiecție în unghiul al treilea, mm), generate din cod: `src/gen_sheets.py` (geometrie + SVG) și `src/render.py` (PNG 2400 px prin Chromium-ul Playwright din `/opt/pw-browsers`).

| planșă | fișiere | ce conține |
|---|---|---|
| 1/4 GA producție (2:1) | `soul_blueprint_ga.svg/.png` + `soul_ga_white.svg/.png` (varianta albă, de printat) | vedere față, sus, lateral dreapta, spate; cote, axe, sticla și zona activă, buton, microfoane, grila difuzorului, buzunarul barei de curea, pad-uri de încărcare, șuruburi |
| 2/4 Secțiunea A-A (4:1) | `soul_blueprint_section.svg/.png` | stratificarea pe axă (sticlă, AMOLED, PCB, celulă, spumă, balast, perete spate), difuzor + LRA în lobul de jos, detaliul B (buza 8:1), tabel cu cote z |
| 3/4 Explodat + BOM | `soul_blueprint_exploded.svg/.png` | vedere axonometrică explodată cu 17 poziții, listă de piese cu materiale și mase estimate (≈73 g), ordinea de asamblare |
| 4/4 Prototip Waveshare 1.75 (2:1) | `soul_blueprint_proto.svg/.png` | varianta de dezvoltare 72 × 64 × 24 cu placa rotită 180° (USB-C sus, sub bara de curea), standoff-uri, header, taste, microfoane, secțiunea B-B, tabel cu datele plăcii |

Regenerare: `cd src && python3 gen_sheets.py ga sec exp pro && python3 render.py ../*.svg`

## Ce e verificat și ce e estimat

**Verificat (V), din modelul STEP Waveshare, via CAD-ul proiectului:** sticlă Ø48.96 × 1.10, față plană Ø44.16, zonă activă Ø43.76, modul + PCB Ø46.0, PCB la 5.70 / 6.90, header 12.70 (cel mai adânc, la margine), 8.90 sub celulă, standoff-uri M2 (3) la 10.43, USB-C r 23.80 / 8.55, taste PWR/BOOT 7.60.

**Din research (06-product-design-v2), cote-țintă:** oval 68 × 60, ecran cu 3–4 mm peste centru (desenat la +4.0), 19 mm la centru, ~12 la margine, spate dom R≈60–80 (desenat R80), sticla la nivel cu o buză mată de 0.3–0.5 (desenat 0.4), 1 buton sus-dreapta (ține apăsat = vorbește), pad-uri pogo pe spate pentru dock, USB-C doar la unitățile dev, sub bară, celulă 523450 de 1000 mAh (K), difuzor sigilat 1813 + LRA în lobul de jos, prototip ~72 × 64 × 24.

**Estimat (E), de verificat:** toate grosimile de perete (1.5 / 1.2 / 2.0), planul de separare z −7.0, grosimile stratului AMOLED/PCB/componente la producție, pozițiile microfoanelor, grilei, șuruburilor și pad-urilor, placa de balast (formată pe dom, ~17 g, adusă ca masa să ajungă aproape de ținta de 75–90 g), difuzorul 1813 și LRA Ø10, spatele R250 și split-ul la prototip, extinderea headerului. Direcția porturilor de microfon de pe placă și difuzorul din kit (20 × 30 × 5.5) sunt **neverificate**.

Observații din desen: la 19 mm și dom R80 celula 523450 încape doar așezată **transversal** (50 mm pe lățime), cu ~0.4 mm rezervă la colțuri. Difuzorul și LRA-ul se suprapun parțial, ca înălțime, cu marginea de jos a ecranului, așa că PCB-ul de producție trebuie să fie teșit jos (D-cut).

## Pașii următori

1. **Șubler:** celula 523450 reală (cu PCM), difuzorul din kit, mufa cablului USB-C, portul microfoanelor, inserțiile M2. Apoi actualizezi cotele (E) din `src/gen_sheets.py`.
2. **CAD:** transferi conturul (arc R30 concentric cu ecranul + superelipsă n 2.6) și profilul (dom R80, R4/R3) în modelul parametric. Verifici coliziunile 3D la colțurile celulei și în lobul de jos.
3. Printezi o probă de potrivire a prototipului (72 × 64 × 24) și cântărești (țintă 95–105 g). Ridici curentul de încărcare AXP2101 la ~500 mA.
4. Rev B după măsurători. Pentru producție: DFM cu furnizorul de carcasă (unghiuri de extracție, grosimi minime PC, buza 2K).
