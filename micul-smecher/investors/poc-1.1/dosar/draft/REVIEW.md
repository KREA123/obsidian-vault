---
tip: finanțare
proiect: SOUL-PoC
rol: autoverificarea draft-urilor Anexa 3 + Anexa 16 + modele, față de Grila ETF (Anexa 10)
actualizat: 2026-09-25
stare: draft 1, de citit de Andu; expertul revizuiește Anexa 16
---

# REVIEW · Autoverificare pe Grila ETF

**Fișiere din `dosar/draft/`:**

| Fișier | Ce este | Pagini (randare LibreOffice) |
|---|---|---|
| `Anexa_3_Plan_Afaceri_SOUL_DRAFT.docx` | modelul oficial Anexa 3 completat secțiune cu secțiune | 32 |
| `Anexa_16_Raport_Stiintific_SOUL_DRAFT.docx` | modelul oficial Anexa 16 completat, gata de revizuirea și semnătura expertului | 22 |
| `Scrisoare_de_intentie_MODEL.docx` | ghid + 3 variante de o pagină (A retailer/distribuitor, B laborator universitar, C utilizator pilot din mediul de afaceri), fiecare cu cele 7 elemente din Grila 4.2 | 4 |
| `Declaratie_cesiune_drepturi_MODEL.docx` | contract de cesiune gratuită Andu → ARTEMIS (cod, design, CAD, brand) + inventar + lista componentelor open-source. **⚠ De revizuit de un avocat** | 3 |

**Cum au fost făcute.** Șabloanele oficiale au fost editate direct: structura, titlurile, numerotarea, tabelele, antetul și subsolul au rămas cele din model. S-au șters: instrucțiunile albastre (✏), sfaturile verzi (✔), secțiunea „Ghid de utilizare” (și intrarea ei din cuprins) și propozițiile-ghid de sub titluri. Avertismentele portocalii (⚠) au rămas, pentru că fac parte din model. Tot ce nu știm încă e marcat **[între paranteze, cu fundal galben]**. Cifrele, lunile, obiectivele, activitățile, indicatorii, bugetul, TRL-ul și domeniile RIS3 sunt copiate din `03-NUCLEU-PROIECT.md` prin același fișier de date, deci sunt identice în Anexa 3 și în Anexa 16. Toate documentele trec validarea XSD (`validate.py`) și au fost randate în PDF și verificate vizual.

**Abateri de la `03-NUCLEU` (de decis de Andu):**
1. **Numărul de teste firmware:** în nucleu scrie 55/55. Azi, `pio test -e native` dă **61/61** (cele 6 teste noi sunt pentru geometria de 480 px a lui SOUL M). În draft am scris 61/61, cu mențiunea „55 în v1 + 6 pentru 480 px”. **Actualizați nucleul §4.1 D1.** Testele AI dau 49/49, ca în nucleu.
2. **X1 (portul pe 2.8C):** codul pentru `lcd28` există deja și compilează (`firmware/README.md`), dar nu a fost încă încărcat pe placă. În draft apare „codul există, compilează; neflash-uit” și este marcat „în curs”.
3. **Proiecția financiară pe 5 ani** nu exista în nucleu (§16 spunea „Claude o calculează separat”). Am construit-o în `scratchpad/work/proj.py` din ipotezele explicite din nucleu (349 € → 239–299 €, COGS 190 € → 60 €, echipa din §16). Toate valorile sunt etichetate [E]. Trebuie trecută în nucleu și verificată de contabil.
4. **Defalcarea materialelor (linia 11)** și împărțirea taxelor EUIPO (1.050 € + 940 €) pe rânduri sunt orientative [E]. Totalurile sunt cele din nucleu.

---

## 1. Scor pe subcriterii (evaluarea draft-urilor, nu a dosarului complet)

Legendă: **Complet** = textul acoperă tot ce cere grila · **Parțial** = conținutul există, dar punctajul depinde de un document sau de un nume care lipsește · **0** = nu se poate puncta încă.

### 1. Contribuția la OS 1.1 (40)

| Sub | Max | Unde în draft | Stare | Motiv / ce lipsește | Estimare |
|---|---|---|---|---|---|
| 1.1 RIS3 (≥ 2 domenii) | 5 | A3 antet + §4.1 (bifate TIC și SCI, argumentare pe O/A/R); A16 date generale + §1.3 | **Complet*** | *Subdomeniile exacte din RIS3 BI sunt încă placeholder (Cl, după descărcarea strategiei). Aceeași formulare trebuie pusă și în CF | 5 |
| 1.2 Relevanța problemei | 15 | A3 §1.1, §1.4, §3.1, §3.3; A16 §1.1–1.5, §2 | **Complet** | Problemă europeană cu surse cu link și dată (Eurostat, IDC, TechCrunch, Axios, The Register, EUR-Lex), 11 lucrări 2021–2025 cu DOI verificate prin Crossref/arXiv, tabelul N1–N5 cu ținte măsurabile. Riscul rămâne subiectivitatea evaluatorului: punctajul ține de D8 (dovezile pe hardware) | 10–15 |
| 1.3 Sediu în BI ≤ 31.12.2025 | 5 | A3 §2.1 (adresă = placeholder) | **Parțial** | se dovedește prin certificatul constatator, nu prin text | 5 dacă data e OK |
| 1.4 Publicare OA | 10 | A3 §6.2; A16 §6.4 + §5.4 (R4) + bugetul (linia 21, APC 3.388 €) | **Complet*** | APC bugetat, OA peer-review + Zenodo, calendar IP (≤ L5/L6) → trimitere ≤ L20. *Revista țintă nu e încă numită (placeholder Cl + captura paginii de APC) | 10 |
| 1.5 Economie circulară | 5 | A3 §4.3 (tabelul EC) + §3.4; A16 §1.5, P10, H5, [10–11] | **Complet** | principiile sunt aplicate produsului și verificate prin P10 (înlocuirea bateriei ≤ 5 min), raportul de dezasamblare și OTA | 5 |

### 2. Calitatea documentației (37)

| Sub | Max | Unde | Stare | Motiv | Estimare |
|---|---|---|---|---|---|
| 2.1a Nevoie de piață + grup țintă | 2 | A3 §3.1, §3.2 (4 segmente cuantificate [E]) + grupul țintă | **Complet** | fiecare cifră de piață are link și dată; dimensiunea adresabilă e o estimare declarată | 2 |
| 2.1b Etapele de realizare | 2 | A3 §4.3: tabelul A0–A8, Gantt L1–L24, dependențe, milestone-uri | **Complet** | – | 2 |
| 2.1c Poziționare competitivă | 2 | A3 §3.3 (9 competitori, cu țară, soluție, avantaj, surse), §3.5 (preț, canale, promovare, obiective), §3.6 SWOT | **Complet** | – | 2 |
| 2.1d IP | 5 | A3 §6.2 (plan în 9 pași: TMview, design UE ≤ L5, marcă ≤ L6, brevetabilitate L12–L18, secret comercial, cesiune, „întâi protecția, apoi publicarea”), bugetul liniilor 19–20 | **Complet** | demersuri concrete, cu termene și costuri. Mai puternic dacă depunem căutarea TMview/DesignView și, eventual, marca prin SME Fund | 5 |
| 2.1e Riscuri + eșec de cercetare | 4 | A3 §6.4 (R1–R12; R1 = eșec de cercetare, poarta IE2, Anexa 17, activele TRL 5 după poartă); §1.3 | **Complet** | – | 4 |
| 2.2a Încadrarea liniilor + praguri | 2 | A3 §4.7 (sinteza bugetului + verificarea pragurilor), §4.5–4.7 | **Complet*** | *Se reverifică pe Anexa 20 finală (plafoane) și la helpdesk (CNC/PCBA ca „servicii echivalente”) | 1–2 |
| 2.2b ≥ 2 surse pe linie | 3 | – (Anexa 19 + oferte) | **0 azi** | nu ține de aceste draft-uri: lipsesc ofertele. Notă de sursă unică pentru taxele EUIPO | 0 → 3 |
| 2.2c Salarii ≤ HG 1188 | 2 | A3 §5.2–5.3 (categoria HG, plafonul și tariful pe fiecare rând; CAM separat) | **Complet** | 34/35 · 25/35 · 12/15 · 18/50 €/h | 2 |
| 2.3a Problemă, ipoteză, obiective | 3 | A16 §1.1 (ipoteză „dacă…, atunci…” cu cifre, falsificabilă), §1.4 O1–O4, §6.1 H1–H5 | **Complet** | – | 3 |
| 2.3b TRL 3 cu dovezi | 2 | A16 §2.1–2.4 (D1–D7 existente, D8 + X1–X8 „în curs”) | **Parțial** | fără raportul de laborator pe placa 2.8C, evaluatorul vede doar teste software + simulator | 1 → 2 după X1–X8 |
| 2.3c Activități TRL 4–5, metodologie | 3 | A16 §3.1–3.3 (5 etape, P1–P11 cu metodă, baseline, praguri TRL 4/5, mediu), mediul relevant (Anexa 18), etica | **Complet** | – | 3 |
| 2.3d Resurse pentru TRL superior | 3 | A16 §4.1–4.2; A3 §2.5, §4.4 | **Parțial** | resursele sunt descrise complet, dar grila cere documente: scrisori de la UPB/IMT și de la laboratorul EMC, oferte | 1,5 → 3 |
| 2.3e Plan de lucru | 2 | A16 §5.1–5.4 (A1–A8 cu TRL, livrabile, milestone-uri; Gantt; 11 livrabile cu responsabil) | **Complet** | – | 2 |
| 2.3f Ipoteze, indicatori, rezultate | 2 | A16 §6.1–6.3 (H1–H5; I1–I14 cu UM, țintă, metodă; R1–R5 cu baseline → țintă) | **Complet** | – | 2 |

### 3. Capacitatea de implementare (9)

| Sub | Max | Unde | Stare | Motiv | Estimare |
|---|---|---|---|---|---|
| 3.1 Echipa nominalizată | 5 | A3 §5.2 (cerințele de profil sunt scrise; numele = placeholder) | **0 azi** | coordonatorul (≥ 5 ani / doctor) și inginerul (≥ 2 ani) trebuie nominalizați, cu CV + dovezi, înainte de depunere | 0 → 5 |
| 3.2a Experiența CDI a firmei | 2 | A3 §2.3 (D1–D8), A16 §2.3 | **Parțial** | dovezile există, dar cer „Raportul tehnic Activitatea CDI SOUL 2026” semnat, cu anexe (git, loguri de test) | 1–2 |
| 3.2b Încă un membru cu experiență CDI | 2 | A3 §1.3, §5.3 (Andu) | **Parțial** | trebuie CV-ul lui Andu cu activitatea CD SOUL documentată sau un al doilea inginer | 1–2 |

### 4. Sustenabilitate și teme orizontale (14)

| Sub | Max | Unde | Stare | Motiv | Estimare |
|---|---|---|---|---|---|
| 4.1 Strategie post-PoC (5 elemente) | 5 | A3 §6.1 (4 etape TRL 6→9, cerințe, perioade, surse de finanțare, punct de pornire = R2), §6.3 (proiecție pe 5 ani + 7 ipoteze + scenariu prudent), §5.4 | **Complet** | (i) traseul TRL ✓ (ii) modelul de business ✓ (iii) sursele ✓ (iv) 5 ani ✓ (v) legătura cu R2 ✓. Contabilul trebuie să completeze rândul „alte venituri” | 5 |
| 4.2 ≥ 2 scrisori valide | 4 | `Scrisoare_de_intentie_MODEL.docx` (toate cele 7 elemente, bifate în tabelul de control) | **0 azi** | modelul e gata; scrisorile trebuie semnate de ≥ 2 entități distincte, datate cu ≤ 6 luni înainte de depunere | 0 → 4 |
| 4.3a Tânăr ≤ 24 ani în CD | 3 | A3 §5.1, §5.2 (studentul, A3/A5/A7) | **Parțial** | trebuie nominalizat, cu adeverință de student 2026–2027 + CIM/angajament + fișă de post | 0 → 3 |
| 4.3b Măsură suplimentară | 2 | A3 §5.1 (panelul TRL 5 cu ≥ 40 % femei / ≥ 3 persoane peste 55 de ani / ≥ 2 persoane cu dizabilități + testul de accesibilitate cu raport public) | **Complet** | se anexează politica internă semnată și, ideal, scrisoarea asociației | 2 |

### Total

| | 1 (40) | 2 (37) | 3 (9) | 4 (14) | **Total** |
|---|---|---|---|---|---|
| **Draft-urile azi** (placeholder-ele netratate, fără D8, oferte, echipă, scrisori) | 35–40 | 30,5–31,5 | 2–4 | 7 | **≈ 75–83** |
| **Cu tot ce e listat mai jos** (X1–X8, oferte, echipă, scrisori, student, revista, subdomeniile RIS3) | 38–40 | 35–37 | 7–9 | 14 | **≈ 94–100** (realist ~92) |

**Pe scurt:** textul acoperă integral 19 din cele 26 de subcriterii. Celelalte 7 (2.2b, 2.3b, 2.3d, 3.1, 3.2, 4.2, 4.3a) depind de **documente și nume**, nu de redactare.

---

## 2. Lista completă a placeholder-elor și cine le completează

**A** = Andu · **Ct** = contabilul · **E** = expertul · **Cl** = Claude · **M** = membrii echipei · **F** = parteneri/furnizori · **Av** = avocat

### Anexa 3 — Plan de afaceri (61 de marcaje)

| Unde | Placeholder | Cine |
|---|---|---|
| antet, §2.1 | CUI, nr. Reg. Com. (J40/…), data înființării (din certificatul constatator) | A / Ct |
| antet, §2.1 | domeniul RIS3: subdomeniile exacte din RIS3 BI 2021–2027 | Cl (după descărcarea de pe adrbi.ro) |
| antet, semnătura | data completării / data semnării | A |
| §2.1 | adresa sediului, sectorul, locația de implementare (dacă diferă) | A |
| §2.1 | codul CAEN principal; codul CAEN de CD autorizat la locul de implementare | Ct |
| §2.1 | capitalul social, structura acționariatului, numărul mediu de angajați | Ct / A |
| §2.1 | categoria IMM (Anexa 7, inclusiv firmele legate) | Ct |
| §2.1, declarația | numele complet al reprezentantului legal (Andu) | A |
| §1.3, §2.4 | confirmarea „fără proiecte anterioare cu finanțare europeană” | A |
| §1.3, §5.2 | numele coordonatorului tehnic/științific, al inginerului embedded și al studentului + CV/diplome/adeverință | A + M |
| §2.2 | 2–3 fraze cu cifre despre KREA/MundiShop (ani, clienți, echipă) | A |
| §2.3 | semnarea cesiunii (model în dosar) | A (+ Av) |
| §2.3 (D1) | exportul logurilor de test + hash-ul git la data depunerii | A + Cl |
| §2.5 | organizația de cercetare (UPB ETTI / IMT / ICI), laboratorul EMC/RF, asociația persoanelor cu dizabilități, expertul (nume, afiliere); scrisori/oferte „de obținut” | A + F |
| §4.1 | citarea exactă a subdomeniilor RIS3 BI | Cl |
| §4.4 | adresa, suprafața (mp), dreptul de folosință (proprietate/chirie/comodat) | A |
| §5.1 | semnarea politicii de egalitate de șanse; verificarea scutirii de impozit CD | A; Ct |
| §5.1 | nominalizarea studentului + adeverința 2026–2027 | A + M |
| §5.3 | CIM pentru administrator sau serviciu extern de management | Ct |
| §6.2 | revista țintă OA (MDPI Electronics/Sensors sau IEEE Access) + captura paginii de APC | Cl |
| §6.3 | rândul „alte venituri” (activitatea curentă, An 1–5) ×5; regimul fiscal | Ct |
| §6.4 (R10) | decizia Founders 00 (fără CE/vânzare SOUL M înainte de contract) | A |
| §4.7 | spațiul de minimis în RegAS | Ct |

### Anexa 16 — Raport științific (69 de marcaje)

| Unde | Placeholder | Cine |
|---|---|---|
| date generale | CUI / Reg. Com.; tipul de expert (independent sau colectiv) | A / Ct; A + E |
| identificarea expertului, semnături | nume, afiliere, domeniu, dovezile a) ≥ 5 ani b) ≥ 2 publicații cu DOI c) certificări; semnătura și data | **E** |
| §1.2 | validarea selecției bibliografice (și eventuale surse proprii ale expertului) | **E** |
| §1.3 | subdomeniile RIS3 BI | Cl |
| §2.2, §2.3 (D8), §6.3 (R1, R2), X1–X8 (×10 „în curs”) | rezultatele experimentelor X1–X8 și Raportul de laborator TRL 3 datat și semnat | **A + Cl** (T−6 … T−2 săpt.) |
| §2.3 (D1), §7.2 | exportul git + hash-ul la data depunerii | A + Cl |
| §2.3 | cesiunea semnată înainte de depunere | A (+ Av) |
| §4.1 | dreptul de folosință al spațiului; laboratorul EMC/RF acreditat (denumire) | A |
| §4.1, §4.2 (×5 „anexa nr. …”, ×4 „de anexat”) | UPB ETTI / IMT / ICI, laboratorul EMC, living lab-ul, asociația, firma de software/retailerul + documentele lor | A + F |
| §4.2, §5.4 (×9 „[Nume]”) | numele coordonatorului, inginerului, studentului | A + M |
| §6.4 | revista țintă + captura paginii de APC | Cl |
| VIII | semnătura solicitantului (Andu) + data | A |

### Scrisoare_de_intentie_MODEL

Se completează de fiecare emitent: antetul, numărul și data (≤ 6 luni înainte de depunere), numele și funcția reprezentantului legal, CUI, e-mail, telefon, semnătura. Pe variante: A (magazinul, numărul de prototipuri expuse, piața de distribuție, comanda orientativă), B (laboratorul, domeniul de expertiză, facultatea, lunile L4–L22), C (numărul de utilizatori-pilot, achiziția orientativă). **Cine:** A obține scrisorile; F le semnează. Țintă: 3–4 scrisori de la entități distincte.

### Declaratie_cesiune_drepturi_MODEL

Datele de identificare ale lui Andu (CNP, CI, domiciliu), datele ARTEMIS (sediu, J40, CUI), data (**anterioară depunerii**), hash-urile commit-urilor din Anexa 1, domeniile și conturile, licențele dependențelor Python. **Av** verifică cele 5 puncte din caseta roșie: operele create cu asistență AI, desenul/modelul nedepus, semnul „SOUL” neînregistrat, eventuala hotărâre AGA, data certă. Semnează A (în nume propriu și pentru ARTEMIS).

---

## 3. Ce mai trebuie făcut pentru punctajul maxim (în ordinea impactului)

1. **X1–X8 pe placa 2.8C + Raportul de laborator TRL 3** → 2.3b (+1), 1.2 (credibilitate), 3.2a. După ce apar valorile, Claude le trece în A16 §2.3/§6.3 și în baseline-ul P1–P9.
2. **Echipa nominalizată** (coordonator ≥ 5 ani, inginer ≥ 2 ani, student ≤ 24 ani) → 3.1 (+5), 3.2b (+2), 4.3a (+3).
3. **≥ 2 (ideal 3–4) scrisori semnate** după model → 4.2 (+4). Scrisoarea de la laboratorul universitar ajută și la 2.3d.
4. **Oferte: 2 pe fiecare linie + nota de sursă unică pentru EUIPO** → 2.2b (+3).
5. **Expertul**: citește A16, completează blocul de identificare, validează bibliografia, semnează.
6. **Claude:** subdomeniile RIS3 BI, revista OA cu captura paginii de APC, actualizarea `03-NUCLEU` (61/61 teste, proiecția pe 5 ani), aceleași texte în CF.
7. **Contabilul:** §2.1, regimul fiscal, „alte venituri”, RegAS, CIM-ul administratorului.

*Scripturile de generare (reproductibile, de rulat după orice schimbare din nucleu) sunt în scratchpad-ul sesiunii: `work/data.py` (datele din nucleu), `build_a3.py`, `build_a16.py`, `build_models.py`, `proj.py` (proiecția). Nu fac parte din vault.*
