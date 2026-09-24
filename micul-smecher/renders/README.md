# Randări produs — SUFLET („Micul Șmecher”)

> **Atenție: acestea sunt randări pe calculator (CGI), NU fotografii ale unui prototip real.**
> Nu există încă o carcasă fizică. Materialele (sticlă mată, aluminiu, piele), lumina și
> proporțiile sunt o propunere vizuală; produsul real va arăta diferit. Dacă le folosiți
> public (pagina de precomandă, social media), marcați-le ca „randare / concept”.

## Imaginile

| Fișier | Ce arată |
|---|---|
| `suflet_hero.png` (1600×1200) | HERO: amuleta **MONEDĂ** (Ø52 mm, 18,5 mm grosime), sticlă mată alb-„nor”, la 3/4 pe fundal cald off-white, lumină de studio moale. Ochii crem (#FFF0C8) se uită spre cameră. |
| `suflet_lineup.png` (1600×1200) | Cele 4 siluete una lângă alta: **NOR** (alb, ochi Cream), **MONEDĂ** (lila #DCD2F2, ochi Lilac), **CABOCHON** (bleu #CDE2F6, ochi Ice), **LACRIMĂ** (piersică #F7D8CB, ochi Peach). Nuanța ochilor = nuanțele de raritate din firmware. |
| `suflet_night.png` (1600×1200) | NOAPTE: moneda pe o noptieră din lemn închis, ochi chihlimbar (#FFC96B, modul lampă de veghe), corpul luminat cald din interior și lumina reflectată pe masă. |
| `suflet_bag.png` (1600×1200) | BRELOC: **LACRIMA** turcoaz (#BEE2DF) atârnată cu inel + lănțișor de mânerul unei genți din piele (cusături, capete din alamă). |
| `suflet_desk.png` (1600×1200) | BIROU: moneda bleu pe un suport din nuc, lângă marginea unui laptop, cu ochii privind în sus. |
| `suflet_social.png` (1080×1920) | Varianta verticală a hero-ului pentru Instagram/TikTok (spațiu liber sus pentru text). |
| `suflet_turntable.mp4` (540×540, h264, 30 fps) | Rotire 360° a monedei din hero, 5 s (150 de cadre). |

## Ce e modelat

- **Siluetele** vin direct din conceptul existent: `../cad/gen_shapes.py` (aceleași contururi ca în
  `shapes.scad`). Dimensiuni folosite în randare: monedă 52×52, cabochon 45×57, lacrimă 47×61,
  nor 68×50 mm, toate de 18,5 mm grosime, cu margini rotunjite („piatră de râu”).
  Obs.: brief-ul cerea cabochon/lacrimă ~44 mm lățime și nor ~62×44, dar ecranul (Ø36 vizibil, piatra
  neagră Ø38,7) nu încape vizual în ele, așa că am mărit ușor formele. Placa Waveshare are Ø43,5 mm,
  deci carcasa reală va fi probabil și mai mare (vezi `../cad/micul_smecher.scad`).
- **„Piatra”**: sticlă neagră lucioasă, ușor bombată (lentilă), cu ecranul emisiv dedesubt.
- **Ochii** sunt randați de `src/eyes.py`, un port 1:1 al funcției `drawEye` din
  `firmware/lib/Suflet/src/Face.cpp` (elipse 0,12×0,19 din diametru, centre ±0,19, pleoapa de sus
  înclinată 0,16 rad cu colțurile interioare mai jos, highlight alb, halo).
- **Corpul**: rășină/sticlă mată translucidă (transmisie cu rugozitate mare + ușoară împrăștiere
  în volum), cu modulul de afișaj vizibil difuz prin material și un inel cald de lumină în interior
  lângă ecran.
- **Capacul** din aluminiu periat, belciug + inel spintecat din oțel Ø12 mm.

## Cum se re-randează

Cerințe (Ubuntu 24.04): `apt-get install blender python3-numpy ffmpeg` (Blender 4.0) și
`pip install numpy pillow OpenEXR opencolorio oidn==0.2.1` pentru Python-ul din sistem.

```bash
cd micul-smecher/renders/src
./render_all.sh                       # toate: hero lineup night desk bag social turntable
./render_all.sh hero night            # doar unele
PREVIEW=1 ./render_all.sh hero        # previzualizare rapidă (jumătate de rezoluție, în /tmp/suflet_render)
```

Pași interni pentru o singură imagine:

```bash
python3 eyes.py                                             # texturile ochilor -> src/tex/
blender -b --factory-startup --python suflet_scene.py -- --shot hero --tmp /tmp/suflet_render
python3 post.py /tmp/suflet_render/hero --out ../suflet_hero.png
```

- `src/suflet_scene.py` — scena Blender procedurală (geometrie, materiale, lumini, camere pentru fiecare
  cadru; `--shot hero|lineup|night|desk|bag|social|turntable`, `--preview`, `--samples N`,
  `--set frost_rough=0.5` etc. pentru parametrii de aspect din `TUNE`).
- `src/post.py` — denoise Intel Open Image Denoise (color + albedo + normal), bloom discret pe ochi și
  transformarea de culoare **AgX** (config-ul OCIO al Blender).
- Motor: **Cycles pe CPU**, 160–192 eșantioane/pixel; ~7–10 min pe cadru pe 4 nuclee
  (turntable: 150 cadre × 48 eșantioane, ~1 oră).
- Ca într-un studio foto adevărat, ecranul negru e ținut negru cu „steaguri” negre văzute doar în
  reflexii, iar sclipirea diagonală de pe sticla ecranului vine de la o bandă de lumină vizibilă tot
  doar în reflexii (`protect_screens`, `screen_highlight` în script).
- Blender-ul din Ubuntu nu are OIDN compilat, de aceea denoise-ul se face separat în `post.py`.

## Variante web pentru pagina de lansare

```bash
python3 src/export_web.py              # scrie ../site/media/render-{hero,lineup,night,desk,bag,inside}[-sm].jpg
python3 src/export_web.py --cad-hires  # re-randează și vederea explodată CAD (1.43, fără baterie) la 1500 px
```

Scriptul decupează fiecare imagine pentru locul ei din pagină (lineup 2:1, noapte și birou 16:9, geantă 4:5),
salvează JPEG progresiv sub 400 KB în două lățimi (întreagă și `-sm` pe jumătate, pentru telefon).
Rulează-l după fiecare re-randare; pagina `../site/index.html` nu trebuie modificată.

## Limitări cunoscute

- Nu e un CAD de producție: fără port USB-C, șuruburi, îmbinări sau grosimi de perete reale.
- Dimensiunile din randări (monedă Ø52 × 18,5 mm) sunt mai mici decât carcasa din `../cad/` (moneda 1.43: 57,8 × 57,8 mm, 17,0 mm grosime fără baterie, 18,8 mm cu baterie). Carcasa reală va părea puțin mai mare în jurul ecranului.
- Sticla mată e o aproximare (transmisie rugoasă + volum); pe fundal alb corpul alb poate părea
  mai degrabă „porțelan mat” decât sticlă.
- Strălucirea interioară e un inel emisiv „ideal”; în realitate depinde de LED-uri/difuzor.
- Turcoazul lacrimei (#BEE2DF) iese spre verde-salvie lângă pielea maro; nuanțele pastel sunt discrete.
- Ochii sunt redați cu intensitate mare, deci crem-ul #FFF0C8 apare aproape alb în centru (ca la o
  fotografie reală a unui AMOLED), cu halou cald.
- Laptopul, geanta și noptiera sunt obiecte generice simple, fără nicio marcă.
