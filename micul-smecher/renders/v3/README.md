# Randări concept — SOUL v3

> **Atenție: acestea sunt randări pe calculator (CGI), NU fotografii ale unui prototip real.**
> Nu există încă o carcasă fizică pentru niciun concept de aici. Materialele (titan sablat, sticlă optică,
> zirconia, porțelan), lumina, gravura și proporțiile sunt o propunere vizuală. Produsul real va arăta diferit.
> Dacă le folosiți public, marcați-le ca „randare / concept”.

## Direcția (24.09.2026)

Fondatorul: SOUL **nu e pentru gât**. Forma rotundă din v1 era bună, dar o voia **mai mare**; v2 (mai mare)
arăta ca plastic ieftin. Acum ținta e un obiect **premium, futurist, „tech cu suflet”**, de purtat în buzunar
sau în geantă, sau de ținut pe birou. Nu e o bijuterie. De aceea runda de concepte de mai jos înlocuiește
seria „amuletă”. Din aceea a rămas doar `v3_amulet_ref.png`, ca referință.

Toate conceptele păstrează **aceeași față**: sticlă neagră bombată (Ø49; la D Ø53 „infinity glass”), ecranul
AMOLED activ Ø44 și ochii crem vii (`src/eyes.py`, portul lui `Face.cpp`). Toate sunt mai mari decât v1 (Ø52).
Specificațiile vin din `../../research/08-wow-design-cmf-2026-09-24.md`.

## Conceptele randate (`concepts/`, 1600×1200)

Runda de concepte a fost oprită de feedback-ul fondatorului: cercurile simple i s-au părut „un cerc mic și urât”.
Direcția finală e **familia v4** (`../v4/`). Au rămas randate doar:

| Fișier | Ce arată |
|---|---|
| `concept_A_lens.png` | **A · LENS**: corp Ø60 × 16 mm din titan natur sablat (ca un obiectiv Leica sau un Apple Watch Ultra). Are o ramă rotativă moletată cu teșitura lustruită și o linie de lumină foarte subțire (halo) între sticlă și metal. Sus e o urechiușă mică detașabilă. Pe flanc e gravat laser un „SOUL” micro. Studio grafit. |
| `concept_B_orb.png` | **B · ORB**: corp Ø62 × 23 mm din sticlă optică transparentă. Ochiul negru plutește în sticlă, iar prin flanc se văd plăcile interioare și un inel de lumină. Are o spină subțire din oțel lustruit. |

Scripturile pentru C (EVE), D (hibridul din research/08, cu dock din porțelan) și E (pietricica-lentilă Ø64 cu
accesorii) sunt în `src/concepts.py` și `src/concept_e.py`. Au fost doar previzualizate și nu au imagini finale.

Referință: `v3_amulet_ref.png` (1600×1200) e amuleta v3 atârnată pe un șnur (Ø56, halo mat, coroană cu
belciug). A fost în afara brief-ului final și a rămas doar ca referință de formă și lumină.

## Cum se re-randează

Aceleași unelte ca la v1 (deja instalate): Blender 4.0 din Ubuntu, `ffmpeg` și Python cu `numpy pillow
OpenEXR opencolorio oidn==0.2.1`. Blender-ul din Ubuntu nu are OIDN, așa că denoise-ul se face în `post.py`.

```bash
cd micul-smecher/renders/v3/src
./render_concepts.sh                     # toate conceptele -> ../concepts/concept_*.png
./render_concepts.sh A_lens B_orb       # doar unele (A_lens A_desk B_orb B_desk C_eve C_desk D_soul D_dock D_back lineup)
PREVIEW=1 ./render_concepts.sh A_lens    # previzualizare la jumătate de rezoluție, în /tmp/soul_concepts_render
./cprev.sh B_orb test --samples 24       # previzualizare rapidă în $SP (implicit /tmp/soul_v3_preview)
```

- `src/concepts.py` conține cele patru corpuri și cadrele. Refolosește **toate** helper-ele din `src/soul_scene.py`
  (scena v1 evoluată: materiale, lumini, „steaguri” negre care țin ecranul negru, pipeline-ul EXR).
  - `build_lens()` (A, iar cu alți parametri și D): profil rotit cu teșituri, moletare pe ramă (180 de dinți),
    materiale pe benzi (sablat și lustruit), gravura micro de pe flanc și capacul din zirconia gravat.
  - `build_orb()` (B), `build_eve()` (C), `build_soul_d()` (D) și `build_cradle()` (dock-ul din porțelan,
    decupat cu boolean).
- `src/soul_scene.py` e scena amuletei v3 (din ea a ieșit `v3_amulet_ref.png`) și biblioteca comună.
  Codul v1 (`build_amulet`) e încă acolo pentru moneda v1 din lineup.
- `src/eyes.py` generează texturile ochilor, `src/engrave.py` masca gravurii, `tex/micro_soul.png` gravura de pe flanc,
  iar `src/annotate.py` etichetele subțiri (DejaVu Sans ExtraLight).
- `src/post.py` face denoise-ul Intel Open Image Denoise (culoare + albedo + normale), un bloom discret și
  transformarea de culoare **AgX**, ca la v1.
- Motor: **Cycles pe CPU** (4 nuclee), 96–144 de eșantioane/pixel plus OIDN, cam 6–10 min pe cadru.

## Limitări cunoscute

- Nu e CAD de producție: nu există garnituri, mecanismul real al ramei (clicuri, encoder), grosimi de perete,
  antenă sau baterie. Moletarea, teșiturile și gravura sunt aproximări vizuale.
- Halo-urile și inelele de lumină sunt surse emisive „ideale”. În realitate lumina depinde de LED-uri, ghidul de lumină și difuzor.
- B (sticlă plină) e cel mai greu de făcut să arate bine în realitate: interiorul ar trebui „designed” cap-coadă
  (vezi riscurile din research/08).
- C seamănă intenționat cu EVE. Pentru un produs real trebuie verificat riscul de trade-dress.
- Laptopul, birourile, cana și soclurile sunt obiecte generice simple, fără nicio marcă.
