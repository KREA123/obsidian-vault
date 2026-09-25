# SOUL v2 („piatra de buzunar”) — randări oprite

> **Stare: abandonat.** Fondatorul preferă aspectul amuletei v1, așa că varianta v2 (piatra de palmă) a fost
> înlocuită. Munca s-a oprit la jumătate: există **o singură imagine finală**. Nu s-au mai pornit alte cadre.
>
> **Acestea sunt randări pe calculator (CGI), NU fotografii.** Nu există un prototip fizic v2.

## Ce există aici

| Fișier | Ce e |
|---|---|
| `soul_hero.png` (1600×1200) | Singura randare finală: piatra SOUL alb-„nor” (70 × 64 mm, ~22 mm grosime, ecran rotund 1,75", Ø44 mm vizibil, ochi crem), culcată pe fundal cald off-white, la 3/4, cu curelușă textilă prin urechiușa de aluminiu și butonul lateral din aluminiu periat. Cycles CPU, 192 eșantioane, denoise OIDN + AgX. |
| `src/soul_scene.py` | Scena Blender procedurală. Cadre pregătite și previzualizate, dar **nerandate final**: `hand` (în palmă, mână stilizată), `scale` (v1 Ø58 mm lângă v2, cu cote), `os` (ecranul cu cardul „17:00 · Sună la bancă ✓”), `colors` (nor, cer, piersică, grafit, lila), `night` (ochi chihlimbar, corp luminat din interior, pe noptieră, în suportul magnetic), `social` (1080×1920), `turntable`. |
| `src/screens.py` | Texturile ecranului: ochii (prin `../src/eyes.py` din v1) și interfața OS desenată cu PIL la 466×466, font Fredoka → `src/tex/`. |
| `src/hand_sdf.py` | Mâna stilizată (SDF + marching cubes) → `src/tex/hand.npz`. |
| `src/post.py` | Copie neschimbată a post-procesării v1 (denoise OIDN, bloom, AgX). |
| `src/annotate.py` | Cotele pentru cadrul `scale`. |
| `src/render_all.sh` | Randează tot sau doar anumite cadre. |
| `src/fonts/Fredoka-Variable.ttf` | Font OFL (Google Fonts). |

## Dacă se reia vreodată

```bash
cd micul-smecher/renders/v2/src
./render_all.sh hero                   # sau: hand scale os colors night social turntable
PREVIEW=1 ./render_all.sh night        # previzualizare la jumătate de rezoluție
```

Cerințe ca la v1 (Blender 4.0, `numpy pillow OpenEXR opencolorio oidn==0.2.1`) plus `scikit-image`;
scriptul v2 folosește scriptul de scenă v1 din `../src/` ca bibliotecă. ~11 min/cadru pe 4 nuclee.

Note: sticla mată folosește transmisie rugoasă (0,25) + granulație + un volum mai dens în miez și aproape clar spre
margine (marginea arată ca sticlă, luminează în contre-jour); pe fundal alb, varianta albă tot tinde spre „satinat”
— efectul de sticlă se vedea mult mai clar în previzualizările de noapte și la culori.
