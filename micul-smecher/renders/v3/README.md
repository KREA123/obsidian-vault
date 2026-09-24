# Randări concept — SOUL v3 „amuleta”

> **Atenție: acestea sunt randări pe calculator (CGI), NU fotografii ale unui prototip real.**
> Nu există încă o carcasă fizică v3. Materialele (sticlă mată, titan, oțel gravat), lumina, gravura și
> proporțiile sunt o propunere vizuală; produsul real va arăta diferit. Dacă le folosiți public
> (precomandă, social media), marcați-le ca „randare / concept”.

v3 întoarce produsul la ce a iubit fondatorul la v1 (pandantiv-monedă purtat vertical, belciug + inel,
sticlă neagră bombată mare, corp de sticlă mată, lumină caldă de studio) și evită ce s-a pierdut la v2
(pietricică ovală culcată, cu ecran mic). Dimensiunile urmează recomandarea din
`../../research/07-amulet-design-language-2026-09-24.md`.

## Imaginile

| Fișier | Dimensiune | Ce arată |
|---|---|---|
| `soul_hero.png` | 1600×1200 | HERO: amuleta atârnată vertical pe un șnur subțire, la 3/4, studio cald off-white, halo-ul „soul light” strălucește slab crem, ochii Cream (#FFF0C8) privesc spre cameră. |
| `soul_necklace.png` | 1600×1200 | PURTAT: pe un șnur cerat, pe un bust de croitorie îmbrăcat în in (fără cap/față), așezată pe stern, „aproape de inimă”; ochii privesc în jos, halo crem discret. |
| `soul_caseback.png` | 1600×1200 | SPATE, macro, profunzime de câmp mică: capacul din oțel (Ø40) cu banda lustruită oglindă și gravura „SOUL · No. 0001 · born 24.09.2026”, centrul periat concentric, cele două contacte de încărcare aurite, fanta pentru monedă a capacului baionetă (OPEN ↺ / ↻ CLOSE gravate lângă ea). |
| `soul_night.png` | 1600×1200 | NOAPTE: pe noptieră din nuc, ochi chihlimbar somnoroși, halo cald chihlimbar, lumina lui reflectată pe masă (ca la v1). |
| `soul_listening.png` | 1600×1200 | ASCULTĂ: fundal gri închis editorial, amuleta atârnă pe un șnur închis, halo albastru moale, ochii privesc în sus. |
| `soul_lineup.png` | 1600×1200 | CULORI: 8 variante pe socluri mici de piatră, în două rânduri. Spate: **Bone** (alb, ochi Cream), **Ice** #CDE2F6 (ochi Ice), **Mint** #BEE2DF (ochi Mint), **Peach** #F7D8CB (ochi Peach). Față: **Lilac** #DCD2F2 (ochi Lilac), **Gold edition** (corp șampanie + coroană și inel aurii, ochi Gold), **Onyx** (corp negru fumuriu, ochi Cream), **Mărțișor** (alb-os, cu șnur răsucit roșu-alb). Nuanțele ochilor = nuanțele „de naștere” din firmware (`Personality.cpp`, `kTints`). |
| `soul_scale.png` | 1600×1200 | SCARĂ: v3 (Ø56) lângă v1 (Ø52) și o cheie generică de casă (~57 mm), văzute aproape de sus; etichete subțiri adăugate în post: „SOUL v1 Ø52” / „SOUL Ø56”. |
| `soul_martisor.png` | 1600×1200 | EDIȚIA MĂRȚIȘOR: corp alb-os atârnat pe șnurul de mătase răsucit roșu-alb. |
| `soul_social.png` | 1080×1920 | Varianta verticală a hero-ului pentru Instagram/TikTok, cu spațiu liber sus pentru text. |
| `soul_turntable.mp4` | 540×540, h264, 30 fps | Rotire 360° a amuletei din hero, 4 s (120 de cadre, eșantioane puține + denoise). |

## Ce e modelat (v3)

- **Corp**: monedă rotundă **Ø56 mm**, **16,5 mm** grosime la centru, ~11,5 mm la margine, margine
  rotunjită „piatră de râu” (secțiune super-elipsă), spate ușor bombat. (Brief-ul inițial spunea Ø58 × 17;
  am folosit dimensiunile de producție din research/07.)
- **Fața = produsul**: o singură fereastră-„ochi” din sticlă neagră bombată **Ø47** (ecran activ **Ø44**,
  panoul AMOLED 466×466), fără grilă sau logo pe față.
- **Halo „soul light”**: inel din sticlă/PC mat translucid, ~4 mm lat, ușor mai înalt decât sticla,
  separat de corp printr-o linie fină; în interior un inel de LED-uri (sursă emisivă ascunsă) care îl face să
  strălucească în culoarea stării: crem (implicit), chihlimbar (noapte), albastru (ascultă). Un inel subțire
  lustruit desparte sticla de halo.
- **Coroana** la ora 12: coroană de ceas de buzunar (canelată, cu guler) topită într-un belciug sculptat
  (mai gros la bază, subțire sus), din titan; inel spintecat din oțel (auriu la ediția Gold).
  Sub coroană, pe muchia de sus, două fante mici pentru difuzor (fără grilă pe față).
- **Capacul din spate**: disc din oțel Ø40, tip **baionetă** (se deschide cu o monedă, fără șuruburi vizibile):
  bandă exterioară lustruită oglindă cu gravura fină, centru periat concentric, două contacte aurii,
  fantă pentru monedă la ora 6.
- **Ochii**: `src/eyes.py`, portul 1:1 al funcției `drawEye` din firmware (`Face.cpp`), cu variante noi
  (privire în jos, în sus/ascultă, somnoros chihlimbar).
- **Culori corp**: Bone/Cream, Ice #CDE2F6, Mint #BEE2DF, Peach #F7D8CB, Lilac #DCD2F2, Gold (șampanie +
  aur), Onyx (negru fumuriu), Mărțișor (alb-os + șnur roșu-alb).

## Cum se re-randează

Aceleași unelte ca la v1 (deja instalate: Blender 4.0 din Ubuntu, `ffmpeg`, Python cu `numpy pillow
OpenEXR opencolorio oidn==0.2.1`). Blender-ul din Ubuntu nu are OIDN, de aceea denoise-ul se face în `post.py`.

```bash
cd micul-smecher/renders/v3/src
./render_all.sh                          # toate: hero necklace caseback night listening lineup scale martisor social turntable
./render_all.sh hero night               # doar unele
PREVIEW=1 ./render_all.sh hero           # previzualizare (jumătate de rezoluție, puține eșantioane; în /tmp/soul_v3_render)
./prev.sh hero test --samples 24         # previzualizare rapidă în $SP (implicit /tmp/soul_v3_preview)
```

Pași interni pentru o singură imagine:

```bash
python3 eyes.py                          # texturile ochilor -> src/tex/eyes_*.png
python3 engrave.py                       # masca gravurii capacului -> src/tex/caseback_engrave.png
blender -b --factory-startup --python soul_scene.py -- --shot hero --tmp /tmp/soul_v3_render
python3 post.py /tmp/soul_v3_render/hero --out ../soul_hero.png
python3 annotate.py /tmp/soul_v3_render/scale.json ../soul_scale.png   # doar pentru scale (etichetele)
```

- `src/soul_scene.py` — scena Blender procedurală, pornită din scena v1 (`../../src/suflet_scene.py`):
  aceleași helper-e, materiale, lumini de studio și „steaguri” negre pentru ecran; `build_soul()` construiește
  amuleta v3, `build_amulet()` (codul v1) mai e folosit doar pentru moneda v1 din `scale`.
  Opțiuni: `--shot`, `--preview`, `--samples N`, `--w/--h`, `--set cheie=valoare` pentru parametrii din `TUNE`
  (ex. `--set halo_inner=0.5` intensitatea halo-ului, `--set body_dens=20` cât de „lăptos” e corpul,
  `--set exposure=-0.2`).
- `src/post.py` — denoise Intel Open Image Denoise (culoare + albedo + normale), bloom discret și transformarea
  de culoare **AgX** (config-ul OCIO al Blender) — identic cu v1.
- `src/annotate.py` — liniile de cotă și etichetele subțiri (DejaVu Sans ExtraLight) pentru `soul_scale.png`.
- Motor: **Cycles pe CPU** (4 nuclee), 96–160 eșantioane/pixel + OIDN; ~6–12 min pe cadru 1600×1200;
  turntable 120 cadre × 24 eșantioane.

## Limitări cunoscute

- Nu e un CAD de producție: fără garnituri, grosimi reale de perete, antenă, baterie sau mecanismul real
  al capacului baionetă (e sugerat doar prin fanta pentru monedă și gravura OPEN/CLOSE).
- Halo-ul e o sursă emisivă „ideală” în interiorul unui inel mat; în realitate lumina depinde de LED-uri,
  ghidul de lumină și difuzor.
- Pe fundal alb, corpul alb mat poate părea mai degrabă „porțelan satinat” decât sticlă; translucența se
  vede mai bine în cadrele întunecate (noapte, ascultă).
- Bustul de croitorie, noptiera, soclurile și cheia sunt obiecte generice simple, fără nicio marcă.
