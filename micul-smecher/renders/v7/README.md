# SOUL v7: studiu de mărime (randări / concept CGI)

**Toate imaginile din acest folder sunt randări / concept (CGI), nu fotografii.** Oriunde le folosești, etichetează-le „randare / concept (CGI)".

Fondatorul a spus: „e prea mic, cum scrii pe el? mai mare". v7 pune același SOUL v6 (aluminiu, argint natural) în jurul a trei ecrane rotunde reale, ca să poată compara mărimile din mână. Cercetarea (panouri, prețuri, driver, taste, baterie) e în `../../research/12-ecran-mai-mare.md`.

| | Ecran | Ø activ | Corp (l × h × a) | Taste tastatură |
|---|---|---|---|---|
| **S** (azi) | 1,75″ AMOLED 466×466 (Waveshare AMOLED-1.75, CO5300 QSPI) | 43,8 mm | **63 × 72 × 27 mm** | 4,1 mm |
| **M** | 2,8″ IPS 480×480 (Waveshare ESP32-S3-Touch-LCD-2.8C, ST7701 RGB) | 71,1 mm | **≈ 93 × 106 × 31 mm** | 6,7 mm |
| **L** | 3,4″ IPS 800×800 (Waveshare ESP32-P4 3.4C, JD9365 MIPI-DSI) | 86,4 mm | **≈ 113 × 129 × 34 mm** | 8,2 mm |

## Fișiere
| Fișier | Ce arată |
|---|---|
| `soul_v7_hands.png` (2400×1150) | S, M și L, fiecare culcat cu fața în sus în aceeași palmă deschisă, cu aceeași cameră și aceeași lumină. Dedesubt: ecranul, dimensiunile și mărimea tastelor. |
| `soul_v7_lineup.png` (2000×1000) | S / M / L în picioare, unul lângă altul, cu un telefon generic (71,5 × 147 × 7,8 mm, fără marcă) și o cană (Ø82 × 95 mm) pentru scară. Etichete discrete. |
| `soul_v7_typing.png` (1600×1200) | M ținut ca un telefon: baza în podul palmei, spatele sprijinit pe degete. Pe ecran e tastatura SoulOS la scară (captura `os/screenshots/soulos-keyboard-hello-1440.png`), iar degetul mare e deasupra tastelor. |

## Ce e diferit față de v6
- **Scalare:** lățimea și înălțimea se scalează cu k (M 1,47, L 1,79). Adâncimea crește mai puțin (M 31 mm, L 34 mm), pentru că un corp mai mare nu trebuie să fie proporțional mai gros: bateria crește în plan.
- **Inel negru mai subțire** la M și L: 1,8 mm la scara locală, față de 4,1 mm la v6, pentru că panourile IPS goale au bordură de ~1,5 mm (panoul 2,8″: contur 73 mm, zonă activă 70,1 mm). Sticla păstrează proporțiile v6 (Ø52 pe 63).
- **IPS nu are negru adevărat.** M și L au în randare un glow foarte slab în cercul activ. Prin sticla neagră, discul se vede puțin mai gri decât inelul. La S (AMOLED), negrul e negru.
- **Mâna** e mâna stilizată din v4/v5, re-pozată în `src/hand_sdf_v7.py`: palmă mai deschisă și fără „cupa" pentru piatră, ca să încapă toate trei mărimile. Pentru `typing`, degetele sunt mai strânse, iar degetul mare e poziționat prin IK pe tasta „n" și ocolește corpul.
- Ecranul unui SOUL culcat își păstrează „susul" spre coroană. Nu se mai folosește `level_eyes`.

## Observații oneste (din imagini)
- **M** acoperă toată palma, iar **L** iese peste marginile ei. Niciunul nu mai e obiect de buzunar. L e un obiect de birou.
- În `typing`, degetul mare ajunge la tastele lui M doar cu mâna întinsă. Pe M se tastează confortabil cu două mâini sau cu SOUL pe masă, nu cu o mână ca pe telefon.
- Dimensiunea M e calculată pe Ø71,1 (2,8″ nominal). Panoul gol real are 70,1 mm activ, deci corpul real ar fi cu ~1 mm mai mic.

## Cum se regenerează
Pipeline-ul v6 (`../v6/src/soul_v6.py` → v5) se încarcă prin `exec`, fără cod duplicat. `src/soul_v7.py` adaugă doar scalarea, ecranul, recuzita și cadrele.
```
cd renders/v7/src
PREVIEW=1 ./render_v7.sh lineup        # previzualizare (jumătate de rezoluție) în /tmp/soul_v7_render
./render_v7.sh                          # hands_S hands_M hands_L lineup typing, apoi compose_v7.py → ../soul_v7_*.png
```
Detalii tehnice:
- Cycles CPU, 4 fire, o singură randare pe rând. Apoi `../v5/src/post.py` (OIDN + AgX) și `compose_v7.py` (triptic, etichete Nunito).
- Plasa corpului vine din cache-ul v6 (`/tmp/soul_v6_cache`).
- Mâinile se generează o dată în `src/tex/{open,hold,type}/hand.npz`. `type` se regenerează la fiecare randare, cu ținta calculată din poziția ecranului.
- Parametri reglabili cu `-- --set cheie=valoare` (de ex. `h_lens`, `lu_d`, `t_tilt`, `ips_glow`).
