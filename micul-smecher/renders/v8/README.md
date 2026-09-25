# SOUL v8: mărimea M (randări / concept CGI)

**Toate imaginile din acest folder sunt randări / concept (CGI), nu fotografii.** Oriunde le folosești, etichetează-le „randare / concept (CGI)".

Fondatorul a ales **mărimea M** (ecran rotund IPS de 2,8″, 480×480, Ø activ ≈ 70–71 mm). v8 este **designul v6 aprobat, neschimbat, doar mai mare**. Randările de studiu v7 nu au plăcut: forma părea întinsă, inelul negru era subțire, iar sticla avea un glow gri de IPS. v8 le corectează pe toate trei.

## Fișiere
| Fișier | Ce arată |
|---|---|
| `soul_v8_hero.png` (1600×1200) | Argint natural, 3/4 din stânga, OU difuz în fundal. Același cadru ca `v6/soul_v6_hero.png` |
| `soul_v8_family.png` (2000×1125) | Cele 5 culori: Grafit · Jar · Argint · Albastru noapte · Șampanie. Același cadru ca în v6 |
| `soul_v8_side.png` | Din partea difuzorului (+x): fanta, teșitura, fața bombată și spatele |
| `soul_v8_hand.png` | În aceeași mână stilizată ca în v4–v6. Mâna are mărimea reală, iar SOUL M o umple ca o piatră mare |
| `soul_v8_desk.png` | Pe un birou de stejar, lângă un telefon generic (71,5 × 147 × 7,8 mm, fără marcă) și o cană (Ø82 × 95 mm) |
| `soul_v8_typing.png` | Pe birou, cu tastatura SoulOS pe ecran (captura în engleză `os/screenshots/soulos3-EN-keyboard-hello-1440.png`, decupată la cercul ecranului) |
| `soul_v8_ou_night.png` | Noaptea, în capsula OU scalată proporțional, cu ochi chihlimbar |

## Ce s-a păstrat din v6 (identic)
- **Silueta din față și proporțiile.** Corpul v6 e scalat **uniform** în lățime și înălțime, cu k = 90 / 63 = 1,4286:
  **63 × 72,2 mm → 90,0 × 103,1 mm**. Conturul din față e același, doar mai mare.
- **Raportul sticlă neagră / corp:** sticla crește de la Ø52 la **Ø74,3 mm**, deci rămâne 0,825 din lățime.
- **Raportul inelului negru:** imaginea de pe ecran păstrează raportul din v6 (21,88 / 26). Ochii, și ecranul în general, ocupă un cerc de Ø62,5 mm, cu aceeași margine neagră ca în v6.
- **Teșitura de 45°** (0,45 → 0,64 mm), cusătura de centură, fanta difuzorului, piciorul plat și placa din polimer. Toate sunt scalate odată cu corpul.
- **CMF:** aluminiu 6061 sablat și anodizat, în aceleași 5 culori, cu picioarele din polimer în același ton:

| Culoare | Aluminiu | Polimer |
|---|---|---|
| Argint natural | #CBCDCF | #B4B6B8 |
| Grafit | #55575B | #3C3E41 |
| Albastru noapte | #26324C | #1D2435 |
| Jar | #D2622C | #A44A22 |
| Șampanie | #D8C3A2 | #BDAA8A |

- **Sticla e neagră și lucioasă.** Nu am pus glow de IPS: e o randare de concept, iar unde pixelii sunt negri sticla e neagră.

## Singura abatere: adâncimea
Scalat uniform, SOUL ar avea 27 × 1,43 = 38,6 mm adâncime. Brief-ul acceptă ~31 mm, deci v8 are **≈ 31,5 mm**.
v7 turtise toată adâncimea cu 0,80, iar asta aplatiza fața bombată. În v8, tot ce e **în fața cusăturii de centură** rămâne scalat exact cu k: fața bombată, sticla, teșitura și racordul lateral. Doar **domul din spate** e comprimat, cu o trecere lină. Din față și din 3/4, SOUL arată exact ca v6. Doar din profil se vede un spate puțin mai plat.

**Dimensiuni SOUL M: ≈ 90 × 103 × 31,5 mm.**

## Observații oneste
- În `hero`, `family`, `side` și `ou_night`, tot cadrul v6 e mărit uniform: camera, luminile, fundalul și OU. De aceea imaginile arată ca în v6. Singurul indiciu de mărime e profunzimea de câmp, puțin mai mare, pentru că diafragma nu se scalează. Scara se vede în `hand`, `desk` și `typing`.
- Cercul imaginii are Ø62,5 mm, ca să păstreze raportul v6. Panoul real de 2,8″ poate afișa până la ~71 mm. UI-ul poate folosi și marginea, iar când e negru nu se vede nicio diferență.
- În `hand`, SOUL M acoperă toată palma, iar degetele rămân în spatele lui. Nu mai e un obiect „de buzunar”, ci o piatră mare, de mărimea unui telefon.
- În `typing`, tastele au ~5,8 mm la scara randării, sau ~6,6 mm dacă UI-ul folosește tot Ø71. Se tastează confortabil cu SOUL pe masă.

## Cum se regenerează
Pipeline-ul v7 → v6 → v5 se încarcă prin `exec`, fără cod duplicat. `src/soul_v8.py` adaugă trei lucruri:
- `compress_depth`: comprimă doar spatele;
- `scale_scene`: scena v6 e construită la mărimea v6, apoi e mărită cu k. Luminile primesc putere × k² și mărime × k, iar camera își păstrează focalizarea. Lemnul de nuc își păstrează granulația reală;
- cadrele noi: `hand`, `desk` și `typing`. Recuzita are mărimea reală.

`src/hand_sdf_v8.py` e mâna v5 cu degetele mai flexate. Forma lui SOUL e „săpată” în mână, iar dispozitivul se așază automat pe palmă. `src/tex_v8.py` decupează captura SoulOS la cercul ecranului.
```
cd renders/v8/src
PREVIEW=1 ./render_v8.sh hero                  # previzualizare în /tmp/soul_v8_render
./render_v8.sh                                  # hero family side hand desk typing ou_night → ../soul_v8_*.png
./render_v8.sh alive                            # opțional: bucla de 5 s (ochii clipesc)
```
Cycles CPU, 4 fire, o singură randare pe rând, apoi `../v5/src/post.py` (OIDN + AgX). Parametrii se reglează cu `-- --set cheie=valoare`, de exemplu `depth=31.5`, `dk_d`, `ty_el`, `hd_rx` sau `hd_fk`.
