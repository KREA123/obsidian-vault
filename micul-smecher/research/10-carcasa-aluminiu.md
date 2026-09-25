# SOUL: carcasa din aluminiu (HOPA), de la primele 10–25 de bucăți la 10k (2026-09-25)

Etichete: **[V]** pagină deschisă azi cu WebFetch (URL în §9) · **[V-s]** doar rezumat de căutare, pagina nedeschisă · **[V-0x]** verificat în nota 0x / `design-max/r-cmf` · **[K]** cunoștințe generale, de verificat · **[E]** estimare/calcul propriu.
Pleacă de la 09 (HOPA 63 × 74 × 27,1 mm, 112 g, sticlă Ø52, talpă-balansoar cu 5 pad-uri, fantă difuzor în cusătura laterală, 40 g balast, COM z 23,8) și r-cmf (carcasa PC ≈ $8 @10k). **Nicio cotație nu e reală până nu urcăm același STEP pe platforme:** cifrele pe bucată sunt [E] ancorate în repere [V]. Nimic nu e comis în git.

---

## 0. Pe scurt
- **Primele 10–25 de bucăți: CNC din bloc 6061 (două cochilii: față + spate), sablare + anodizare tip II, comandate toate într-un singur lot în China (JLCCNC/PCBWay/RapidDirect)**, cu talpă și șasiu printate (SLA/MJF) — talpa din polimer e și fereastra de antenă. Carcasa ≈ **$110–220/set la 10 buc., $70–140/set la 25** [E]. Fără matrițe.
- **Prototipurile 1–3 ale fondatorului:** SLA printat (sau FDM pentru potriviri) + vopsea metalizată/Cerakote = model „looks-like" la $30–80/buc.; apoi **2 seturi CNC reale** ($150–300/set) ca test de aspect, greutate, RF.
- **SLM (aluminiu printat) nu merită:** AlSi10Mg se anodizează gri-maroniu, pătat [V], iar suprafața cere oricum sablare + CNC pe locașul sticlei.
- **RF:** un corp metalic închis îneacă BLE/Wi-Fi. Soluția: antena mutată lângă **o bandă de polimer în cusătura-centură** (deja există ca linie de design) + talpa din polimer. Buget: ≤ 3–6 dB pierdere [E], de măsurat.
- **Greutate:** Al 1,2 mm ≈ 24,5 g față de PC 16,4 g → **~120 g cu același balast, COM +0,8 mm** [E]. Rocking-ul rămâne, marja scade; soluție: perete 1,0 mm în zona coroanei sau balast W jos (09 §3.4).
- **Cost total/unitate (sistem complet, fără certificare):** ≈ **$340 (≈ €300) la 10 buc.** și ≈ **$230 (≈ €200) la 25** [E]. **Comandă 25, chiar dacă vinzi 10:** cele 15 seturi în plus costă ~$60 fiecare.
- **Preț de lansare:** **€349–399 „FOUNDERS 00" (25 buc.)** acoperă COGS-ul. **Nu acoperă certificarea CE/RED (€5–12k pentru un lot mic, nota 03)**, care la 25 de buc. înseamnă €200–480/unitate. Vezi §6.
- **Mai târziu (1k/10k):** cel mai ieftin „premium" e **ambutisare (5052) față + spate + CNC de finisare + sablare + anodizare** ≈ **$9–14 carcasă @10k** față de ~$8 la PC, cu scule de $20–45k [E]. Turnarea sub presiune ADC12 e mai ieftină, dar nu se anodizează frumos.

---

## 1. Pilotul de 10–25 de bucăți (focus)
### 1.1 Cum se fabrică fără scule
| Variantă | Look în poze / în mână | Greutate cochilii | Cost/set @10 · @25 [E] | Termen | Verdict |
|---|---|---|---|---|---|
| **(a) CNC 6061-T6 din bloc + sablare + anodizare tip II** | real metal, rece, precis; trece drept „premium" și în mână ✔✔ | 20–25 g (perete 1,0–1,2) | China $110–220 · $70–140; UE (Weerg/Protolabs/Xometry EU) $250–450 · $180–320; RO $200–400 · $150–280 | China 7–12 zile + DHL 3–5 [V]; UE 3–10 zile [V] | **DA: pilotul** |
| (a′) CNC 7075-T6 | +duritate, se lovește mai greu; ton ușor gălbui la anodizare [V], material +15–25 % timp [V] | la fel | +15–30 % | la fel | doar pentru o ediție „grafit" |
| (b) SLM AlSi10Mg (JLC3DP, PCBWay, Craftcloud) + sablare | gri-mat „turnat"; anodizare gri-maronie, pătată (Si 9–11 %) [V]; Ra brut mare → șlefuire manuală | 18–25 g | $60–150 print + $20–40 finisare + CNC pe locașul sticlei | 3–7 zile [V] | NU: nu arată a anodizat |
| (b′) SLM titan TC4 (−47 % preț JLC3DP din 24 iul 2026 [V]) | titan sablat = foarte premium, gri cald | ~34 g la 1,0 mm (ρ 4,43) → +17 g sus ✗ | $80–200 | 5–7 zile | doar ca ediție-bijuterie, cu recalcul balast |
| (b″) Oțel 316L SLM | lucios la polizare | ~60 g ✗ | $50–120 | — | NU (prea greu) |
| (c1) SLA (rășină gri/tough) + grund + vopsea metalizată auto | bun în poze; în mână cald și ușor → „plastic vopsit"; se ciobește pe muchii | 16 g (ca PC) | $30–60 print + $10–25 vopsit | 3–7 zile | looks-like, nu vânzare |
| (c2) SLA/MJF + Cerakote (ceramic 20–30 µm) | satinat metalic uniform, rezistent; MJF cere șlefuire + grund | 16–18 g | print + $10–25/piesă (ateliere: $5–25 piese mici [V-s]) | +1 săpt. | cel mai bun „fals metal" |
| (c3) SLA + galvanizare Cu-Ni-Cr (10–20 µm Cu + 20–25 µm Ni + ~5 µm Cr [V-s]) | metal real la suprafață, crom/nichel satinat; parțial rece | +3–5 g | $20–60/piesă [E] | 2–3 săpt. | frumos, dar **conductiv = blochează RF** → mascat pe bandă; aderență variabilă |
| (d) Hibrid: CNC Al corp + talpă/șasiu printate | = (a) | = (a) | = (a) + $8–20 | = (a) | **recomandat (e de fapt varianta (a))** |
| (d′) Față CNC Al (2,5D, ieftină) + dom spate SLA vopsit | risc de nepotrivire a culorii între metal și vopsea ✗ | — | −25 % | — | NU |

**De ce CNC e scump și cum îl ieftinim** [E; cost = setup + timp de mașină, materialul e ~$2/set]:
- Setup-ul (programare + dispozitiv de prindere) e 40–60 % din preț la 1–10 buc. [V-s Xometry]; o piesă de €80 la 1 buc. coboară la €35–45 la 100 [V-s]. **De aceea 25 > 10.**
- **Cochilia față = 2,5D:** masa plată „D" din jurul sticlei + racord 5 × 7 mm + locaș Ø52,3 cu treaptă → freză frontală + freză-bilă doar pe racord. **Cochilia spate = domul** (supraelipsă 2,2) → 3D cu freză-bilă, pas 0,15–0,2 mm, apoi sablare (ascunde urmele de trecere). Două fixări pe piesă (exterior, apoi interior pe bacuri moi).
- Perete constant 1,2 mm (1,0 la coroană), raze interioare ≥ 1,5 mm (freză Ø3), **fără degajări și fără filete** în Al: șuruburile în inserții din șasiul printat.
- Toleranță strânsă doar pe locașul sticlei și pe cusătură (±0,05); restul ISO 2768-m.
- Aceeași culoare pentru tot lotul: **o singură baie de anodizare** (culoarea variază cu baia, pH, temperatura, etanșarea [V]). Comandă +20 % rezerve din aceeași baie.
- Culori sigure: **natur (argintiu) și grafit/negru**. Albastrul și roșul se decolorează UV [V]; auriul/șampania/portocaliul sunt „sensibile la proces", diferă între furnizori [V] → **eșantion fizic aprobat** înainte de lot.

**Unde** (același STEP la 4–5 platforme, cotațiile vin în minute–24 h):
- China: **JLCCNC** (comandă de la $0,4, anodizare, sablare, periere; express din 3 zile [V-s]) · **PCBWay** (6061/7075/5052, anodizare, din 2 zile [V-s]) · **RapidDirect** (bracket 6061 1 buc.: $65,55 brut, ~$112 livrat [V]).
- UE: **Weerg** (Veneția; 6082/7075, CNC 5 axe, anodizare colorată, sablare, livrare în 2 zile de la confirmare [V]) · Xometry (același bracket: $118 [V]) · Hubs ($152, 14 zile [V]) · Protolabs [K]. Fără vamă, cu TVA intracomunitar.
- **România:** **ARSAT** (Pecica, Arad: ~100 CNC, frezare 4/5 axe, anodizare, sablare [V]) · **Alvi Technik** (Cluj: centru vertical CNC Victor, sablare/vopsire/anodizare, print Stratasys F370 [V]) · Rombis, KlassCNC, cnc-3d.ro [V-s]. Tarif RO ~€35–60/h [K]; avantaj: vezi piesa și baia de anodizare, fără vamă. Dezavantaj: puțini fac 3D fin + anodizare colorată cosmetică; cere „cosmetic sample".

**Import din China în RO** [V/K]:
- DHL Express Shenzhen → RO: 3–5 zile lucrătoare, ~101 RMB/kg ≈ $14/kg [V] → 25 seturi (~2 kg ambalate) ≈ $60–100 cu suprataxe [E].
- Vamă: din 1 iul 2026 scutirea sub €150 a dispărut; **€3/articol doar pentru B2C ≤ €150**; **pentru B2B (firmă cu CUI/EORI) se aplică taxa vamală normală** [V]. „Alte articole din aluminiu" 7616 99 90: ~6 % convențional [K] — codul poate fi și „părți de aparat"; cere clasificare brokerului. Antidumpingul de 61,4 % listat la 7616 99 90 e pentru anumite produse chinezești (radiatoare) [V] → **declară corect „carcasă pentru aparat electronic"**, nu „articol de aluminiu" generic.
- TVA import 21 %, deductibil dacă firma e plătitoare de TVA; comision de vămuire DHL ~€15–30 [K]. Ai nevoie de **EORI**.

### 1.2 Arhitectura pilotului (ieftină, fără piese custom inutile)
- **Placă:** Waveshare ESP32-S3-Touch-AMOLED-1.75 **$29,99–39,99** [V] (ES7210 + 2 mic., ES8311, QMI8658, AXP2101, RTC, conector MX1.25). Există și **1.75C cu carcasă CNC din aluminiu la $39,99–41,99** [V]: **cumpără 2 pentru un test RF gratuit** (RSSI în carcasa lor vs placa goală) înainte de a desena ceva.
- **Sticla stoc a modulului (Ø48,96 peste activ Ø43,76 [V-0x r-cmf])**, fără Ø52 custom: cochilia față o încadrează cu o buză de ~1,5 mm care acoperă inelul mort. Costă $0 în loc de $5–15 NRE + $5–15/buc. Minus: fără „infinity glass" → acceptabil pentru pilot.
- **Atenție la grosime:** stiva Waveshare are 8,9 mm, iar 09 cere ≤ 6,5 mm (09 §3.4). Pilotul („SOUL-P0") are deci nevoie de **+1,5–2 mm adâncime** (≈ 63 × 75 × 29) și de o **celulă stoc mai mică** (603040 ≈ 800 mAh sau 503035), plus verificare în CAD [E].
- **Talpa (fereastra de antenă + pad-uri):** SLA tough/MJF PA12 vopsită în ton cu corpul, 2 × T5 în balast. Moneda cu pad-uri = **PCB mic JLCPCB cu ENIG/aur dur** ($1–3/buc. la 25 [K]).
- **Capsula OU:** conector magnetic pogo 5 pini gata făcut (pereche $2–6 [K]), fără pini custom. Balast: 3 plăci de oțel tăiate cu laser la un atelier local ($1–3) sau W „putty"/foi ($5–10) jos.
- **Șasiu interior** SLA/MJF negru: toate bosajele, inserțiile de alamă și cutia difuzorului. Cochiliile de Al rămân „goale".

### 1.3 Cost complet pe unitate (sistem vândut: SOUL + OU + ambalaj) [E]
| Linie | @10 buc. | @25 buc. | Note |
|---|---|---|---|
| Placă Waveshare 1.75 (+ taxe/transport) | 35–45 | 33–42 | [V] preț listă |
| Celulă Li-po stoc + PCM · difuzor 1813/2030 + LRA · mic./cabluri/magneți/șuruburi/garnituri | 5–9 · 2–4 · 4–7 | 4–8 · 2–3 · 3–6 | |
| Balast oțel/W · monedă PCB pad-uri · conector pogo magnetic | 2–10 · 1–3 · 2–6 | 2–8 · 1–2 · 2–5 | |
| **Carcasă CNC Al 2 cochilii + sablare + anodizare (China)** | **110–220** | **70–140** | +20 % rezerve incluse la 25 |
| Talpă + șasiu printate, vopsite | 12–25 | 8–18 | SLA/MJF |
| Capsulă OU printată (cupă, capac, liner) + finisare + placă USB-C/pogo + balama | 35–60 | 25–45 | SLA + vopsea/Cerakote |
| Ambalaj (cutie rigidă mică, card, cablu) | 8–15 | 6–12 | tipografie RO |
| Transport CN→RO + vamă + comision | 8–15 | 4–8 | §1.1 |
| Rebut/rezervă (~10 %) | 20–35 | 12–25 | |
| **Total COGS** | **≈ $245–455, tipic $340 (≈ €300)** | **≈ $170–330, tipic $230 (≈ €200)** | €1 = $1,137 (09) |
| NU include | manoperă de asamblare (2–3 h/buc., a fondatorului), certificare CE/RED, cont AI, garanție | | |

## 2. Procese pentru volum (1k/10k, pe scurt)
| Proces | Poate face forma? (dom asimetric, 27 mm total, D în plan) | Suprafață | Unitate @1k · @10k [E] | Scule [V/E] |
|---|---|---|---|---|
| **Ambutisare 5052-H32/3003, 0,8–1,0 mm + tăiere + CNC finisare** | DA în 2 cochilii: față ~10 mm, spate ~17 mm adâncime pe 63 × 74 → raport adâncime/lățime ≈ 0,27, sub „deep" (adâncime > diametru [V]); 1 ambutisare + recalibrare | foarte bună după sablare (ascunde liniile de tragere); 5052 se anodizează curat [K] | $12–20 · **$4–7** + finisare | matrițe transfer (mai bune pentru ambutisat [V-s]) $15–40k pentru 2 cochilii + dispozitive CNC $2–5k |
| Extrudare prin impact | doar forme cu simetrie de revoluție / tuburi, cutii [V] | bună | — | NU pentru HOPA |
| Forjare + CNC | DA, piesă masivă → apoi golită prin CNC | excelentă | $18–30 · $8–15 | matrițe forjare $5–15k [E] |
| CNC integral 6061/6063 | DA, orice | excelentă | $25–45 · $15–25 (08: $12–20) | dispozitive $1–3k |
| Turnare sub presiune ADC12 | DA, cu înclinări și perete ≥ 1,2–1,5 | anodizare gri → neagră cu Si 6–12 % [V]; nu se poate natur [V] → vopsea în câmp electric/pulbere, e-coat, PVD | $6–10 · **$2–5** + finisare $1–3 | matriță simplă $3–10k [V], realist $8–20k pentru 2 cochilii |
| Turnare aliaje anodizabile (AlMg „DM3/DM6" [V], Magsimal-59 [K]) | DA, dar AlMg fisurează, se toarnă greu [V] | anodizare colorată posibilă, uniformitate < laminat | +20–40 % față de ADC12 | ca ADC12 + probe |
| MIM | aluminiul MIM e rar comercial [K]; MIM oțel e bun pentru **balast** (09) | — | — | — |
| Oxidare micro-arc (PEO/MAO) pe turnat | Si ridicat scade calitatea [V]; 2000 HV pe aliaje bune [V] | ceramic mat, culori limitate | +$1–3 | — |
**O bucată vs două cochilii:** HOPA are nevoie de cusătură (asamblare, difuzor, antenă); monobloc = CNC din interior prin deschiderea sticlei (ca un Apple Watch), posibil doar CNC și scump. **Rămân două cochilii.**

## 3. Finisaje
- **Sablare (sticlă/ceramică) + anodizare tip II, 10–25 µm** [V], etanșată. China, în volum: $0,5–1,5/piesă [K]; la lot mic: minim $65–150/lot [V-s], deci $3–10/piesă la 25.
- **Culori:** argintiu natur (cel mai stabil) · grafit/negru (stabil; negrul anorganic rezistă la UV [V]) · albastru (se decolorează în UV [V]) · portocaliu/auriu (sensibile la proces, variază între furnizori [V]).
- **Risc de nepotrivire între loturi:** aliaj/tratament termic, finisarea anterioară, baia (T, pH, contaminare), etanșarea, lumina de inspecție [V]. Fără un ΔE universal [V] → **„golden sample" semnat + lumină D65 + același aliaj și același furnizor**. Nu amesteca 6061 cu 6063 în aceeași culoare.
- **Rezistență:** tipul II e mai moale decât tipul III [V], dar mult peste PC la zgârieturi. Loviturile rămân **lovituri (deformare plastică)**, nu zgârieturi. Muchii cu rază ≥ 0,5 mm, altfel se ciobesc la anodizare [K].
- **Dacă e turnat:** vopsea în câmp electric/pulbere (60–80 µm, acoperă porii), e-coat + lac, PVD pe grund (look metalic, dar fin), MAO (mat ceramic). Toate „metal vopsit" → mai puțin „metal sincer" decât anodizarea.

## 4. RF: metalul blochează BLE/Wi-Fi
- Carcasa de Al devine o cușcă Faraday deschisă doar la sticlă (față, panou AMOLED cu spate metalic) și la talpă (plină de balast de oțel). **Antena PCB a lui 09 (colț sus −x, sub dom) ar sta direct sub metal** → pierdere estimată 15–25 dB, adică BLE aproape mort [E].
- **Exemple:**
  - iPhone 4: rama de oțel *e* antena, cu fante, iar prinderea care scurtcircuita fanta făcea semnalul să cadă („antennagate", rezolvat cu bumper) [V].
  - AirTag: capac de oțel, dar placa stă într-un cadru de antenă din plastic, cu RF ieșind prin partea de plastic [V].
  - Beosound A1: dom de Al sablat + bază din polimer [V].
  - Apple Watch din Al: RF prin display/spatele ceramic [K].
  - **Waveshare 1.75C: Wi-Fi/BLE din carcasă CNC de Al [V]** — măsoară-l.
- **Strategii, în ordinea preferinței:**
  1. **Banda-centură din polimer**: cusătura HOPA (09 §3.3) devine un inel de 3–4 mm din PC/PBT colorat în ton sau contrast, lipit/prins între cochilii. Antena (chip ceramic sau FPC) se lipește pe interiorul benzii, sus pe −x, ≥ 5 mm de metal. Tot acolo stau fanta difuzorului și găurile de microfon. Pierdere ≈ 2–5 dB [E]. Pentru pilot: banda printată SLA.
  2. **Talpa din polimer:** doar dacă antena stă pe marginea tălpii, ≥ 10 mm de balast. Balastul de oțel/W detunează [E] → secundar.
  3. **Sticla din față:** inelul mascat Ø43,8–48,9 are ~2,5 mm, dar panoul și cadrul metalic sunt dedesubt → slab [E].
  4. **Carcasa ca antenă** (slot/rama, stil iPhone): cel mai bun randament, dar e proiect RF pentru 1k+.
- **Impact pe rază:** fiecare 6 dB înjumătățește raza în spațiu liber [K]. BLE ~10–30 m în casă → **5–15 m cu −6 dB**, suficient pentru telefon în aceeași cameră. Wi-Fi spre router e ok cu −3…−6 dB [E].
- **Test:** RSSI/TRP cu placa goală vs în carcasă, în mână, pe birou, în OU. Ținta din 09: ≤ 3 dB pierdere. Tolerăm 6 dB la pilot.
- **Efecte secundare:**
  - Electrodul capacitiv de pe coroană nu merge prin metal. În schimb, **cochilia spate izolată devine ea însăși electrod de atingere** (canal touch ESP32-S3) [E].
  - ESD: cochiliile se leagă la masă printr-o zonă nemascată la anodizare [K].
  - Sub dom: niciun magnet N52 lângă antenă.

## 5. Greutate, balans, senzație, căderi [E, modelul de masă din 09 §3.4]
| Carcasă | Masă cochilii | Total cu balast 40 g | COM z | Efect |
|---|---|---|---|---|
| PC 1,8 mm (09) | 16,4 g | 112 g | 23,8 | referință: recuperare ≈ 30° / 28,4° |
| **Al 1,0 mm** (7.575 mm² × 1,0 × 2,70) | 20,5 g | 116 g | 24,2 | marjă −0,4 mm, ok |
| **Al 1,2 mm** | 24,5 g | 120 g | 24,6 | marjă 9,5 → 8,7 mm, recuperarea înapoi ~27° → la limită |
| Al 1,2 mm cu balast redus la 32 g (ca să rămână 112 g) | 24,5 g | 112 g | 25,9 | ✗: sub limita de 28° |
| Al 1,2 + strat inferior W-Ni-Cu 14 g (09) | 24,5 g | 120 g | ≈ 24,2 | ✔ +$1,2–2,5 |
| Printat SLA/MJF 1,8 mm | 16–18 g | 112–114 g | 23,8–23,9 | neschimbat (ca PC) |
- **Regula:** metalul adaugă masă *sus* (cochilia are COM la z ≈ 36), deci nu scoate balast. Perete 1,0 mm pe dom/coroană, 1,2 mm doar în zona cusăturii și a locașului; eventual W jos. Mula cântărită decide.
- **Senzație termică:** aluminiul e „rece" la atingere (efuzivitate ≫ PC) = premium. Uniformizează căldura ESP32/încărcare (bine pentru ≤ 41–43 °C, 09 §3.8), dar iarna e rece în mână [K].
- **Densitate:** 120 g / ~68 cm³ ≈ 1,76 g/cm³, mai aproape de ținta 08 (≥ 1,7) ✔.
- **Căderi:** 120 g de la 1 m ≈ 1,2 J. Sticla scapă datorită mesei plate +0,05–0,10 mm (09), dar **Al se adâncește pe racordul „D"** (nu crapă ca PC) [E]. Sablarea ascunde zgârieturile fine, nu loviturile. Testul din 09 §3.8 rămâne, cu „adâncitură ≤ 0,3 mm acceptată".

## 6. Recomandare
**Prototip 1–3 (fondatorul, săptămânile 1–3):**
1. FDM acasă/Bambu (PLA/PETG, €1–5/set) pentru potrivirea plăcii, celulei, tălpii.
2. **SLA la un print-shop din RO sau Formlabs/JLC3DP** (~$15–40/set), grund + vopsea metalizată sau Cerakote ($10–25) = looks-like pentru poze și teste de mână. Greutate corectă cu balast.
3. **2 seturi CNC reale de la JLCCNC/PCBWay** (qty 2: $150–300/set cu anodizare [E]) = primul test de metal, RF (vs Waveshare 1.75C) și balans. Nu comanda SLM.

**Pilot 10–25 (FOUNDERS 00):**
- CNC 6061 China, un singur lot de 25 + 5 rezerve, argintiu natur + grafit (fără auriu/portocaliu), bandă-centură și talpă printate, placă Waveshare stoc, sticla stoc, pogo magnetic stoc, OU printat.
- COGS ≈ **€200/unitate la 25** (≈ €300 la 10).
- **Preț:** **€349–399** (incl. TVA 21 %). La €349: net ≈ €288 − comisioane/transport ≈ €20 → **≈ €68 marjă × 25 ≈ €1,7k**. La €399 → ≈ €2,9k.
- La 10 bucăți, €349 e **sub cost** (net €268 vs €300); ar trebui minim **€429**.
- **Certificare:** vânzarea către consumatori = punere pe piață → CE/RED obligatoriu, fără scutire pentru serii mici (03). Waveshare folosește cip ESP32-S3 fără modul certificat → teste radio complete, **€5–12k** (03).
  - **Varianta 1:** considerați-o investiție în brand, nu COGS.
  - **Varianta 2:** pre-comandă FOUNDERS la €399–449 (ca în 09: €349–379) cu livrare după teste.
  - **Varianta 3:** trecere la ESP32-S3-WROOM pe PCB propriu (refolosește dovezi radio Espressif).
- **Nu vinde 10 „prototipuri" fără CE.**

**Volum (1k → 10k):**
- **1k:** CNC integral în China $25–45/carcasă, fără scule.
- **5k+:** **ambutisare 5052 front + back + CNC pe locaș/cusătură + sablare + anodizare, bandă-centură PC injectată**. Carcasă **≈ $9–14 @10k** vs **~$8 PC** (+$1–6/unitate).
  - Scule: $20–45k (matrițe transfer + dispozitive + bandă).
  - Furnizori: Dongguan/Shenzhen (ambutisare + anodizare în aceeași fabrică) [K].
  - UE: ambutisori auto/electrocasnice din RO/PL/CZ, de cotat; ARSAT pentru CNC/anodizare [V].
- **ADC12 turnat + vopsea** doar dacă prețul contează mai mult decât „metalul sincer" ($5–8 total).

## 7. Riscuri
- Stiva Waveshare (8,9 mm) nu intră în HOPA-27 → P0 mai gros (§1.2). Fondatorul trebuie să accepte ~29 mm la pilot.
- Culoare diferită între lotul pilot și producția ambutisată (6061 vs 5052, alt furnizor) → FOUNDERS rămâne o ediție separată, declarată.
- RF sub prag → bandă mai lată sau antenă FPC pe bandă. Testul cu 1.75C trebuie făcut în săptămâna 1.
- Talpa printată se uzează la rostogolire → UV coat sau PA12 vopsit, cu rezervă în cutie.

## 8. Pașii următori (2 săptămâni)
1. Cumpără 2 × 1.75 + 2 × 1.75C ($140) și măsoară RSSI.
2. CAD P0 (2 cochilii, bandă, talpă, șasiu) → STEP.
3. **Același STEP la JLCCNC, PCBWay, RapidDirect, Weerg, Xometry, ARSAT, Alvi Technik** pentru 2 / 10 / 25 / 30 buc., cu anodizare natur + grafit → tabel real de cotații.
4. SLA looks-like + Cerakote.
5. Ofertă RED de la un laborator (03) înainte să fixezi prețul.

## 9. Surse
[V] fetched 2026-09-25: https://en.wikipedia.org/wiki/Deep_drawing · https://en.wikipedia.org/wiki/Anodizing · https://en.wikipedia.org/wiki/Impact_extrusion · https://en.wikipedia.org/wiki/Plasma_electrolytic_oxidation · https://en.wikipedia.org/wiki/IPhone_4 · https://www.ifixit.com/News/50145/airtag-teardown-part-one-yeah-this-tracks · https://hlhrapid.com/blog/how-much-does-die-casting-cost/ · https://rollyu.com/anodized-aluminum-colors/ · https://www.prodiecasting.com/die-casting-aluminum-for-anodizing/ · https://tirapid.com/aluminum-machining-cost/ · https://www.otronatlas.com/guides/cnc-machining-cost/ · https://www.weerg.com/en/ · https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm · https://www.waveshare.com/esp32-s3-touch-amoled-1.75c.htm · https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-1.75C · https://jlc3dp.com/blog/metal-3d-printing-cost · https://jlc3dp.com/news/materials-finishing-pricing-update-july2026 · https://www.pcbway.com/rapid-prototyping/3d-printing/metal/aluminum/Aluminum-0/ · https://www.fehrmann-materials.com/en/news/almgty-color-anodized-components-metal-3d-printing · https://www.avalara.com/blog/en/europe/2025/11/eu-end-150-customs-duty-exemption-2026.html · https://www.tariffnumber.com/2026/76169990 · https://goodhopefreight.com/romania/dhl.html · https://www.pocket-lint.com/speakers/reviews/bang-and-olufsen/152302-beosound-a1-2nd-gen-review-bang-olufsen-portable-bluetooth/ · https://www.alvi-technik.com/ · https://www.arsat.ro/ro/industrie-prelucrare-metalica-cnc
[V-s] search summaries only: Xometry cost articles (setup 40–60 %, €80 → €35–45), JLCCNC/PCBWay CNC service pages, transfer vs progressive dies (ht-pt, sancosales), anodising costs (okdor, rivcut: min. $65–150/lot), 6061 vs 6063 cosmetics, Cerakote price lists, electroplating SLA (Formlabs, Sharretts), Romanian CNC workshops (Rombis, KlassCNC, cnc-3d.ro), DHL 2026 rates. vatcalc.com gave 403.
[K]/[E]: all per-part SOUL costs, shell masses and COM (§5), RF losses, the 7616 duty rate (~6 %), clearance fees, Magsimal, aluminium MIM, RO hourly rates, thermal feel, dent behaviour, pogo/PCB coin prices.
