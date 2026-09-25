---
tip: finanțare
proiect: SOUL-PoC
actualizat: 2026-09-25
sursa: Ghid 03.06.2026 §4.4, §7.1–7.5, §8.9; Anexele 3, 10, 16
---

# 01 · Documentele pentru MySMIS2021 — cine le face, cum se semnează, cât sunt valabile

## Reguli generale de format și semnătură
- **Totul se depune exclusiv prin MySMIS2021**, în intervalul apelului (§4.4 p. 34).
- **PDF**, semnat cu **semnătură electronică extinsă bazată pe un certificat calificat** valid al reprezentantului legal (Andu) sau al unei persoane împuternicite expres (§4.4 p. 34; §7.5 p. 71). Furnizori de certificate calificate în RO: certSIGN, DigiSign, Trans Sped, AlfaTrust (≈ 40–100 €/an; livrare pe token sau în cloud).
- Documentele **emise pe hârtie** (oferte, scrisori, diplome) se **scanează integral și lizibil** și se semnează electronic de Andu (§7.5 p. 71). Documentele **elaborate electronic** se salvează ca PDF și se semnează electronic.
- **Limba română** pentru CF și anexe (§7.2 p. 66). Documentele tehnice/comerciale în altă limbă (oferte străine, fișe tehnice) se acceptă cu **traducere simplă asumată de solicitant**. Actele cu valoare juridică emise în străinătate cer traducere autorizată.
- Denumiri clare ale fișierelor, de exemplu `05_Raport_stiintific_SOUL-PoC_semnat.pdf`.
- Dacă MySMIS poate interoga direct registrele (ONRC, ANAF), unele documente nu mai trebuie încărcate (§7.4 p. 70–71). **Le pregătim oricum.**
- **Clarificările nu pot crește punctajul** (Grila ETF, final). Orice dovadă pentru punctaj se încarcă **la depunere**.

Responsabili: **A** = Andu · **Ct** = contabilul · **E** = expertul științific · **Cl** = Claude (redactare) · **F** = furnizori/parteneri · **M** = membrii echipei · **ONRC/ANAF** = instituții.

---

## A. La depunere — documente OBLIGATORII (§7.4 p. 68–71)

| Nr. | Document | Model | Cine îl produce | Semnături | Valabilitate / condiții | Stare |
|---|---|---|---|---|---|---|
| A1 | **Cererea de finanțare** (formularul MySMIS) | MySMIS + Anexa 1 (instrucțiuni) | Cl redactează textele; A le introduce/verifică | A (electronic) | – | ❌ |
| A2 | **Declarația unică** | Anexa 2, **generată în MySMIS** | MySMIS; A verifică fiecare punct | A | la data depunerii | ❌ |
| A3 | **Declarația privind încadrarea în categoria IMM** + calculul pentru întreprinderi partenere/legate | Anexa 7 (+ Îndrumarul 7.1) | Ct (cifre) + Cl (formular) | A | exercițiile N-1 și N-2 față de anul depunerii | ❌ |
| A4 | **Planul de afaceri** ⚠ fără el: respingere fără clarificări | **Anexa 3** (18 p., toate capitolele, inclusiv §6.2 IP și §6.3 proiecție pe 5 ani) | Cl redactează; Ct verifică cifrele financiare; A aprobă | A (declarația de la p. 18 + semnătură electronică) | corelat 100 % cu CF și cu Raportul științific | ❌ |
| A5 | **CV-uri** pentru echipa de cercetare/management nominalizată **+ fișe de post pentru TOATE pozițiile** | Europass (Grila 3.1) | M își completează CV-ul (Cl ajută); Cl redactează fișele de post | **fiecare titular** își semnează CV-ul și fișa de post; A semnează electronic la încărcare | CV-uri datate; se atașează diplome/certificări/adeverințe (Grila 3.1) | ❌ |
| A6 | **Raportul științific** ⚠ fără el: respingere fără clarificări | **Anexa 16** (§I–VIII) | Cl redactează împreună cu A; **E validează** | **A (solicitant) + E (expert/fiecare membru al colectivului)** | ≥ 3 surse științifice din ultimii 5 ani; ≥ 2 dovezi TRL 3 | ❌ |
| A6.1 | Anexe la Raportul științific: dovezile TRL 3 (raport de laborator, loguri, video, commit-uri git), Gantt, scrisori de la organizații de cercetare | Anexa 16 „Anexe la raport” | Cl + A | A (+ E pe raport) | datate înainte de depunere | ❌ |
| A6.2 | **Dovada drepturilor** asupra rezultatelor CD de la care pornim: **contract de cesiune a drepturilor Andu → ARTEMIS** (cod firmware/AI, SoulOS, design v6/M, CAD) + **declarația privind componentele open-source** (claude-desktop-buddy MIT, Nunito OFL, eventual xiaozhi-esp32 MIT) | liber (Cl redactează) | Cl + A (+ avocat, opțional) | A în nume propriu + A pentru ARTEMIS | **datat înainte de depunere**; cu titlu gratuit (costul drepturilor anterioare nu e eligibil) | ❌ |
| A7 | **CV-ul expertului științific** + documentele care dovedesc cumulativ a) ≥ 5 ani de experiență, b) ≥ 2 publicații în ultimii 10 ani, c) acreditări/certificări din ultimii 10 ani | §7.4 poz. 6 | E | E pe CV; A semnează electronic la încărcare | publicații cu DOI, copii ale certificatelor | ❌ |
| A8 | **Centralizatorul privind justificarea costurilor** + documentele justificative (**≥ 2 surse distincte pe linie**: oferte, cataloage, capturi de website datate, cu URL) | **Anexa 19** (neprimită) | Cl completează; A cere ofertele de la F | A | ofertele datate recent și **fără comandă**; capturile cu data și URL-ul vizibile | ❌ |
| A9 | **Certificatul constatator** ONRC | – | A (online, portal ONRC) | A (semnătură electronică pe PDF) | „în termen de valabilitate la data transmiterii”. **Grila 1.3: emis cu cel mult 30 de zile înainte de depunere.** Cerem varianta care arată **sediul, punctele de lucru, data înregistrării lor și activitățile autorizate** | ❌ (se cere în ultima lună) |
| A10 | **Situațiile financiare anuale** ale ultimului an fiscal încheiat și aprobat: **F10** bilanț, **F20** cont de profit și pierdere, **F30** date informative, **F40** situația activelor imobilizate + **recipisa de depunere** | – | Ct | A | exercițiul 2025 (dacă depunem în 2026) | ❌ |
| A11 | **Actul de identitate al reprezentantului legal** (și al împuternicitului, dacă există) | – | A | A | valabil la depunere | ✅ |
| A12 | **Mandat/împuternicire specială** (dacă semnează altcineva decât Andu) | liber | A | A | – | nu e cazul (Andu semnează) |
| A13 | **Orice alte documente** pentru criteriile de evaluare (vezi secțiunea B) | – | – | A | – | ❌ |

## B. La depunere — documente-SUPORT pentru punctaj (§7.4 poz. 12; Grila ETF)

| Nr. | Document | Pentru criteriul | Cine | Condiții de validitate | Stare |
|---|---|---|---|---|---|
| B1 | **≥ 2 scrisori de intenție/acorduri/protocoale** de la **entități distincte**, fiecare cu cele **7 elemente obligatorii** (modelul e în `04-CE-TREBUIE-SA-FACA-ANDU.md`) | 4.2 (4 p.) | F semnează; Cl redactează modelul; A le obține | specifice proiectului; soluția descrisă; rolul partenerului; forma colaborării; orizontul de timp; semnate de reprezentantul legal cu nume, funcție, e-mail, telefon; **datate cu ≤ 6 luni înainte de depunere** | ❌ |
| B2 | **Dosarul de dovezi TRL 3**: raport de laborator datat (fps, touch, BLE, latență, offline), video cu marcaj de timp, loguri seriale, hash/tag git, rezultatele testelor automate (55 + 49), capturi din simulator | 2.3b, 1.2 | Cl (protocol, raport) + A (placa, filmare) | datat, verificabil (link nelistat sau PDF) | ❌ |
| B3 | Lista publicațiilor/rezultatelor CDI ale echipei (anexă la CF) | 1.2, 3.1 | M + Cl | cu DOI/link | ❌ |
| B4 | **Documente privind experiența CDI a ARTEMIS**: raport tehnic intern „SOUL v0 – activitatea CDI 2026” (istoric git, teste, simulator, prototip SoulOS, cercetări 01–12), eventual procese-verbale interne de recepție a livrabilelor, proiecte IT KREA cu componentă de dezvoltare | 3.2a (2 p.) | Cl redactează; A semnează | „simplele declarații nu sunt suficiente”: atașăm dovezi (exporturi, capturi, commit-uri datate) | ❌ |
| B5 | Pentru student: **adeverință de student** (înmatriculat în anul universitar curent) + copie act identitate (vârsta ≤ 24) + **CIM sau angajament** + fișă de post | 4.3a (3 p.) | student + A | adeverința din anul universitar 2026–2027 | ❌ |
| B6 | Declarații de disponibilitate/angajament pentru personalul-cheie neangajat încă (coordonator, inginer) | 3.1, 3.2b | M | semnate, datate | ❌ |
| B7 | Diplome, certificări, atestate pentru pozițiile-cheie | 3.1 | M | copii lizibile | ❌ |
| B8 | **Politica internă de egalitate de șanse și nediscriminare** a ARTEMIS (decizia administratorului) + măsura suplimentară (ex. panel de test TRL 5 cu ≥ 40 % femei și ≥ 2 persoane cu deficiențe de vedere/motorii; testare de accesibilitate cu o asociație) | 4.3b (2 p.) | Cl redactează; A semnează | datată înainte de depunere | ❌ |
| B9 | Dovezi pentru protecția IP: raportul căutării TMview/DesignView „SOUL”, eventual cererea de marcă deja depusă (dacă o depunem prin SME Fund înainte) | 2.1d, 1.2 | A (+ consilier PI) | – | ❌ |
| B10 | Scrisori de disponibilitate a infrastructurii (acces la laborator EMC/RF, cameră anecoică, living lab) de la UPB/IMT/ICPE-CA sau alt laborator | 2.3d | F + A | semnate | ❌ |
| B11 | Oferta/confirmarea revistei sau a platformei open-access (taxa APC publicată pe site: captură datată) | 1.4 | Cl (capturi) | – | ❌ |
| B12 | Surse de piață citate în Planul de afaceri (rapoarte, capturi datate) | 1.2, 2.1a/c | Cl | verificabile | ✅ parțial (research 01, 04, 11) |

## C. Liniile bugetare care cer câte 2 surse (Anexa 19)

Pe fiecare linie: **2 oferte sau 1 ofertă + 1 catalog/captură de website**. Captura trebuie să arate URL-ul, data, prețul și specificația. Liniile vin din `03-NUCLEU-PROIECT.md` §10.

| Linie | Sursa 1 (ofertă) | Sursa 2 (catalog/ofertă) | Cine |
|---|---|---|---|
| Osciloscop 4 canale ≥ 200 MHz | distribuitor RO (ex. Conrad RO, TME, Farnell RO) | catalog Rigol/Siglent (captură) | A / Cl |
| Analizor de spectru ≥ 3 GHz | distribuitor Siglent/Rigol RO/UE | a doua ofertă sau captură | A / Cl |
| Analizor de consum (Joulescope sau echivalent) | Mouser/Digi-Key (captură) | distribuitor UE | Cl |
| Cutie ecranată RF | furnizor UE (ex. Ramsey, tescom — captură) | a doua sursă | Cl |
| Stație de lucru PC | 2 magazine RO (captură) | – | Cl |
| Imprimantă 3D SLA | reseller Formlabs RO/UE | alt model echivalent (Elegoo/Prusa SL1S) | A / Cl |
| Materiale: plăci Waveshare 2.8C, panouri 2,8", audio, celule, componente, rășină | Waveshare/distribuitor + AliExpress/TME (capturi) | Optimus Digital / Robofun (RO) | Cl |
| CNC + anodizare carcase (3 + 5 + 15 seturi) | JLCCNC / PCBWay / RapidDirect (RFQ cu STEP-ul M) | atelier UE/RO (Weerg, Xometry, ARSAT, Alvi) | A trimite STEP-ul; Cl redactează RFQ-ul |
| PCB propriu rev A/B (fabricare + asamblare) | JLCPCB (calculator online, captură) | PCBWay sau un asamblator RO/UE | Cl |
| Pre-testare EMC/RF (2 sesiuni) | laborator RO (ICPE-CA — de verificat dacă are EMC acreditat, ICMET Craiova) | laborator UE (PL: Instytut Łączności; DE: Phoenix Testlab / Nemko) | A trimite RFQ-ul (Cl redactează) |
| Evaluare EN 18031 | laborator/consultant RO | laborator UE | A |
| Servicii CDI externalizate: antenă prin carcasa de aluminiu | UPB ETTI (contract de cercetare) | firmă de design RF (RO/UE) | A |
| Workshop-uri de testare cu utilizatori | spațiu/organizator (ex. un hub din București) | a doua ofertă | A |
| SaaS (API AI, găzduire UE, CAD) | prețurile publice Anthropic/OpenAI/Hetzner/OVH/Autodesk (capturi) | alternative (Scaleway, Onshape) | Cl |
| EUIPO marcă + design | taxele oficiale EUIPO (captură) | – (taxă oficială, **notă justificativă de sursă unică**) | Cl |
| Consilier în proprietate industrială | 2 cabinete autorizate OSIM | – | A |
| APC open-access | pagina de APC a revistei 1 (ex. MDPI *Electronics*/*Sensors*) | revista 2 (ex. IEEE Access) | Cl |
| Conferință/târg (taxă, transport, cazare) | site-ul evenimentului + oferte de zbor/cazare (capturi) | a doua variantă | Cl |
| Customer discovery / focus-grupuri | agenție de research 1 | agenție 2 | A |
| II.2 Consultanță + expert | oferta expertului | a doua ofertă (alt expert sau alt cabinet) | A |
| II.4 Audit financiar | 2 auditori financiari (membri CAFR/ASPAAS) | – | Ct |
| II.5 Vizibilitate (afiș/panou, comunicat) | 2 tipografii | – | A |

---

## D. La contractare (§7.5 p. 71–75) — termen: **15 zile lucrătoare** de la notificare (§8.9 p. 82)

| Nr. | Document | Cine | Valabilitate / condiții | Stare |
|---|---|---|---|---|
| D1 | Dreptul asupra spațiului de implementare: **contract de comodat/locațiune** pe perioada implementării + 3 ani de durabilitate, cu **acordul proprietarului** și clauza prin care proprietarul nu are niciun drept asupra bunurilor din grant (text la p. 73). Dacă e proprietate: **extras de carte funciară emis cu ≤ 30 de zile înainte** | A (+ proprietar) | valabil ≈ 2027 → 2032+ | ❓ |
| D2 | Declarația IMM (Anexa 7), **dacă s-a schimbat ceva** | Ct + A | – | – |
| D3 | **Certificate de atestare fiscală**: buget de stat (ANAF) + **buget local** (primăria de sector) pentru sediu și toate sediile secundare | Ct / A | **în termen de valabilitate** (de regulă 30 de zile de la emitere; verificați pe certificat) | – |
| D4 | **Certificat de cazier fiscal** (OG 39/2015) | Ct / A (SPV) | în termen de valabilitate | – |
| D5 | Documentele statutare **consolidate** (act constitutiv), conforme cu certificatul constatator | A (ONRC) | toate modificările de la înființare | – |
| D6 | **Hotărârea AGA / decizia asociatului unic** de aprobare a proiectului și a cheltuielilor, pe **bugetul final** după evaluare | Cl redactează; A semnează | datată după notificare | – |
| D7 | Declarația reprezentantului legal privind modificările condițiilor de eligibilitate (**Anexa 14**) | A | – | – |
| D8 | Situații financiare noi (dacă a apărut un nou exercițiu aprobat între timp) | Ct | ⚠ dacă procesul trece în 2027, bilanțul 2026 trebuie depus **imediat** la MF (§8.4 p. 79) | – |
| D9 | **Declarația privind ajutoarele de stat și de minimis** primite de întreprinderea unică în ultimii 3 ani (**Anexa 5**) | Ct + A | orice ajutor nou se notifică în ziua semnării, înainte de semnare | – |
| D10 | **Planul de monitorizare** (**Anexa 13**): indicatori de etapă IE1 (≤ L6), IE2 (raport TRL 4, ≤ 2/3), IE3 (TRL 5) + indicatori de management | Cl + A | corelat cu CF | – |
| D11 | Orice document din lista de la depunere, **actualizat**, dacă s-a schimbat ceva (ex. certificat constatator nou, CV-uri pentru posturi ocupate între timp) | A | – | – |
| D12 | Declarație că nu desfășoară CD cu (micro)organisme modificate genetic (după caz) | A | „nu e cazul”, dar dăm declarația | – |
| D13 | Autorizațiile OUG 44/2007 și OUG 43/2007 | – | **nu e cazul** | – |
| D14 | Graficul cererilor de prefinanțare/plată/rambursare (secțiune în CF, completată la contractare) | Cl + Ct | corelat cu calendarul | – |
| D15 | Vizita pe teren (eșantion): în **5 zile lucrătoare** de la notificare; amânare justificată max. 15 zile lucrătoare | A (sau un împuternicit din firmă) | spațiul arată ca un loc de CD | – |

---

## E. Ce trebuie cerut și când (calendar invers față de T = deschiderea apelului, ≈ nov. 2026)

| Când | Document | Observație |
|---|---|---|
| **acum** | certificat constatator **cu istoric** (pentru verificarea internă S7, nu pentru depunere) | vedem mențiunile după 03.06.2026 |
| acum | F10/F20/F30/F40 2024 + 2025, balanța la zi | test IMM + „dificultate” |
| acum | extras RegAS / lista ajutoarelor de minimis | contabil |
| T−8 săpt. | semnătura electronică calificată + cont MySMIS2021 | vezi `04-CE-...` |
| T−6 săpt. | cesiunea drepturilor Andu → ARTEMIS; politica de egalitate de șanse | Cl redactează |
| T−5 săpt. | contract cu expertul (II.2, permis înainte de depunere) | – |
| T−4 săpt. | dovezile TRL 3 (placa 2.8C) | – |
| T−3 săpt. | CV-uri + fișe de post semnate; adeverința studentului | – |
| T−3 săpt. | scrisorile de intenție (datate ≤ 6 luni înainte de depunere) | – |
| T−2 săpt. | ofertele (2 pe linie), Anexa 19 | – |
| T−2 săpt. | Raportul științific semnat de expert; Planul de afaceri final | – |
| **≤ 30 de zile înainte de depunere** | **certificatul constatator** pentru depunere | Grila 1.3 |
| T+0…T+7 zile | încărcare, verificare, depunere | „primul depus, primul evaluat” |
| la contractare | D1–D15 în 15 zile lucrătoare | certificatele fiscale cerute în primele zile ale termenului |
