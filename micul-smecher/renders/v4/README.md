# Randări concept — familia SOUL v4

> **Atenție: acestea sunt randări pe calculator (CGI), NU fotografii ale unui prototip real.**
> Nu există încă nicio carcasă fizică v4. Materialele, lumina și proporțiile sunt o propunere vizuală;
> produsul real va arăta diferit. Dacă le folosiți public, marcați-le ca „randare / concept”.

## Direcția

Fondatorul a vrut înapoi **caracterul siluetelor din v1** (NOR, MONEDĂ, PIETRICICĂ, LACRIMĂ; vezi
`../suflet_lineup.png`) și pietricica ovală desenată în prototipul SoulOS (`../../os/screenshots/`). Le-a vrut
**mai mari** și **fără belciug sau inel** (prinderea vine din accesorii separate, ca la AirTag), cu aspect
premium, dar ieftine de fabricat.

Regulile formei v4:
- **Pe față există doar corpul și sticla neagră.** Fără grilă, puncte, logo sau detalii. Sticla bombată are Ø49,
  iar bordura e tipărită în negrul real al panoului, așa că toată sticla pare ecran. Dedesubt e ecranul AMOLED de 1,75"
  (Ø44 activ), cu ochii crem vii din firmware. În jurul sticlei e un singur inel lustruit, subțire cât un fir de păr.
- **Difuzorul** e pe muchia laterală dreaptă (o micro-perforație din 7 găuri de Ø0,6 mm), iar **încărcarea** se face
  pe baza plată de jos (două contacte pogo aurii). Nu există port USB vizibil.
- **Stă vertical** pe o bază plată mică. Grosimea e ~18 mm, cu margini moi, rotunjite („piatră de râu”).
- **Corp** din PC injectat lucios, cu luciu perlat (mai deschis și mai rece la unghiuri razante). Culori:
  alb-perlă, salvie, nisip, piersică, lila.

| Formă | Dimensiuni | Note |
|---|---|---|
| **PEBBLE** | 64 × 72 × 18 mm | ou vertical, mai lat sus; ecranul e în partea de sus (ca în prototipul SoulOS) |
| **CLOUD** | 84 × 66 × 18 mm | conturul norului din v1, mărit; fața e centrată |
| **DROP** | 64 × 80 × 18 mm | lacrimă cu vârful în sus; vârful e doar formă, fără belciug |
| **AMULET** | Ø64 × 18 mm | moneda v1 hero, mai mare și fără belciug |

## Imaginile (toate 1600×1200)

| Fișier | Ce arată |
|---|---|
| `soul_v4_family.png` | Toate patru în picioare, mari în cadru, în studio cald off-white ca la v1: CLOUD salvie, PEBBLE alb-perlă, DROP piersică, AMULET lila; ochi crem sau în nuanța corpului. |
| `soul_v4_pebble.png` | PEBBLE alb-perlă, hero la 3/4. |
| `soul_v4_cloud.png` | CLOUD salvie, hero la 3/4. |
| `soul_v4_drop.png` | DROP piersică, hero la 3/4. |
| `soul_v4_amulet.png` | AMULET nisip, hero la 3/4. |
| `soul_v4_hand.png` | PEBBLE ținut în palmă (mână stilizată, ca un manechin), cât o piatră de palmă. |
| `soul_v4_scale.png` | Familia culcată cu fața în sus, lângă moneda v1 (Ø52) și un card bancar generic (85,6 × 54), cu etichete subțiri adăugate în post. |
| `soul_v4_capsule.png` | PEBBLE stând într-un leagăn-dock sculptat, lucios, care îl încarcă prin contactele de jos. |

## Cum se re-randează

Aceleași unelte ca la v1 (deja instalate): Blender 4.0 din Ubuntu, `ffmpeg` și Python cu `numpy pillow
OpenEXR opencolorio oidn==0.2.1`. Blender-ul din Ubuntu nu are OIDN, așa că denoise-ul se face în `post.py`.

```bash
cd micul-smecher/renders/v4/src
./render_all.sh                    # toate: family pebble cloud drop amulet hand scale capsule -> ../soul_v4_*.png
./render_all.sh pebble hand        # doar unele
PREVIEW=1 ./render_all.sh family   # previzualizare la jumătate de rezoluție, în /tmp/soul_v4_render
./prev.sh cloud test --samples 16  # previzualizare rapidă în $SP (implicit /tmp/soul_v4_preview)
```

- `src/soul_v4.py` conține scena v4: contururile, corpul (loft ca `build_body` din v1, cu locaș pentru sticlă și
  margine în sfert de elipsă), materialul perlat, sticla, difuzorul, contactele și cadrele. Încarcă
  `src/concepts.py`, care la rândul lui încarcă `src/soul_scene.py`, adică scena v1 evoluată. De acolo vin
  materialele, luminile de studio, „steagurile” negre care țin ecranul negru și pipeline-ul EXR. Contururile
  NOR / LACRIMĂ vin din `../../../cad/gen_shapes.py` (aceleași ca la v1), scalate la dimensiunile de mai sus.
  Moneda v1 din `scale` e construită tot cu codul v1 (`build_amulet`).
- `src/eyes.py` generează texturile ochilor (portul lui `Face.cpp`), `src/hand_sdf.py` construiește mâna
  (din v2, plasă în `tex/hand.npz`), iar `src/annotate.py` pune etichetele (DejaVu Sans ExtraLight).
- `src/post.py` face denoise-ul Intel Open Image Denoise, un bloom discret și transformarea de culoare AgX, ca la v1.
- Motor: **Cycles pe CPU** (4 nuclee), 96–128 de eșantioane/pixel plus OIDN, cam 6–9 min pe cadru.

## Limitări cunoscute

- Nu e CAD de producție: nu există grosimi de perete, îmbinarea față/spate, baterie, antenă sau mecanismul de
  apăsare. Pentru PEBBLE, CLOUD și DROP, spațiul de sub sticla de Ø49 e strâns la margini.
- Luciul perlat e o aproximare (culoare dependentă de unghi, strat lucios și puțină împrăștiere). O vopsea
  perlată reală are și irizații.
- Mâna e stilizată, nu fotorealistă. Cardul și docul sunt obiecte generice, fără nicio marcă.
