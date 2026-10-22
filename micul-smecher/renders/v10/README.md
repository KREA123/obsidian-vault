# SOUL v10: mărimea S, produsul final (randări / concept CGI)

**Toate imaginile din acest folder sunt randări / concept (CGI), nu fotografii.** Oriunde le folosești, etichetează-le „randare / concept (CGI)".

Decizia fondatorului (2026-10-20, `03 Decizii/Jurnal decizii.md`): **produsul final e mărimea S**. Prototipul de lucru rămâne **M** (placa 2.8C, firmware 1.9.0), pentru teste și dovada TRL 3. v10 e v9 (MĂRGĂRITAR) la **scara lui de design**, fără mărirea × 1,43 a lui M. Restul e neschimbat:
- aluminiu 6061 sablat și anodizat, în Argint, Grafit, Albastru noapte, Jar și Șampanie;
- sticlă neagră plată **Ø52**, cu teșitura de 45°, și nimic altceva pe față;
- ecran rotund **1,75″ AMOLED 466×466**: negru adevărat, ochii stau pe negru;
- picior oval din polimer în tonul carcasei, contactele de încărcare dedesubt (capsula OU);
- fanta difuzorului în cusătura +x, două găuri de microfon pe −x.

## Dimensiuni SOUL S (v10)
Cifrele vin din `docs/size-s.json` (sursa unică) și sunt cele ale modelului randat (`renders/v9/src/marg_geo.py`, geometria „local”).

| | **S (v10, produsul final)** | M (v9, prototipul) |
|---|---|---|
| Lățime × înălțime × adâncime | **62,96 × 70,8 × 23,0 mm** (înălțimea cu piciorul de 1,2 mm) | 89,9 × 101,1 × 31,5 mm |
| Sticla neagră | **Ø52** (0,825 din lățime) | Ø74,3 |
| Ecran | 1,75″ AMOLED 466×466, zona activă Ø43,76 | 2,8″ IPS 480×480 |
| Compresia spatelui (s_back) | **0,807** | 0,735 |
| Baza plată / piciorul | 37,8 × 17,0 mm / 28 × 13,8 mm | 54 × 23 / 40 × 19,7 mm |
| Baterie [estimare] | 750 mAh (LiPo 603040) | 1500 mAh |

Ca la v9, adâncimea se obține comprimând **doar spatele** (partea din spatele cusăturii). Fața, sticla, teșitura și rulourile laterale sunt exact cele de design. Fără compresie, adâncimea ar fi 25,65 mm. 23,0 mm e ținta aleasă în `docs/12-SIZE-S.md` §2.4: încape bateria de 750 mAh cu 0,93 mm rezervă. Față de M împărțit la 1,43 (22,05 mm), spatele e cu ~1 mm mai plin.

## Fișiere
| Fișier | Ce arată |
|---|---|
| `soul_v10_hero.png` (1600×1200) | Argint, 3/4 din stânga, cu OU difuz în spate. Cadrul hero din v6/v9 |
| `soul_v10_family.png` (2000×1125) | Cele 5 culori: Grafit · Jar · Argint · Albastru noapte · Șampanie |
| `soul_v10_side.png` | Din partea difuzorului (+x): fanta din cusătură, teșitura, fața înclinată la 8°, spatele de 23 mm |
| `soul_v10_hand.png` | În aceeași mână de adult ca în v8/v9, la mărimea reală. Camera e la aceeași distanță reală ca la M (× 0,8), deci S se vede cât e: încape în palmă, degetele rămân libere |
| `soul_v10_desk.png` | Pe biroul de stejar, lângă telefonul generic (71,5 × 147 mm), camera mai aproape ca la v9 (560 mm) |
| `soul_v10_ou_night.png` | Noaptea, în capsula OU, cu ochi chihlimbar |
| `soul_v10_vs_m.png` (2000×1295) | **S lângă M** pe birou, aceeași cameră, aceeași scară (ambele MĂRGĂRITAR, Argint), cu dimensiunile dedesubt |

Planșele cotate ale lui S sunt în `blueprints/final/soul_s_1_general_arrangement*.svg/png`. Șablonul de printat la scară reală: `prototip/SOUL-marimi-scara-reala.pdf`.

## Observații oneste
- În `hero`, `family`, `side` și `ou_night` camera, luminile și studioul sunt cele din v6/v9 la scara de design, deci imaginile arată ca în v9. Singura diferență vizibilă de mărime e profunzimea de câmp: fundalul e mai difuz, pentru că diafragma nu se scalează. Mărimea se vede în `hand`, `desk` și `vs_m`.
- Ochii ocupă tot cercul Ø43,76 al ecranului (raportul v6 21,88 / 26). Pe AMOLED-ul real zona activă e exact Ø43,76.
- La S, sticla de 0,7 mm și panoul AMOLED de ~0,95 mm sunt din stiva de produs (`docs/12` §2.2), nu de pe placa Waveshare. Prototipul S-P0 de pe placa de dezvoltare are sticla ei, Ø48,96, și adâncimea de 25,65 mm (`prototip/stl/s/`).
- În `vs_m`, M e corpul v9 (s_back 0,735) mărit cu 90/63. Ambele sunt construite din același cod, deci comparația e exactă.
- Fără `typing` în v10: tastatura SoulOS pe 1,75″ e încă de proiectat (to-do „SoulOS pe 1,75″”).

## Cum se regenerează
`src/soul_v10.py` încarcă v9 prin `exec` (v9 → v8 → v7 → v6 → v5, nimic duplicat). Înainte, înlocuiește corpul din `marg_geo` cu `MargaritarV9(adâncime 23,0)` și apoi pune `K = 1`. Aici sunt și cadrele noi `vs_m` și `hand` (camera la distanța reală din v9), plus încadrarea `desk`.
```
cd renders/v10/src
PREVIEW=1 ./render_v10.sh hero          # previzualizare în /tmp/soul_v10_render
./render_v10.sh                          # hero family side hand desk ou_night vs_m → ../soul_v10_*.png
python3 compose_v10.py vs                # etichetele de sub soul_v10_vs_m.png
```
Randarea se face în Cycles, pe CPU, cu 4 fire, câte una pe rând, apoi prin `../v5/src/post.py` (OIDN + AgX). Cache-ul mâinii stă în `/tmp/soul_v10_tex` (nu se publică).
