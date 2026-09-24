---
tip: produs
afacere: Micul Șmecher
status: activ
actualizat: 2026-09-24
---
# Design produs v2 — SUFLET Pebble

> **Pe scurt:** v2 e o **piatră de râu care deschide ochii**: ovală **68 × 60 × 19 mm, ~80 g**, ecran rotund AMOLED **1,75″ (466×466)**, baterie **1.000 mAh (~2,5 zile normal)**, un singur buton fizic pentru „ține și vorbește”, vibrații „tors”, curea de mână / șnur și un **„Cuib”** magnetic care o încarcă și o ține pe birou. Face lucruri pentru tine cu Claude/ChatGPT (mementouri, notițe vocale, briefing, aprobări Claude Code), dar **nu încearcă să fie telefon**.
> Prototipul pe placa Waveshare iese mai mare: **~72 × 64 × 24 mm, ~100 g**.

Surse brute (EN, cu linkuri): `micul-smecher/research/06-product-design-v2-2026-09-24.md`. Etichete: **[V]** verificat azi (pagină sau datele STEP din proiect) · **[K]** din cunoștințe, de verificat înainte de citat public · **[E]** estimare.

## Ce știm deja sigur (din proiect)
- Placa **Waveshare ESP32-S3-Touch-AMOLED-1.75**: 466×466, 2 microfoane cu anulare de ecou, difuzor 8 Ω 2 W în kit, IMU, RTC, PMU AXP2101, buton PWR, 16 MB flash / 8 MB PSRAM, $29,99–39,99 [V].
- Cote din STEP [V]: sticla Ø48,96 mm, zona activă Ø43,76 mm, placa + modul Ø46, **12,7 mm adâncime la margine** (conector). Carcasa-monedă v1 pe 1.75 cu baterie 400 mAh + difuzor: **Ø60,8 × 23,5 mm** (vezi `cad/README.md`).
- Densitatea ecranului: ~270 ppi (10,6 px/mm) [E].
- Nu există plăci ESP32 cu AMOLED **rotund** mai mare: 2,06″ și 1,8″ de la Waveshare sunt **dreptunghiulare** (tip ceas) [V]. **1,75″ e plafonul rotund** — și e suficient.

## 1. Ce învățăm de la obiectele de referință
| Obiect | Mărime / greutate | Cum se ține, ce input | Ce a mers | Ce n-a mers | Lecția pentru noi |
|---|---|---|---|---|---|
| **Rabbit r1** (Teenage Engineering) | ecran 2,88″ [V]; ~78×78×13 mm, ~115 g [K] | buzunar; buton de vorbit, rotiță, cameră rotativă [V] | obiectul, culoarea, rotița; $199 fără abonament | 130.000 vândute → ~5.000 folositori zilnic (sept. 2024) [V] | un obiect frumos nu e un motiv zilnic. **Lansăm doar sarcini care merg în fiecare zi.** |
| **Humane AI Pin** | ~34 g + ~20 g baterie magnetică [K] | prins prin haine cu magnet; touchpad, gesturi, proiector laser [V] | prinderea magnetică prin material | se supraîncălzea (proiector limitat la 9 min), baterie slabă, $699 + $24/lună, **cărămidă din 28.02.2025** [V] | nu înlocuim telefonul; fără proiector; fără abonament obligatoriu; buget termic; trăiește și fără server. |
| **Playdate** (Panic + TE) | **76×74×9 mm, 86 g** [V] | buzunar; D-pad, A/B, **manivela** [V] | un gest fizic unic + sezoane de conținut | rechemarea bateriilor 2022 | un singur gest memorabil; conținut nou periodic; baterii testate. |
| **Tamagotchi** | ou de breloc ~40×45×15 mm, ~20 g [K]; 3 butoane [V] | lanț, 3 butoane | 98 mil.+ bucăți [V]; forma = „creatură”; ritual zilnic | se plictisește lumea fără conținut nou | forma spune „e viu”; puține butoane. |
| **Nothing Ear (1) / Phone (1)** | cutia Ear (1) ~58,6×58,6×23,7 mm, ~57 g [K] | buzunar | transparența = brand; lumina Glyph = limbaj | cazuri de folosire subțiri pentru Glyph | „sufletul” se vede prin material mat-translucid; lumina e limbajul. |
| **Oura** | 4–6 g, ~2,5–2,9 mm grosime [K] | purtat 24/7, fără input | invizibil, valoarea e în aplicație | abonamentul | valoare pasivă, zero ceremonie. |
| **Apple Watch / AirTag** | ceas 41–49 mm, 30–62 g, ecran 1,7–1,9″ [K]; AirTag Ø31,9×8 mm, 11 g [K] | coroana digitală, „ridici încheietura = se aprinde” | coroana = cel mai bun scroll pe ecran mic | — | **ridici = se trezește** (avem deja gestul). Coroana/inelul e cel mai bun scroll pentru interfețe rotunde. |
| **Plaud NotePin** | **~17 g** [V]; ~50×20×10 mm [K]; 20 h înregistrare, 40 zile standby [V] | **pin magnetic, clips, șnur, brățară** [V]; o apăsare | o sarcină clară (înregistrare → rezumat); >2 mil. bucăți, ~50% plătesc [V] | — | notițele vocale sunt o sarcină pentru care oamenii plătesc; oferă multe moduri de purtare. |
| **Meta Muse Charm** (anunțat sept. 2026) | breloc cu ecran mic + avatar [V] | **amprentă ca să vorbești** [V] | validează „breloc + personaj + voce” | fără preț, fără specificații | gestul de intimitate trebuie să fie al nostru și vizibil; viteză. |
| **Casio Moflin** | ~180 mm, ~280 g [K], fără ecran | ținut în poală; senzori de mângâiere | >20.000 bucăți [V] | nu „face” nimic util | **mângâierea ca input** — la noi, electrozi capacitivi în spate (aproape gratis). |
| **Pebble** (ceasul) | original 52×36×11,5 mm, **38 g, 7 zile** [V/K]; Time Round 38,5 mm, doar ~2 zile [K]; revenire 2025: Pebble 2 Duo $149, Time 2 $225, Round 2 $199 [V] | 4 butoane | bateria lungă, butoanele, comunitatea (Rebble) | Round-ul cu 2 zile de baterie; firma a murit în 2016 [V] | **bateria e o funcție**; butoanele bat touch-ul când nu te uiți; ecosistemul deschis supraviețuiește firmei. |
| **TE OP-1 / Pocket Operators** | OP-1 ~282×102×14 mm, ~590 g aluminiu [K] | encodere tactile colorate | limbaj grafic fix, jucăuș, pe ecrane mici | — | un limbaj grafic strict pentru SufletOS. |
| **Dieter Rams** | 10 principii: inovator, util, estetic, ușor de înțeles, discret, onest, durabil, atent la detaliu, ecologic, **cât mai puțin design** [V] | — | radioul de buzunar Braun T3 (1958) [K] | — | „mai puțin, dar mai bine”: un buton, un ecran, un gest. |
| **Jony Ive / LoveFrom + OpenAI** | dispozitiv de buzunar fără ecran, nu înainte de feb. 2027 [V] | — | obsesie pentru materiale și „cum se simte în mână”; tehnologie calmă | — | grijă pentru material; obiectul trebuie să te liniștească, nu să te agite. |
| **Pietre de râu, pietre de palmă, „worry stones”** | pietre de palmă ~40–65 × 30–45 × 15–25 mm; worry stone ~35–45 × 30–35 × 8–10 mm cu adâncitură de ~20 mm pentru deget [K/E] | ținute, frecate, puse în buzunar | liniștitoare universal, fără instrucțiuni | — | **elipsa organică cu spatele bombat e cea mai „ținibilă” formă care există.** |

## 2. Ergonomie — ce înseamnă „în palmă” și „în buzunar” [K/E]
- **Lungime ≤ 70 mm**: lățimea palmei adulte e ~70 mm (femei, percentila 5) până la ~97 mm (bărbați, percentila 95). Sub 70 mm obiectul stă în palma oricui. **55–70 mm = zona pietrei de palmă.**
- **Folosire cu o mână**: degetul mare acoperă comod ~Ø40–50 mm când obiectul stă în degete → ecranul activ de 44 mm e accesibil de la margine la margine.
- **Grosime 15–22 mm** = piatră; peste 25 mm pare „puc”; sub 12 mm alunecă din mână fără șnur. Marginea subțiată face obiectul să pară mai subțire decât e la mijloc.
- **Buzunar**: buzunarele de blugi pentru femei sunt mult mai mici (studiul The Pudding 2018: în medie ~48% mai scurte) [K] → cel mai mare latură ≤ ~70 mm, grosime ≤ ~22 mm, **nimic proeminent** (o coroană se agață).
- **Greutate**: breloc < 40 g; obiect de buzunar confortabil 60–120 g (Playdate 86 g, r1 ~115 g). **Ținta: 70–95 g** — pare solid și scump, dar nu trage buzunarul sau șnurul. Plasticul pur (~1,1 g/cm³) pare jucărie; ținta e ~1,3–1,8 g/cm³.
- **Raze**: nimic sub 1 mm unde ajunge mâna; conturul ≥ 3 mm; secțiunea unei pietre 6–15 mm; buza din jurul sticlei ≤ 0,5 mm peste sticlă.
- **Lizibilitate**: litera mare trebuie să aibă ~0,4–0,5° din câmpul vizual → **în mână (35 cm): ~3 mm ≈ 30 px**; **pe birou (65 cm): ~5–6 mm ≈ 55–60 px**. Pătratul util din cercul de 44 mm are 31 mm → **~5 rânduri scurte în mână, ~3 pe birou**. Concluzie: **carduri de o privire, nu documente.**

## 3. Forma, materialele, inputul și purtarea
### Trei variante
| | **A. Piatra (Pebble) — aleasă** | B. Moneda cu inel rotativ | C. Capsula / oul |
|---|---|---|---|
| Plan | ovală **68 × 60 mm** (producție) / 72 × 64 (prototip) | rotundă Ø62–64 | 82 × 44 (stadion sau ou) |
| Grosime | **19 mm la mijloc, ~12 la margine** (prod.) / ~24 (prototip) | 17–19, plată | 20–22 |
| Greutate | **75–90 g** | 85–100 g (inel metalic) | 90–110 g |
| Baterie | 1.000 mAh | 800–1.000 mAh | 1.200–1.500 mAh |
| Difuzor | cutie sigilată mică în lobul de jos | foarte strâmt | cel mai bun |
| Input | touch + 1 buton + IMU + spate capacitiv | touch + inel rotativ + buton | touch + buton + rotiță |
| Pro | cea mai plăcută în mână, pare creatură, sigură în buzunar, fără piese mobile, matriță simplă | navigare excelentă prin SufletOS, bună pe birou | sunet și baterie cele mai bune |
| Contra | fără scroll precis | inelul = praf, etanșare, cost, se agață; pare ceas | pierde „ființa rotundă”; seamănă cu o telecomandă sau cu Rabbit |

**Alegerea: A — Piatra.** De ce: e forma cea mai bună în palmă și în buzunar; matrița e cea mai ieftină (2 piese); e cea mai puternică emoțional (piatra care deschide ochii — continuă gestul-semnătură); iar ovalul lasă exact loc pentru un difuzor sigilat și un motor de vibrații în lobul de jos și pentru o baterie de 1.000 mAh în spatele plăcii. Varianta B (inel rotativ) rămâne pentru o ediție „Pro / birou” mai târziu.

### Specificația propusă (A)
- **Contur**: oval moale 68 × 60 mm; ecranul centrat cu 3–4 mm mai sus decât centrul (lobul de jos = difuzor + vibrații).
- **Secțiune**: spate bombat (rază ~60–80 mm), 19 mm la mijloc, ~12 mm pe margine; sticla la nivel cu o buză mată de 0,3–0,5 mm.
- **Prototip pe Waveshare 1.75**: ~72 × 64 × 24 mm, ~95–105 g (conectorul de la marginea plăcii la 12,7 mm + celula 5,2 mm + spumă + perete). Placa proprie de la EVT coboară la 19 mm.
- **Materiale**:
  - corp din **policarbonat mat translucid** — nu blochează radioul, e ieftin la injecție și lasă să se vadă o strălucire caldă din interior („sufletul se vede prin piatră”);
  - ediția premium: **spate din ceramică mată (zirconiu)** — rece, grea (~110 g total), nu blochează antena; sau **inel frontal din aluminiu anodizat sablat** (doar inelul; zona antenei rămâne nemetalică);
  - **fără soft-touch**: se degradează și devine lipicios în 2–4 ani.
- **Input**:
  1. **Ecranul tactil**: tap, swipe, ții apăsat.
  2. **Un singur buton fizic**, la ora 1–2, la nivel cu carcasa, cu cursă reală. **Ții apăsat = vorbești** — microfonul pornește doar prin buton, deci promisiunea „te ascult doar cât ții degetul” devine fizică. Dublă apăsare = înapoi / anulează.
  3. **IMU**: îl ridici → se trezește; cu fața în jos → Nu deranja / mut; scuturat; înclinat → derulează listele.
  4. **Spate capacitiv** (pinii touch ai ESP32-S3 + folie de cupru în carcasă): știe când e ținut în mână și când e mângâiat (la fel ca Moflin, aproape gratis).
  5. **Fără „squeeze”**: ar cere mărci tensometrice — nu în v2.
- **Purtare**:
  - **curea de mână sau șnur detașabil**, printr-o bară ascunsă sus;
  - **clips magnetic** (placă de oțel în carcasă, magnet în clips — lecția Humane / Plaud);
  - **„Cuibul”**: stand greu, tot în formă de piatră, cu aliniere magnetică și **pini pogo de încărcare**, care o ține la 15–20° pe birou (modul Claude Code);
  - USB-C ascuns sub bară doar la unitățile pentru dezvoltatori.

## 4. „Face lucruri pentru tine” — funcții în ordinea valoare × fezabilitate [E]
| # | Funcția | Unde rulează | Valoare | Fezabilitate | Versiune |
|---|---|---|---|---|---|
| 1 | Ochii vii, fără internet (există) | pe dispozitiv | ★★★★★ | gata | v2.0 |
| 2 | **Ții și vorbești** cu Claude / ChatGPT | microfon → Wi-Fi (sau telefon prin BLE) → serverul nostru din UE → LLM + voce | ★★★★★ | mare (stivă tip xiaozhi, MIT) | v2.0 |
| 3 | **Mementouri, alarme, cronometre** din voce | cloud-ul înțelege → alarma stă în RTC-ul local, sună și vibrează **și fără internet** | ★★★★★ | mare | v2.0 |
| 4 | **Notițe vocale → Obsidian / email / telefon** | audio Opus în memorie → urcare → transcriere + rezumat → email / Git (Obsidian) / aplicație | ★★★★★ (Plaud arată că se plătește) | mare | v2.0 |
| 5 | **Aprobări Claude Code / Cowork** (există) | BLE Hardware Buddy | ★★★★ (capul de pod) | gata | v2.0 |
| 6 | Timer de concentrare (ochii „citesc concentrat”) | pe dispozitiv | ★★★★ | mare | v2.0 |
| 7 | Briefing de dimineață (calendar, vreme, un memento) | cloud-ul compune, dispozitivul arată 3 carduri și vorbește | ★★★★ | medie-mare | v2.1 |
| 8 | Notificări de telefon + control muzică | BLE: pe iPhone merge **fără aplicație** (ANCS/AMS); pe Android cere aplicația noastră | ★★★ | medie | v2.1 |
| 9 | Check-in de stare + jurnalul zilei (există în `ai/`) | cloud | ★★★ | mare | v2.1 |
| 10 | Acțiuni MCP (casă inteligentă, trimite mesaj) cu **confirmare pe piatră** (ții = aprobi) | agent cloud + conectorii tăi | ★★★ | medie; fiecare acțiune de scriere se confirmă | v2.2 |
| 11 | Găsește-mi telefonul | aplicația de telefon | ★★ | medie | v2.2 |
| 12 | Traducere (fraze scurte) | cloud | ★★ | medie; telefonul o face mai bine | mai târziu |

### Ce ținem DEPARTE de dispozitiv (lecțiile Humane / Rabbit)
Cameră, proiector, SIM / 4G, ascultare permanentă sau cuvânt de trezire implicit, browsing, tastat, citit texte lungi, plăți, magazin de aplicații, orice încearcă să înlocuiască telefonul. Orice răspuns care întârzie peste ~2 s fără „ochi care gândesc”. **Tot ce e critic în timp (alarmele) merge și offline.**

### SufletOS — regula de bază
**Ochii sunt ecranul principal și bara de stare.**
- Conținutul apare ca un card **sub ochii care se micșorează**, maximum 3 rânduri.
- Swipe în sus = teancul de carduri: următorul eveniment, timerul, ultima notiță.
- Swipe în jos = comutatoare rapide: Nu deranja, volum, Wi-Fi.
- Butonul ținut apăsat = vorbești, de oriunde.
- După 8–10 s, totul se întoarce la ochi.

## 5. Piese și cost suplimentar față de v1 (producție, ~1.000 bucăți) [E]
| Piesă | Alegerea v2 | Δ cost |
|---|---|---|
| Ecran | AMOLED 1,75″ 466² (CO5300) în loc de 1,2–1,43″ | +€3–5 |
| Baterie | LiPo 1.000 mAh **523450** (5,2×34×50 mm, ~19 g) cu protecție | +€1,5–2,5 |
| Difuzor | cutie sigilată 1813/2015 (~0,7–1 W) + plasă acustică | +€0,8–1,5 |
| Vibrații | motor LRA + driver DRV2605L / AW86224 | +€1,5–2,5 |
| Încărcare | pini pogo + magneți în carcasă | +€1–2 |
| Senzor „în buzunar” | lumină/proximitate (VEML7700 / LTR-553) | +€0,5–1 |
| Carcasă | 2 piese PC mat, mai mare + bară + placă de oțel | +€2–4 |
| Curea / șnur | inclus | +€1–2 |
| „Cuibul” (stand greu cu pogo) | inclus la varianta premium sau accesoriu de €19–29 | €4–8 cost propriu |
| **Total** | | **≈ +€11–20 → cost ~€50–70 la 1.000 buc.; ~€38–50 la 10.000** |

- **Preț** (regula ≥ 2,5× costul livrat): **€149** de bază · **€179–199** cu Cuib · **€249+** ediția din ceramică. Se leagă de [[Planul de bani Micul Șmecher]].
- **Prototipul pe dev-kit**: placa $35 + celulă 1.000 mAh €8 + DRV2605L cu LRA €10 + carcasă SLA €15 + curea €3 ≈ **€75–85**.
- **Alternativa 2,06″**: e dreptunghiulară (410×502, format de ceas) [V]. Primești mai mult text, dar pierzi „ființa rotundă”. **Nu o recomandăm** pentru SUFLET; poate fi un produs separat, „SUFLET Desk”.

### Bateria — cât ține (1.000 mAh; de măsurat pe placă) [E]
| Mod | Curent | Timp pe zi | mAh/zi |
|---|---|---|---|
| Ochi în ambient (slab, 2–5 fps, BLE conectat) | ~12–18 mA | 10 h | 150 |
| Treaz, interacțiune (30 fps, touch) | ~70–100 mA | 1 h | 85 |
| Voce (Wi-Fi + difuzor) | ~200–300 mA | 20 min | 85 |
| În buzunar / cu fața în jos (ecran stins, BLE) | ~3–6 mA | 5 h | 25 |
| Noaptea (RTC + trezire din IMU) | ~1–3 mA | 8 h | 15 |
| **Total** | | | **~360 mAh → ~2,5 zile normal; 1–1,5 zile intens; >10 zile în așteptare** |

- **Încărcare la 0,5C (500 mA) → ~2,5 h pe Cuib.** ⚠️ Firmware-ul setează azi 200 mA (sigur pentru 400–500 mAh); pentru 1.000 mAh îl urcăm la 500 mA.
- **Baterie schimbabilă cu șurubelnița** (Regulamentul UE, din februarie 2027) — vezi [[Conformitate și riscuri Micul Șmecher]].

## 6. Pașii următori
1. **Model de formă (looks-like), săptămâna asta**: printezi 3 pietre goale (68×60×19, 72×64×24, 64×56×17) cu lest de alice până la 80–100 g. Le porți 3 zile în buzunar și în geantă și le dai la 5 oameni (inclusiv 3 femei, pentru buzunare). Alegi una.
2. **CAD**: adaugi forma `pebble` în `cad/shapes.scad` (oval + spate bombat + lob pentru difuzor + bară pentru curea + locaș pentru placa de oțel), pentru placa 1.75 și celula 523450.
3. **Comanzi piesele**: celulă 1.000 mAh 523450 cu protecție și conector MX1.25; DRV2605L + LRA; difuzor sigilat 1813/2015; pini pogo magnetici cu 2 contacte; VEML7700.
4. **Firmware**: încărcare 500 mA; profile de consum (ambient 2–5 fps, stins în buzunar sau cu fața în jos); **măsori curentul real** în fiecare mod cu un USB-metru / PPK2 și actualizezi tabelul de baterie.
5. **Butonul „ține și vorbește”** pe PWR-ul plăcii (sau un buton extern pe un GPIO liber). Legi mementourile / alarmele din `ai/` de RTC-ul local. Notițele vocale ajung în Obsidian (prin Git) și pe email.
6. **Schița SufletOS**: 6 ecrane (ochi, card, teanc, comutatoare, ascultă/gândește, aprobare), în simulator. Faci clipuri pentru pagina de lansare.
7. **Cuibul**: stand greu cu magnet + pogo, derivat din standul de birou existent.
8. **Test de 7 zile „mi-a făcut ceva util azi?”** cu 5–10 oameni: câte mementouri, notițe și aprobări pe zi. Poarta: ≥ 3 folosiri utile pe zi la ≥ 60% dintre oameni.
9. Abia apoi: inginer EE pentru placa proprie (EVT), care coboară grosimea la 19 mm. Discuți cu un designer industrial (1–2 zile de schițe) pentru suprafață și materiale.

## Legat de
[[Micul Șmecher]] · [[Produs și dezvoltare Micul Șmecher]] · [[Viziunea — momentul iPhone]] · [[Planul de bani Micul Șmecher]] · [[Brand și lansare Micul Șmecher]] · [[Conformitate și riscuri Micul Șmecher]] · [[Piață și concurență Micul Șmecher]]
