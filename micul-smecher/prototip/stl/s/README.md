# SOUL S-P0: kitul de printat pentru mărimea S (placa Waveshare AMOLED-1.75)

Prototipul **S-P0** e SOUL S (MĂRGĂRITAR la scara de design) construit în jurul plăcii de dezvoltare **Waveshare ESP32-S3-Touch-AMOLED-1.75**, cu sticla ei. Produsul final are 23,0 mm adâncime și PCB propriu. S-P0 are **63,0 × 70,8 × 25,65 mm**: forma necomprimată, singura adâncime la care încap placa (8,7 mm până la cea mai înaltă piesă) și o baterie (`docs/12-SIZE-S.md` §2.3–2.4).

Modelul: `../../cad/soul_p0_s.py` (CadQuery), portat din kitul S vechi (`../../legacy-S/`) pe conturul MĂRGĂRITAR. Cotele plăcii vin din desenul și STEP-ul Waveshare, verificate pe 2026-10-20 (`docs/12` §1.1). Planșa cotată: `blueprints/final/soul_s_2_p0_kit.png`.

## Piesele (varianta plastic)

| # | Fișier | Ce e | Masă (PLA/PETG) | Orientare la print |
|---|---|---|---|---|
| 1 | `soul_s_p0_plastic_front_shell.stl` | carcasa din față: locașul sticlei, buza de 1,2 mm, 4 bosaje M2, jumătate din picior | ~8 g | cum e în STL: cusătura pe masă, fața în sus |
| 2 | `soul_s_p0_plastic_back_shell.stl` | carcasa din spate: tunelul USB-C, canalul cablului în picior, ieșirile știfturilor | ~12 g | cum e în STL: cusătura pe masă |
| 3 | `soul_s_p0_plastic_chassis.stl` | șasiul: leagănul bateriei, rama difuzorului, stâlpul pe standoff-ul 1 | ~1 g | cum e în STL: partea bateriei pe masă, PETG |
| 4 | `soul_s_p0_plastic_pin_pwr.stl`, `..._pin_boot.stl` | știfturile tastelor PWR și BOOT (11,8 / 11,9 mm) | – | în picioare, gulerul pe masă, 100 % umplere |

`assembly/` are toate piesele **la locul lor**, în același sistem de coordonate (carcase, șasiu, știfturi, placa, bateria, difuzorul, mufa USB-C), pentru verificat în slicer sau în CAD. STEP-urile pieselor sunt în `../../step/s/*.step.gz`.

## Ce mai cumperi

| Ce | Câte | Notă |
|---|---|---|
| Waveshare ESP32-S3-Touch-AMOLED-1.75 (Standard) | 1 | are 2 microfoane, codec și difuzorul de 8 Ω din kit |
| LiPo clasa **503030** (5,0 × 30 × 30 mm, ~450 mAh [estimare], PCM, mufă 2 pini MX1.25) | 1 | **verifici polaritatea** față de mufa BAT a plăcii înainte să o conectezi |
| Difuzor **1511** (15 × 11 × 3,5 mm, 8 Ω) | 1 | dacă difuzorul din kit e altul, măsori-l: rama din șasiu e făcută pentru 15 × 11 |
| Inserții la cald **M2** (Ø3,2 × ≤4 mm) | 4 | în bosajele carcasei din față |
| Șuruburi **M2 × 12** (jos) și **M2 × 8** (sus), cap cilindric | 2 + 2 | lungimea maximă calculată: 13,3 și 9,1 mm |
| Spumă EVA 0,3–0,5 mm, bandă VHB, Kapton | puțin | sub baterie și sub difuzor, niciodată lipici pe baterie |
| Cablu USB-C cu mufa dreaptă **subțire** | 1 | tunelul e făcut pentru o mufă de cel mult **12,4 × 7,0 mm** (NEVERIFICAT: măsori-ți cablul) |

**De ce 503030 și nu 503035** (planul de hârtie din `docs/12-SIZE-S.md` §2.3): cu tunelul mufei USB-C sub placă, o celulă de 35 mm nu mai încape în partea de jos, mai îngustă, a lui MĂRGĂRITAR (căutarea de poziții din 2026-10-20). `docs/size-s.json` (`variants.S-P0_dev_board`) e aliniat cu acest kit din 22.10.2026: ~450 mAh, ~16 h [estimare, proporțional cu capacitatea; cu 503035 ar fi fost ~18 h].

## Asamblarea, pe scurt

1. **Placa întâi.** O pornești pe USB-C, fără baterie, și flashezi firmware-ul S: `cd micul-smecher/firmware && pio run -e amoled175 -t upload` (vezi `firmware/README.md`). Cu șublerul verifici ce e marcat NEVERIFICAT în `cad/soul_p0_s.py`: mufa cablului, înălțimea mufelor MX1.25 cu firele în ele, cursa tastelor.
2. **Inserțiile.** Letconul la 220–230 °C (PLA) sau 240–250 °C (PETG). Apeși cele 4 inserții M2 drept în bosajele carcasei din față, până la nivel cu fața bosajului.
3. **Placa în carcasa din față.** Carcasa cu fața în jos, pe o cârpă. Placa intră cu sticla în jos, în locașul rotund, cu **mufa USB-C în jos** (spre picior), **PWR sus-stânga** și **BOOT sus-dreapta**, privit din față. Sticla stă pe buză; trebuie să intre fără forță.
4. **Șasiul.** O bulină EVA de 0,5 mm pe vârful standoff-ului 1 (dreapta-sus privit din față, deci stânga-sus cum ții placa acum, cu spatele spre tine). Așezi șasiul: stâlpul pe bulină, cele două picioare pe bosajele de jos.
5. **Difuzorul și bateria.**
   - Difuzorul 1511 intră în rama de sus a șasiului, pe spumă, cu **membrana spre capacul din spate**. Firul lui merge la mufa SPK (marginea din stânga, sus, privit din față).
   - Bateria intră între cele două șine, pe spumă, cu firele spre mufa BAT (marginea din stânga, jos). E înclinată cu 6° față de placă, așa e făcut leagănul.
   - **Nu o conectezi încă.**
6. **Știfturile.** Știftul PWR și știftul BOOT intră din interior în cele două găuri din partea de sus a carcasei din spate, cu gulerul spre placă.
7. **Închiderea.** Conectezi bateria (după verificarea polarității). Pui carcasa din spate; limba de pe cusătură intră în ea. Strângi **2 × M2 × 12** jos și **2 × M2 × 8** sus, din spate, până simți rezistență. Nu forța: inserția se smulge din plastic.
8. **Cablul.** Mufa USB-C intră de jos, prin tunelul din picior, direct în placă. Cablul iese prin canalul de 5 mm din talpă, așa că SOUL stă drept și când se încarcă.
9. **Test.** Ochii apar drepți și reacționează la atingere; PWR și BOOT merg prin știfturi; bateria se încarcă. **Prima încărcare o supraveghezi**, pe o farfurie ceramică. Regulile pentru LiPo: `../../README.md` §E9.

## Setări de print (FDM, duză 0,4)

| Piesă | Material | Strat | Pereți | Umplere | Suporți |
|---|---|---|---|---|---|
| Carcasa din față | PLA mat / PETG | 0,12 mm | 3 | 15 % gyroid | „tree”, doar pe masă, sub buza sticlei; fața nu are nevoie |
| Carcasa din spate | la fel | 0,12 mm | 3 | 15 % | de obicei nu; dacă slicer-ul cere, „tree” doar pe masă |
| Șasiul | PETG | 0,12 mm | 3 | 30 % | nu |
| Știfturile | PETG | 0,12 mm | 2 | 100 % | nu |

Prima dată printezi **doar șasiul** și îl probezi pe placă, cu bateria și difuzorul reale. Pentru rășină (SLA) și pentru finisajul „ca v6” se aplică regulile kitului M: `../../README.md` §F.

## Ce a verificat CAD-ul (`cad/report_s_plastic.json`)

- **60 de perechi** de piese verificate; nicio suprapunere peste 0,01 mm³ (singura, 0,002 mm³, e mufa USB-C atingând șasiul în model).
- Jocuri minime măsurate pe B-rep: difuzor–carcasa din spate **0,53 mm**, baterie–carcasa din spate **0,43 mm**, mufa SPK–carcasa din spate **0,17 mm** (înălțimea mufei e NEVERIFICATĂ).
- Sticla stă pe buză (0,04 mm), cum trebuie.
- Mărime: **62,96 × 70,8 × 25,65 mm**.

## Fișiere și cum regenerezi

- STL-uri: acest folder + `assembly/`. STEP: `../../step/s/soul_s_p0_plastic_*.step.gz` (carcase, șasiu, știfturi).
- STEP-ul de ansamblu cu placa (`soul_s_p0_plastic_ASSEMBLY_with_board.step`) are ~50 MB și comprimat, peste limita repo-ului: se generează local cu comanda de mai jos.
- Doar varianta din **plastic** e exportată. Aluminiu (`alu`, `alu_band`) se generează cu `python3 cad/soul_p0_s.py alu` (zeci de minute [estimare]).

```bash
cd micul-smecher/prototip/cad
python3 soul_p0_s.py plastic          # construiește, verifică și exportă (lung; scrie și cache/s_plastic)
python3 soul_p0_s.py finish plastic   # doar verificări + export din cache/s_plastic (cache-ul nu e în git)
python3 stl_fix.py ../stl/s/*.stl     # închide plasa STL acolo unde teselarea lasă muchii deschise
python3 step_shrink.py ../step/s/*.step
python3 blueprints_s.py p0            # planșa blueprints/final/soul_s_2_p0_kit
```
