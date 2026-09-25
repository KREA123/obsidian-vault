---
tip: checklist
proiect: SOUL-PoC
pentru: Andu
actualizat: 2026-09-25
---

# 04 · Ce trebuie să faci tu, Andu (în ordine)

**T** = ziua în care se deschide apelul în MySMIS (după calendarul ADR BI: **≈ noiembrie 2026**). Azi, 25.09.2026, suntem la ~**T−6 săptămâni**. Fereastra poate fi scurtă, iar regula e „primul depus, primul evaluat”. **Ținta e să depunem în prima săptămână după T.**

Nimeni nu poate garanta că primim banii. Lista de mai jos elimină motivele de respingere și aduce punctajul spre 90+.

---

## ⛔ Regulile de aur (de azi până la finalul durabilității, ~2032)
- [ ] **Nu schimba asociații și nici administratorii ARTEMIS.** Fără cesiuni de părți sociale, asociați noi (inclusiv investitori), fuziuni sau divizări. Altfel e „condiție artificială” și cererea e respinsă sau contractul reziliat (ghid §5.1.2 p. 41).
- [ ] **Nu comanda, nu semna contracte și nu plăti nimic** din ce vrem să punem în buget (echipamente, CNC, PCB, laborator, IP) **înainte de depunere**. **Ofertele de preț sunt OK** (fără comandă). Excepție: consultanța/expertul pentru cerere.
- [ ] **Nu vinde și nu certifica CE SOUL M înainte de contract** (vezi pasul 3). Waitlist-ul e OK.
- [ ] **Nu lăsa datorii** la ANAF sau la primărie, nici măcar de câțiva lei.

---

## Pasul 1 — Verificări despre firmă · **până la T−5 săpt. (≈ 05.10.2026)**
- [ ] **Certificat constatator cu istoric** (portal ONRC): **nicio mențiune de asociați/administratori după 03.06.2026**. Trimite-mi PDF-ul.
- [ ] **Statut IMM** (cu contabilul): numărul de salariați, cifra de afaceri și activele pe **2024 și 2025**, plus **toate firmele în care ai > 25 %** (sau în care ARTEMIS are participații). Se completează Anexa 7.
- [ ] **„Întreprindere în dificultate”** (cu contabilul, pe bilanțul 2025): capitalurile proprii trebuie să fie **pozitive și ≥ jumătate din capitalul social**. ⚠ Pierderile MundiShop pot fi o problemă. Dacă e cazul, contabilul propune soluția (ex. majorare de capital **de către tine, ca asociat existent**, fără asociați noi).
- [ ] **De minimis**: lista tuturor ajutoarelor de minimis primite în ultimii 3 ani de ARTEMIS **și** de firmele legate (granturi COVID, IMM Invest/garanții, microgranturi, EDIH, alte programe). Contabilul verifică în **RegAS** (Consiliul Concurenței) sau la furnizori. Avem nevoie de **≥ 108.700 € liberi** din plafonul de 300.000 €.
- [ ] **Datorii**: SPV ANAF + primăria de sector → **0 restanțe**. Contabilul confirmă și cazierul fiscal (fără fapte înscrise).
- [ ] **CAEN Rev.3**: actualizarea (termen 25.09.2026) e făcută? Adăugăm la sediu **7210** (cercetare-dezvoltare în inginerie) și **2640** (electronice de larg consum), eventual **7411** (design industrial). Asta e modificare de **obiect de activitate**, nu de asociați, deci e permisă.
- [ ] **Sediul/punctul de lucru din București**: data înregistrării la ONRC e **≤ 31.12.2025**? Atunci luăm 5 puncte la criteriul 1.3. Spațiul e potrivit pentru un mic laborator (prize, internet, o masă de lucru)? Ai **contract de comodat/închiriere** care poate acoperi 2027 → 2032? (Îl cerem abia la contractare, dar trebuie să existe.)
- [ ] **Salariul tău de manager de proiect**: întreabă contabilul dacă poți avea **CIM cu ARTEMIS** fiind administrator/asociat. Dacă nu, managementul se face ca serviciu extern.

## Pasul 2 — Semnătură și cont MySMIS · **până la T−4 săpt.**
- [ ] **Semnătură electronică calificată** pe numele tău (certSIGN, DigiSign, Trans Sped sau AlfaTrust; ≈ 40–100 €/an; token sau cloud).
- [ ] **Cont MySMIS2021** pentru tine + înrolarea ARTEMIS ca organizație (cu semnătura calificată). Testează semnarea unui PDF.
- [ ] Abonează-te la noutățile de pe **regiobucuresti-ilfov.ro** și scrie la **helpdesk@adrbi.ro** cu 3 întrebări (le redactez eu): CNC/PCBA ca „servicii echivalente de dezvoltare experimentală”, CIM-ul administratorului pentru management și dacă un student-angajat poate fi și CDI.

## Pasul 3 — Decizia Founders 00 · **până la T−4 săpt.**
- [ ] Alege între:
  - **A (recomandat pentru grant):** SOUL M nu se vinde și nu se certifică CE înainte de contract (~toamna 2027). Founders 00 devine **pasul de după PoC**. Waitlist-ul continuă.
  - **B:** lansare rapidă cu bani proprii/investitor. PoC-ul devine foarte riscos (TRL > 5, „investiție demarată”). În loc de PoC, încercăm PR BI 1.2.
- [ ] Orice investitor intră **într-un vehicul separat**, nu în ARTEMIS (sau abia după durabilitate).

## Pasul 4 — Dovezile TRL 3 (placa 2.8C) · **cumpări acum, gata la T−3 săpt.**
- [ ] Comandă **din banii tăi, fără s-o pui în buget**: 1–2 × **Waveshare ESP32-S3-Touch-LCD-2.8C** (cu touch, ≈ 40 $), 1 microfon I2S ICS-43434, 1 amplificator MAX98357A + difuzor mic, o celulă Li-ion cu MX1.25, o tablă de aluminiu de 1,5 mm. Păstrează factura în dosarul „pre-proiect”.
- [ ] Eu portez firmware-ul pe ST7701/GT911. Tu faci flash-ul, filmezi și rulezi testele X1–X8 (fps, touch, tastare cu 5 persoane, BLE prin aluminiu, consum) după protocolul pe care ți-l scriu.
- [ ] Semnezi „Raportul de laborator TRL 3” (îl redactez eu), datat, cu video și commit git.
- [ ] Semnezi **cesiunea drepturilor** tale (cod, design, CAD SOUL) către ARTEMIS, cu titlu gratuit (o redactez eu; opțional o vede un avocat).

## Pasul 5 — Expertul științific · **contactează acum, contract până la T−5 săpt., raport semnat la T−2 săpt.**
Condiții (toate trei): **≥ 5 ani** în domeniu · **≥ 2 articole** în ultimii 10 ani · **acreditări/certificări** din ultimii 10 ani. Nu trebuie să fie angajatul tău. **Să nu fie și coordonatorul echipei.** Costul (≈ 1.500–2.500 €) e eligibil și îl poți plăti înainte de depunere.

Unde cauți, pe site-urile facultăților (pagina departamentului → listă de cadre didactice → CV cu publicații):
- [ ] **UPB – Facultatea de Electronică, Telecomunicații și Tehnologia Informației (ETTI)**: departamentele *Dispozitive, Circuite și Arhitecturi Electronice*, *Electronică Aplicată și Ingineria Informației*, *Telecomunicații* (pentru RF/antene); centrul **CETTI** (tehnologie electronică și interconectare).
- [ ] **UPB – Facultatea de Automatică și Calculatoare (ACS)**: departamentul *Calculatoare* (sisteme embedded, interacțiune om–calculator), departamentul *Automatică și Ingineria Sistemelor*.
- [ ] **IMT București** (INCD pentru Microtehnologie): microsisteme, senzori, RF-MEMS.
- [ ] **ICI București** (INCD în Informatică): AI, IoT, securitate cibernetică.
- [ ] Rezervă: **ICIA/RACAI** (Institutul de Cercetări pentru Inteligență Artificială al Academiei Române), pentru partea AI/limba română.
- [ ] Trimite e-mailul-model (îl scriu eu): 1 pagină despre SOUL + ce cerem (validarea raportului, 2–3 întâlniri, semnătura) + onorariul + termenul.
- [ ] Cere-i: CV Europass semnat, lista publicațiilor cu DOI, copii ale certificărilor (ex. certificat de abilitare, certificări IEEE/IPC/EMC, atestat de expert evaluator) și o adeverință de vechime/experiență.
- [ ] Întreabă același departament (sau un alt laborator) și de **o scrisoare de colaborare**: acces la laborator/camera anecoică, sprijin pentru antenă, recrutarea studentului. Ne ajută la criteriul 2.3d și poate conta ca una dintre scrisorile de la 4.2.

## Pasul 6 — Echipa (nominalizată la depunere!) · **până la T−3 săpt.**
- [ ] **Coordonator tehnic/științific**: embedded/electronică, **≥ 5 ani** (ideal cu doctorat), part-time ~50 h/lună, **34 €/h brut**. Semnează CV + declarație de disponibilitate + fișa de post.
- [ ] **Inginer embedded/firmware**: studii superioare în domeniu, **≥ 2 ani** experiență, ~80 h/lună, **25 €/h brut**. Aceleași documente.
- [ ] **Student ≤ 24 ani**, înmatriculat (UPB ETTI/ACS; îl poți găsi prin coordonator sau prin expert), ~60 h/lună, **12 €/h brut**. Documente: **adeverință de student 2026–2027**, copie CI (vârsta), fișă de post, declarație/angajament.
- [ ] **Tu**: CV Europass (manager de proiect + experiența CD SOUL), fișă de post.
- [ ] Toți semnează **CV-ul și fișa de post** (cerință din ghid). Diplomele și certificările se scanează.

## Pasul 7 — Scrisori de intenție (≥ 2, ideal 3–4) · **până la T−3 săpt.**
Se punctează **doar** scrisorile care au **toate cele 7 elemente**, sunt de la **entități diferite** și sunt **datate cu cel mult 6 luni înainte de depunere**. MundiShop/KREA nu contează (sunt tot ARTEMIS).

Cui le ceri (ținte):
- [ ] un **retailer sau distribuitor** de gadgeturi/design (concept store, magazin online de electronice premium): distribuție și testare comercială;
- [ ] o **firmă de software** din București care folosește Claude Code/asistenți AI: pilot cu 3–5 dezvoltatori;
- [ ] un **living lab/hub de inovare** sau un **laborator universitar**: testare și validare;
- [ ] (rezervă) un **creator de conținut/o agenție** pentru validarea comercială sau un club de makeri.

**Model (se tipărește pe antetul emitentului):**

> **SCRISOARE DE INTENȚIE**
> Nr. ____ / Data: **__.__.2026** *(cu cel mult 6 luni înainte de depunerea cererii)*
>
> Către: ARTEMIS DIGITAL S.R.L., CUI ____, București
>
> **(1) Proiectul vizat:** Subsemnatul/a ______, în calitate de **reprezentant legal** al ______ (CUI ____), confirm interesul pentru colaborare în legătură cu proiectul **„SOUL — dispozitiv AI tangibil, local-first, cu interfață circulară și carcasă reparabilă din aluminiu: validarea modelului conceptual de la TRL 3 la TRL 5”** (SOUL-PoC), propus de ARTEMIS DIGITAL S.R.L. în apelul PR BI P1/1.1/1/2026 – Proof of Concept.
>
> **(2) Soluția vizată:** SOUL este un dispozitiv de 90 × 103 × 31 mm, cu carcasă din aluminiu și ecran rotund de 2,8″. Arată doi ochi expresivi, are o tastatură circulară și funcționează offline (notițe, alarme, mementouri) sau cu asistentul AI ales de utilizator (Claude/ChatGPT), inclusiv pentru aprobarea cererilor Claude Code. Bateria poate fi înlocuită de utilizator.
>
> **(3) Rolul nostru:** *[alegeți]* testarea prototipurilor de către __ utilizatori din organizația noastră (pilot) / distribuția produsului prin canalele noastre / acces la laborator și expertiză tehnică / co-dezvoltare / utilizare.
>
> **(4) Forma colaborării:** *[ex.]* acord de pilot fără costuri pentru ARTEMIS; furnizarea de feedback structurat (chestionare, interviuri); negocierea unui contract de distribuție/achiziție după validarea TRL 5.
>
> **(5) Orizontul de timp:** colaborarea începe la **data semnării contractului de finanțare** (estimat 2027) și durează **__ luni** *(ex. 24 luni + 12 luni după finalizare)*.
>
> **(6) Semnătura:** Nume și prenume: ______ · Funcția: **reprezentant legal / administrator / director general** · E-mail: ______ · Telefon: ______ · Semnătura și ștampila (sau semnătură electronică calificată).
>
> **(7) Data:** __.__.2026 *(repetată lângă semnătură)*
>
> *Scrisoarea exprimă o intenție și nu creează obligații financiare pentru niciuna dintre părți.*

## Pasul 8 — Ofertele (2 surse pe fiecare linie) · **cereri la T−5 săpt., toate la T−2 săpt.**
**Doar cereri de ofertă, fără comandă.** Eu redactez e-mailurile/RFQ-urile. Tu le trimiți și îmi dai PDF-urile. Liniile:
- [ ] osciloscop 4 canale ≥ 200 MHz (2 distribuitori)
- [ ] analizor de spectru ≥ 3 GHz (2)
- [ ] analizor de consum (source-measure) (2)
- [ ] cutie ecranată RF (2)
- [ ] stație de lucru PC (2)
- [ ] imprimantă 3D SLA (2)
- [ ] materiale: plăci 2.8C, panouri 2,8″, audio, celule, componente, rășină (capturi datate din 2 magazine)
- [ ] **CNC + anodizare carcase Al** pentru 3 / 5 / 15 seturi (trimitem STEP-ul M la JLCCNC, PCBWay, RapidDirect + un atelier UE/RO)
- [ ] **PCB propriu**: fabricare + asamblare 2 × 10 buc. (JLCPCB + PCBWay)
- [ ] **pre-testare EMC/RF**, 2 sesiuni (un laborator RO + un laborator UE; ex. ICPE-CA sau ICMET Craiova — de verificat acreditarea; Instytut Łączności PL, Phoenix Testlab/Nemko DE)
- [ ] evaluare EN 18031 (2)
- [ ] servicii CDI pentru antenă (UPB/IMT + o firmă de design RF)
- [ ] workshop-uri de testare cu utilizatori (2)
- [ ] SaaS (API AI, găzduire UE, CAD): capturi de prețuri publice
- [ ] consilier în proprietate industrială (2 cabinete)
- [ ] APC la 2 reviste open-access (capturi)
- [ ] conferință/târg: taxă, zbor, cazare (capturi)
- [ ] customer discovery/focus-grupuri (2 agenții)
- [ ] expert/consultanță pentru cerere (2)
- [ ] audit financiar (2 auditori)
- [ ] vizibilitate: afiș/panou (2 tipografii)

## Pasul 9 — IP înainte de depunere · **până la T−4 săpt.**
- [ ] Căutare **TMview** și **DesignView** pentru „SOUL” (clasele 9, 42, 14, 28). Îți fac eu lista de rezultate.
- [ ] Dacă e liberă: decidem dacă depui **marca** acum prin **EUIPO SME Fund** (voucher 75 %, termen **04.12.2026**; întâi voucherul, apoi taxa). Atunci ea **nu** mai intră în bugetul PoC.
- [ ] Notează **data primei publicări** a randărilor SOUL (site, rețele sociale). Designul trebuie înregistrat în **12 luni** de la ea.

## Pasul 10 — Documentele „de hârtie” · **T−2 săpt. … T**
- [ ] Contabilul: **F10/F20/F30/F40 2025 + recipisa**; declarația IMM (Anexa 7).
- [ ] Semnezi politica de egalitate de șanse (o redactez eu).
- [ ] Citești și aprobi **Planul de afaceri** și **Raportul științific** (le redactez eu din `03-NUCLEU`). Expertul semnează raportul.
- [ ] **Certificatul constatator** pentru depunere: cerut cu **≤ 30 de zile** înainte de depunere.
- [ ] CI valabil.
- [ ] Semnezi electronic toate PDF-urile; le încărcăm împreună; **depunem**.

## Pasul 11 — După depunere
- [ ] Răspunzi la clarificări **în termen** (în etapa de contractare: max. 15 zile lucrătoare).
- [ ] Notifici AM PR BI în **5 zile lucrătoare** despre orice schimbare (ghid p. 35).
- [ ] La contractare (15 zile lucrătoare): certificate fiscale (stat + local), cazier fiscal, contractul de spațiu, decizia asociatului, Anexele 5, 13, 14. Le pregătim din timp.
- [ ] Orice ajutor de minimis nou (ex. EDIH) se declară **înainte** de semnarea contractului.

---

### Pe scurt, ce îmi trimiți în următoarele 10 zile
1. Certificatul constatator cu istoric.
2. Bilanțurile 2024 + 2025 (F10/F20/F30/F40).
3. Lista firmelor tale și a ajutoarelor de minimis.
4. Confirmarea: 0 datorii.
5. Decizia A/B pentru Founders 00.
6. Confirmarea că ai comandat placa 2.8C.
