# SOUL v9: MĂRGĂRITAR, mărimea M (randări / concept CGI)

**Toate imaginile din acest folder sunt randări / concept (CGI), nu fotografii.** Oriunde le folosești, etichetează-le „randare / concept (CGI)".

Decizia fondatorului (2026-09-26): forma finală a lui SOUL e **MĂRGĂRITAR** (ALT B din `v5/`, `v5/soul_v5_altB_margaritar.png`), nu HOPA. A ales-o pentru colțurile mai geometrice și „umerii” discreți de la creștet. Restul rămâne ca în v8:
- mărimea M, cu ecran rotund de 2,8″;
- aluminiu 6061 sablat și anodizat, în Argint, Grafit, Albastru noapte, Jar și Șampanie;
- sticlă neagră cu teșitura de 45° și nimic altceva pe față;
- picior plat din polimer în tonul carcasei;
- difuzorul în cusătura laterală (+x);
- încărcarea pe dedesubt, în capsula OU;
- fără buclă.

## Dimensiuni SOUL M (v9)
| | v8 (HOPA) | **v9 (MĂRGĂRITAR)** |
|---|---|---|
| Lățime × înălțime × adâncime | 90,0 × 103,1 × 31,5 mm | **89,9 × 101,1 × 31,5 mm** |
| Sticla neagră | Ø74,3 | **Ø74,3** (0,825 din lățime, ca în v6/v8) |
| Baza plată | – | **54 × 23 mm**, cu piciorul oval de 40 × 19,7 mm |

MĂRGĂRITAR (63 × 72 × 24, sticlă Ø52) e scalat **uniform** cu k = 90 / 63 = 1,4286, ca sticla să aibă tot Ø74,3. Din cauza proporțiilor lui, iese cu 2 mm mai scund decât HOPA M.

Ca la v8, adâncimea e adusă la **31,5 mm** comprimând doar spatele, adică partea din spatele cusăturii, cu factorul 0,735. Fața, sticla, teșitura și rulourile laterale rămân scalate exact cu k. Fără compresie, adâncimea ar fi ~36,7 mm.

## Fișiere
| Fișier | Ce arată |
|---|---|
| `soul_v9_hero.png` (1600×1200) | Argint, 3/4 din stânga, cu OU difuz în spate. Același cadru ca în v8 |
| `soul_v9_family.png` (2000×1125) | Cele 5 culori: Grafit · Jar · Argint · Albastru noapte · Șampanie |
| `soul_v9_side.png` | Din partea difuzorului (+x): fanta din cusătură, teșitura și fața înclinată la 8° |
| `soul_v9_hand.png` | În aceeași mână stilizată ca în v8 |
| `soul_v9_desk.png` | Pe biroul de stejar, lângă telefonul generic (71,5 × 147 mm) și cană |
| `soul_v9_typing.png` | Tastatura SoulOS în engleză pe ecran (aceeași textură ca în v8) |
| `soul_v9_ou_night.png` | Noaptea, în capsula OU, cu ochi chihlimbar |
| `soul_v9_vs_v8.png` | v8 (HOPA) lângă v9 (MĂRGĂRITAR), din față: aceeași cameră, aceeași scară |

## Ce s-a schimbat față de v8
- **Corpul** e MĂRGĂRITAR: tabelele de lățime și adâncime din `v5/src/alt_geo.py`, cu masa plată Ø56 pentru sticlă și fața îndoită la R150 spre bărbie. Peste el am pus prelucrările v6:
  - locașul sticlei cu teșitură de 45°;
  - fanta de 0,6 mm pe cusătura +x;
  - două găuri de microfon pe −x;
  - tăietura plată și placa de bază din polimer.
- **Talpa de zamak** de la ALT B e înlocuită cu baza plată din v6/v8: placa de polimer în tonul carcasei și piciorul oval, cu contactele de încărcare.
- **Capsula OU:** căptușeala nu mai are cupa elipsoidală făcută pentru talpa-balansoar HOPA.
  - SOUL stă drept pe o podea plată.
  - Piciorul intră într-o adâncitură de 1 mm (conturul piciorului + 0,5 mm), care îl centrează pe contacte.
  - Capsula OU propriu-zisă e neschimbată.

## Observații oneste
- „Umerii” de la creștet se văd mai ales pe metal, pentru că reflexiile îi accentuează. E forma aleasă, nu o eroare.
- Baza lui MĂRGĂRITAR e îngustă în adâncime: 23 mm. SOUL stă stabil pe masă, dar rezistența la răsturnare trebuie verificată pe piesa reală la EVT.
- În `ou_night`, SOUL stă drept, nu înclinat la 6° ca HOPA.

## Cum se regenerează
`src/soul_v9.py` încarcă v8 prin `exec` (v8 → v7 → v6 → v5) și înlocuiește doar trei lucruri: corpul (`src/marg_geo.py`), cusătura și căptușeala OU.
```
cd renders/v9/src
python3 marg_geo.py                          # cifrele (compresia spatelui, dimensiunile M)
PREVIEW=1 ./render_v9.sh hero                # previzualizare în /tmp/soul_v9_render
./render_v9.sh                               # hero family side hand desk typing ou_night → ../soul_v9_*.png
./render_v9.sh front                         # vederea din față (pentru comparație)
python3 compose_v9.py vs <v8_front.png> <v9_front.png>   # soul_v9_vs_v8.png
python3 compose_v9.py site                   # imaginile site/media/soul-m-*.jpg
./render_v9.sh alive                         # opțional: bucla de 5 s
```
Randarea se face în Cycles, pe CPU, cu 4 fire și câte o singură randare pe rând, apoi prin `../v5/src/post.py` (OIDN + AgX).
