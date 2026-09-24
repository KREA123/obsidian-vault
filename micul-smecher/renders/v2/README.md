# Randări produs — SOUL v2 (piatra de buzunar)

> **Atenție: acestea sunt randări pe calculator (CGI), NU fotografii ale unui prototip real.**
> Nu există încă o carcasă fizică v2. Forma, sticla mată, aluminiul, curelușa, mâna și lumina sunt o
> propunere vizuală; produsul real va arăta diferit. Dacă le folosiți public (precomandă, social media),
> marcați-le ca „randare / concept”. Mâna din `soul_hand.png` e un model stilizat (tip manechin), nu o
> persoană reală.

## Imaginile

| Fișier | Dimensiune | Ce arată |
|---|---|---|
| `soul_hero.png` | 1600×1200 | HERO: piatra SOUL alb-„nor”, culcată pe fundal cald off-white, la 3/4, ochii crem (#FFF0C8) pe ecran. Curelușa textilă de mână iese prin urechiușa din aluminiu (cu manșon de aluminiu) și stă în buclă pe masă. Lumină din spate, ca la fotografia de sticlă: marginile se aprind, iar prin corp trece lumină în umbră. |
| `soul_hand.png` | 1600×1200 | ÎN PALMĂ: piatra ținută într-o palmă deschisă (mână stilizată, generată procedural), pentru scară. |
| `soul_scale.png` | 1600×1200 | SCARĂ: amuleta v1 (moneda Ø58 mm, 18,8 mm) lângă piatra v2 (70×64 mm, ~22 mm), văzute de sus, cu cote desenate. |
| `soul_os.png` | 1600×1200 | ECRAN OS: prim-plan cu ecranul pe care rulează interfața — cardul rotund „17:00 · Sună la bancă ✓ gata”, text crem pe negru, inel de progres mentă (4/5 azi). Piatra stă în suportul magnetic din aluminiu. |
| `soul_colors.png` | 1600×1200 | CULORI: cele 5 variante, de la stânga la dreapta — **nor** (alb), **cer** (bleu), **piersică**, **grafit**, **lila**, fiecare cu nuanța ochilor asortată (crem, gheață, piersică, crem, lila). |
| `soul_night.png` | 1600×1200 | NOAPTE: piatra în suportul magnetic pe o noptieră din nuc, ochi chihlimbar somnoroși (modul lampă de veghe), corpul luminat cald din interior, lumina se revarsă pe masă. |
| `soul_social.png` | 1080×1920 | Varianta verticală a hero-ului pentru Instagram/TikTok (spațiu liber sus pentru text). |
| `soul_turntable.mp4` | 540×540, h264, 30 fps, 5 s | Rotire 360° a pietrei din hero (fără curelușă). |

## Ce e modelat (dimensiunile folosite)

- **Corpul**: „piatră de râu” ușor ovală, **70 × 64 mm** (contur superelipsă cu mici neregularități, partea
  de jos puțin mai plină), **~22 mm grosime în centru** (8,6 mm față + 1,35 mm lentila bombată + 11,6 mm
  spate), toate muchiile foarte rotunjite (sfert de elipsă spre ecuator, spate aproape plat ca să stea pe masă).
- **Ecranul**: AMOLED rotund 1,75" (466×466 px), **Ø44 mm vizibil**, sub o lentilă neagră ușor bombată Ø46,4 mm.
- **Sticla mată** (îmbunătățirea față de v1, care arăta a porțelan): transmisie cu rugozitate 0,30, granulație
  fină în relief (textura de sticlă sablată/corodată), un volum care împrăștie lumina înainte (anizotropie 0,8),
  așa că lumina trece prin tot corpul, plus o ușoară nuanță verzuie-rece de sticlă sodo-calcică în zonele groase.
  Iluminarea e din spate, ca în fotografia de produs pentru sticlă: marginile strălucesc, iar în umbră apare
  lumina care a trecut prin piatră (caustice).
- **Buton lateral** subțire din aluminiu periat (13 × 2,6 mm) pe marginea din dreapta.
- **Urechiușă** din sârmă de aluminiu în marginea din stânga + **curelușă textilă** țesută (8 mm lățime,
  1,15 mm grosime, nod „cap de lark” pe urechiușă, manșon de aluminiu, buclă de ~11–14 cm cu o răsucire naturală).
- **Suportul magnetic** (opțional): soclu jos din aluminiu cu inserție neagră soft-touch și un spătar îngust
  în spatele pietrei (acolo ar sta magnetul și pinii de încărcare); piatra se sprijină la ~20° de verticală.
- **Ochii** vin din `../src/eyes.py` (portul 1:1 al funcției `drawEye` din `firmware/.../Face.cpp`, același ca la v1).
  **Interfața OS** e desenată cu PIL în `src/screens.py` la rezoluția reală a panoului (466×466, rotund), cu
  fontul rotunjit **Fredoka** (OFL, în `src/fonts/`; „ă” e compus din „a” + căciulița combinantă).
- **Mâna** e un model SDF (sferă/capsule netezite) poligonizat cu marching cubes în `src/hand_sdf.py`.

## Cum se re-randează

Cerințe (Ubuntu 24.04), aceleași ca la v1: `apt-get install blender ffmpeg` (Blender 4.0) și
`pip install numpy pillow OpenEXR opencolorio oidn==0.2.1 scikit-image` pentru Python-ul din sistem.
Scriptul v2 încarcă scriptul de scenă v1 din `../src/` ca bibliotecă (lumini, camere, fundal, amuleta v1
pentru imaginea de scară, ieșirea EXR), deci folderul `../src/` trebuie să rămână lângă `v2/`.

```bash
cd micul-smecher/renders/v2/src
./render_all.sh                        # toate: hero hand scale os colors night social turntable
./render_all.sh hero night             # doar unele
PREVIEW=1 ./render_all.sh hero         # previzualizare rapidă (jumătate de rezoluție, în /tmp/soul_v2_render)
```

Pași interni pentru o singură imagine:

```bash
python3 screens.py                     # texturile ecranului (ochi + interfața OS) -> src/tex/
python3 hand_sdf.py                    # mesh-ul mâinii -> src/tex/hand.npz
blender -b --factory-startup --python soul_scene.py -- --shot hero --tmp /tmp/soul_v2_render
python3 post.py /tmp/soul_v2_render/hero --out ../soul_hero.png
python3 annotate.py /tmp/soul_v2_render/scale.json ../soul_scale.png   # doar pentru „scale”: cotele
```

- `src/soul_scene.py` — scena Blender procedurală: piatra, materialele, suportul, curelușa, mâna, luminile și
  camerele pentru fiecare cadru (`--shot hero|hand|scale|os|colors|night|social|turntable`, `--preview`,
  `--samples N`, `--set frost_rough=0.3` etc. pentru parametrii de aspect din `TUNE`).
- `src/post.py` — copia neschimbată a celui din v1: denoise Intel Open Image Denoise (culoare + albedo + normală),
  bloom discret pe ochi și transformarea de culoare **AgX** (config-ul OCIO al Blender).
- `src/screens.py`, `src/hand_sdf.py`, `src/annotate.py` — texturile ecranului, mâna, cotele.
- Motor: **Cycles pe CPU**, 160–256 eșantioane/pixel; ~8–15 min pe cadru pe 4 nuclee
  (turntable: 150 de cadre × 32 eșantioane).
- Ecranul negru e ținut negru cu „steaguri” negre văzute doar în reflexii, iar sclipirea fină de pe lentilă vine
  de la o bandă de lumină vizibilă tot doar în reflexii (`lens_card` în script).

## Limitări cunoscute

- Nu e un CAD de producție: fără port USB-C, șuruburi, îmbinări, grosimi de perete sau modul intern real.
- Sticla mată e o aproximare; pe fundal alb, varianta „nor” rămâne destul de albă — diferența față de porțelan
  se vede mai ales la margini, în umbră și la variantele colorate.
- Strălucirea de noapte e un inel emisiv + o lumină punctuală în interior; în realitate depinde de LED-uri/difuzor.
- Mâna e intenționat stilizată (fără unghii, riduri sau detalii de piele).
- Noptiera, cartea, paharul și suportul sunt obiecte generice simple, fără nicio marcă.
