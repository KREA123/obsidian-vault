---
tip: checklist
proiect: SOUL-PoC
pentru: Andu
actualizat: 2026-10-12
---

# 04 · Ce trebuie să faci tu, Andu (în ordine)

**T** = ziua în care se deschide apelul în MySMIS. Data **nu e publicată** (12.10.2026). Ghidul final încă nu a apărut. Estimarea noastră: **decembrie 2026 – februarie 2027** [neverificat]. Putem depune în decembrie **doar dacă** ghidul final apare **cel târziu pe ~1 decembrie** (cu cele 30 de zile de pregătire, MySMIS s-ar deschide ~31 decembrie); **realist**, ca să depunem confortabil în decembrie, trebuie să apară **până la începutul lui noiembrie** [estimare]. Aceeași regulă e în `00-ELIGIBILITATE`. Ținta: dosarul gata **înainte** de T și depus în **prima săptămână**.

Nimeni nu poate garanta banii. Lista de mai jos scoate motivele de respingere și duce punctajul spre 90+.

Datele firmei (le folosim peste tot): **ARTEMIS DIGITAL S.R.L.**, CUI **53145290**, J2025098748009, înregistrată la **17.12.2025**, sediul în Str. Vlăhița nr. 1, bl. PM18bis, sc. 2, ap. 123, Sector 3, București, neplătitoare de TVA.

---

## ⛔ Regulile de aur (de azi până la finalul durabilității, ~2032)
- [ ] **Nu schimba asociații și nici administratorii ARTEMIS.** Fără cesiuni de părți sociale, fără investitori intrați în firmă, fără fuziuni. Altfel cererea e respinsă (ghid §5.1.2 p. 41).
- [ ] **Nu comanda și nu plăti nimic** din ce punem în buget (aparate, CNC, PCB, laborator, IP) **înainte de depunere**. Cererile de ofertă sunt OK. Excepție: expertul și consultanța pentru cerere.
- [ ] **Nu vinde și nu certifica CE SOUL înainte de contract.** Pe site rămâne doar lista de așteptare. **Magazinul Shopify nu se deschide pentru vânzare.** Fără rezervări, fără plăți.
- [ ] **Nu scrie nicăieri că SOUL include AI.** Omul își conectează propriul AI. Abonamentele Claude Pro/Max nu merg pe dispozitive terțe.
- [ ] **Nu lăsa datorii** la ANAF sau la primărie, nici de câțiva lei.

---

## Pasul 1 — Verificări despre firmă · **acum (până la T−6 săpt.)**
- [ ] **Certificat constatator cu istoric** (portal ONRC). Verifici: nicio schimbare de asociați/administratori după 03.06.2026. Îmi trimiți PDF-ul.
- [ ] **Statut IMM** (cu contabilul). Firma e nouă (17.12.2025), deci are doar exercițiul 2025. Contabilul face Anexa 7 și verifică **toate firmele în care ai peste 25 %**.
- [ ] **De minimis** (cu contabilul). Lista tuturor ajutoarelor de minimis din ultimii 3 ani, pentru ARTEMIS și firmele legate. Verificare în **RegAS** (Consiliul Concurenței). Ne trebuie **cel puțin 108.760 € liberi** din plafonul de 300.000 €.
- [ ] **Datorii.** SPV ANAF + primăria Sectorului 3: zero restanțe. Contabilul verifică și cazierul fiscal.
- [ ] **Coduri CAEN** (cu contabilul, la ONRC). Azi ai doar **7311** (publicitate). Adaugi: **2640, 6210, 7210, 7411, 4740** (+ **4791** pentru vânzarea online). Contabilul verifică lista pe **CAEN Rev.3** (la 4791 verifică dacă mai înseamnă vânzare online). E o schimbare de activitate, nu de asociați, deci e permisă.
- [ ] **Locul proiectului.** Sediul e un **apartament**. Ghidul cere un spațiu potrivit pentru activitate economică sau de cercetare și face vizită la fața locului. Alegi:
  - **A:** confirmi (cu contabilul și, dacă trebuie, cu helpdesk@adrbi.ro) că apartamentul e acceptat și pregătești un colț de laborator (masă, prize, internet, dulap);
  - **B:** închiriezi un spațiu mic în București/Ilfov și îl înregistrezi ca **punct de lucru**.
  - Oricum, ai nevoie de un contract (comodat sau chirie) care să acopere ~2027 → 2032. Îl cerem abia la contractare.
- [ ] **Salariul tău de manager de proiect.** Întrebi contabilul dacă poți avea CIM cu ARTEMIS ca administrator. Dacă nu, managementul devine serviciu extern.

## Pasul 2 — Semnătură electronică și cont MySMIS · **până la T−5 săpt.**
- [ ] **Semnătură electronică calificată** pe numele tău (certSIGN, DigiSign, Trans Sped sau AlfaTrust; ~40–100 €/an).
- [ ] **Cont MySMIS2021** + înrolarea ARTEMIS. Testezi semnarea unui PDF.
- [ ] Te abonezi la noutăți pe **regiobucuresti-ilfov.ro/apeluri**. Când apare ghidul final, îmi spui imediat.
- [ ] Trimiți la **helpdesk@adrbi.ro** întrebările pe care le redactez eu: apartamentul ca loc de implementare; CNC/PCB ca „servicii de dezvoltare experimentală”; CIM-ul administratorului; **găzduirea pe servere în UE a instanței de test SOUL Cloud** (linia 18b), folosită doar la testarea prototipurilor: intră la SaaS (ghid §5.3.2 p. 57: servicii „utilizate exclusiv pentru modelarea, testarea, simularea, analiza datelor și dezvoltarea prototipurilor digitale”) sau la servicii pentru dezvoltare experimentală? Reverificăm și pe Anexa 20.

## Pasul 3 — Dovada TRL 3 pe placa reală · **gata la T−3 săpt.**
Fără asta **TRL 3 nu poate fi atestat** (Anexa 18 cere măsurători inițiale de laborator; simularea doar completează) → risc de **respingere**, nu doar puncte pierdute la Grila 2.3b. Până atunci scriem „TRL 3 — de atestat după D8”, iar Anexa 16 are mesajul „NU SE SEMNEAZĂ”.
- [ ] Placa **Waveshare ESP32-S3-Touch-LCD-2.8C** e comandată. Când vine, cumperi și **bateria LiPo 803450, 1500 mAh** (cu mufă MX1.25), un microfon INMP441 și un amplificator MAX98357 + difuzor mic, plus o tablă de aluminiu de 1,5 mm. **Din banii tăi. Nu intră în buget.** Păstrezi facturile.
- [ ] **Încarci firmware-ul 1.8.0** (`firmware/release/`) și urmezi `firmware/BRINGUP.md`. Îmi trimiți ce vezi (ecran, touch, giroscop, BLE).
- [ ] Rulăm împreună testele **X1–X8**: ochii pe placă, fps, touch, tastare cu 5 persoane, comenzi offline, un tur Claude cu cheia ta de test, BLE prin aluminiu, consum.
- [ ] **Filmezi fiecare test pe placa reală**, cu data vizibilă. Fără montaj.
- [ ] Semnezi „Raportul de laborator TRL 3” (îl scriu eu din măsurătorile tale). Abia apoi trec `D8_DONE = True` în `draft/_build/data.py` și refac drafturile; textele trec automat pe „atestat”.

## Pasul 4 — Expertul științific · **contactezi acum; contract la T−5 săpt.; raport semnat la T−2 săpt.**
Condiții: criteriul aprobat prin **Anexa 1 la Decizia CM PR BI nr. 54/29.09.2026** cere **≥ 5 ani** în domeniu **plus** (**≥ 2 articole** în ultimii 10 ani **SAU** o calificare/certificare/rezultat relevant). Ghidul din consultare cerea toate trei cumulativ. **Ținta sigură, până apare ghidul final: toate trei** (≥ 5 ani · ≥ 2 articole · o certificare/acreditare); minimul acceptat: 5 ani + una din celelalte două. Reverificăm pe ghidul final. **Să nu fie și coordonatorul echipei.** Costul e eligibil și se poate plăti înainte de depunere.
- [ ] Cauți pe paginile de departament (CV cu publicații):
  - **UPB – Electronică (ETTI)**: dispozitive și circuite electronice, electronică aplicată, telecomunicații (RF/antene);
  - **UPB – Automatică și Calculatoare (ACS)**: sisteme embedded, interacțiune om–calculator;
  - **IMT București** (microtehnologie, senzori, RF-MEMS);
  - **ICI București** (AI, IoT, securitate cibernetică);
  - rezervă: **ICIA/RACAI** (AI, limba română).
- [ ] Trimiți e-mailul-model (îl scriu eu): ce e SOUL, ce cerem (citește raportul, 2–3 întâlniri, semnătură), onorariul, termenul.
- [ ] Ceri: CV Europass semnat, lista publicațiilor cu DOI, copii ale certificărilor, dovada vechimii.
- [ ] Îl întrebi și de o **scrisoare de colaborare** a laboratorului (acces la camera anecoică, ajutor la antenă, recrutarea studentului).
- [ ] Numele expertului intră în Anexa 16: **[de completat]**.

## Pasul 5 — Echipa, numită la depunere · **până la T−3 săpt.**
- [ ] **Coordonator tehnic/științific**: embedded/electronică, **≥ 5 ani** (ideal doctor), ~50 h/lună, **34 €/h brut**. **[de completat: nume]**
- [ ] **Inginer embedded/firmware**: facultate în domeniu, **≥ 2 ani**, ~80 h/lună, **25 €/h brut**. **[de completat: nume]**
- [ ] **Student ≤ 24 de ani**, înmatriculat (UPB ETTI/ACS), ~60 h/lună, **12 €/h brut**. Adeverință de student 2026–2027 + copie CI. **[de completat: nume]**
- [ ] **Tu**: CV Europass (manager de proiect + munca de cercetare la SOUL din sept. 2026).
- [ ] Toți semnează **CV-ul, fișa de post și o declarație de disponibilitate**.

## Pasul 6 — Scrisori de intenție (minim 2, ideal 3–4) · **până la T−3 săpt.**
Modelul e gata: `draft/Scrisoare_de_intentie_MODEL.docx` (variante A, B, C). Contează **doar** scrisorile cu **toate cele 7 elemente**, de la **firme diferite**, datate cu **cel mult 6 luni** înainte de depunere. KREA și MundiShop nu contează (sunt tot ARTEMIS).
- [ ] un **magazin sau distribuitor** de gadgeturi/design (varianta A) — **[de completat]**;
- [ ] un **laborator universitar** (varianta B; poate fi același cu expertul) — **[de completat]**;
- [ ] o **firmă de software** din București care folosește Claude Code (varianta C, pilot cu 3–5 oameni) — **[de completat]**;
- [ ] (rezervă) un hub de inovare / living lab sau o asociație a persoanelor cu dizabilități — **[de completat]**.

Ce scrie despre SOUL în scrisoare (deja în model): obiect de ~63 × 71 × 23 mm din aluminiu (SOUL S), ecran rotund AMOLED de 1,75″ (466×466), ochi vii, tastatură rotundă; merge offline sau cu AI-ul conectat de proprietar (Claude, cu contul/cheia proprie; în curând ChatGPT, cu cheie proprie — în lucru); **SOUL nu include AI**; baterie înlocuibilă.

## Pasul 7 — Ofertele (2 pe fiecare linie) · **cereri la T−5 săpt., toate la T−2 săpt.**
**Doar cereri de ofertă, fără comandă.** Eu scriu e-mailurile. Tu le trimiți și îmi dai PDF-urile. Lista liniilor e în `01-DOCUMENTE.md` §C:
- [ ] aparate de măsură: osciloscop, analizor de spectru, analizor de consum, cutie ecranată, PC, imprimantă SLA (câte 2);
- [ ] materiale (SOUL S, `docs/12-SIZE-S.md` §3): plăci de dezvoltare Waveshare ESP32-S3-Touch-AMOLED-1.75, panouri AMOLED 1,75″ goale (Tailor-Pixels / NoseDisplay / Lianxun), microfoane MEMS + difuzoare, celule LiPo 603040 de 750 mAh, componente (capturi din 2 magazine). Plăcile 2.8C nu intră în buget: sunt prototipul M, din bani proprii;
- [ ] **CNC + anodizare** carcase MĂRGĂRITAR (3 / 5 / 15 seturi; trimitem STEP-ul);
- [ ] **PCB propriu** fabricare + asamblare (2 firme);
- [ ] **pre-testare EMC/RF** (un laborator RO + unul UE) și **evaluare EN 18031** (2);
- [ ] serviciu CDI pentru antenă (universitate + firmă RF);
- [ ] workshop-uri de testare; SaaS (capturi de prețuri); consilier PI (2 cabinete); revista open-access (2 capturi de APC); conferință; customer discovery; expert; audit; panou de vizibilitate.
- [ ] Taxele EUIPO au o singură sursă (taxa oficială): scriu eu nota justificativă.

## Pasul 8 — Proprietatea intelectuală · **până la T−4 săpt.**
- [ ] Căutare **TMview** și **DesignView** pentru „SOUL” (clasele 9, 42, 14, 28). Risc mare de conflict. Eu îți fac lista de rezultate.
- [ ] Decizi dacă depui **marca** acum prin **EUIPO SME Fund** (voucher 75 %, termen **04.12.2026** [de verificat pe site-ul EUIPO]). Dacă da, marca **nu** mai intră în bugetul PoC.
- [ ] **Data primei publicări (din git, verificată 12.10.2026):** depozitul `github.com/KREA123/obsidian-vault` e **public de la crearea lui, pe 24.09.2026**. Randările sunt acolo din **24.09.2026** (MĂRGĂRITAR v9 din **26.09.2026**); decodorul tastaturii și conceptul ferestrei radio din **25.09.2026**. Dacă randările au apărut mai devreme și pe site sau pe rețele, îmi spui data: **[de completat, doar dacă e mai devreme]**.
- [ ] **Designul MĂRGĂRITAR se depune înainte de 24.09.2027** (grația de 12 luni). Contractul vine abia în aug.–oct. 2027, deci **nu** așteptăm proiectul: îl depui **acum prin EUIPO SME Fund** (împreună cu marca) sau **imediat după depunerea CF**, din banii firmei. Nu intră în bugetul PoC.
- [ ] **Decizi: facem depozitul GitHub privat, inclusiv dosarul?** Ce s-a publicat rămâne publicat, dar oprim divulgarea lucrului nou (PCB, măsurători RF, designul rev B). Metoda de decodare și fereastra radio nu le mai revendicăm ca brevet sau secret: sunt publice. **[de completat: decizia]**

## Pasul 9 — Cesiunea drepturilor · **până la T−3 săpt.**
- [ ] Citești `draft/Declaratie_cesiune_drepturi_MODEL.docx`: tu cedezi gratuit către ARTEMIS codul, designul, CAD-ul, ochii, brandul.
- [ ] Îmi spui ce e deja public open source (ex. SOUL Bridge, MIT). Cesiunea respectă licențele deja date. Restul depozitului e vizibil public, dar fără licență open-source (toate drepturile rezervate).
- [ ] **Un avocat** o verifică (5 puncte din caseta roșie). Apoi o semnezi, cu dată **anterioară depunerii**.

## Pasul 10 — Documentele finale · **T−2 săpt. … T**
- [ ] Contabilul: **bilanțul 2025** (F10/F20/F30/F40 + recipisa) și **Anexa 7** (IMM).
- [ ] Semnezi politica de egalitate de șanse (o scriu eu).
- [ ] Citești și aprobi **Planul de afaceri (Anexa 3)** și **Raportul științific (Anexa 16)** din `draft/`. Expertul semnează Anexa 16.
- [ ] **Certificatul constatator** pentru depunere: cerut cu **cel mult 30 de zile** înainte, **după** ce s-au adăugat codurile CAEN.
- [ ] CI valabil.
- [ ] Semnezi electronic toate PDF-urile. Le încărcăm împreună. **Depunem.**

## Pasul 11 — După depunere
- [ ] Răspunzi la clarificări **la timp** (la contractare: max. 15 zile lucrătoare).
- [ ] Anunți AM PR BI în **5 zile lucrătoare** despre orice schimbare (ghid p. 35).
- [ ] La contractare (15 zile lucrătoare): certificate fiscale (stat + Sectorul 3), cazier fiscal, contractul de spațiu, decizia asociatului, Anexele 5, 13, 14. Le pregătim din timp.
- [ ] Orice ajutor de minimis nou (ex. EDIH) îl declari **înainte** de semnarea contractului.
- [ ] Dacă evaluarea trece în 2027: contabilul depune **imediat** bilanțul 2026, altfel evaluarea se oprește.

---

### Pe scurt, ce îmi trimiți în următoarele 10 zile
1. Certificatul constatator cu istoric.
2. Bilanțul 2025 și lista firmelor tale (cu procentele).
3. Lista ajutoarelor de minimis (de la contabil, din RegAS).
4. Confirmarea: zero datorii.
5. Ce alegi pentru loc: apartamentul (A) sau un spațiu închiriat (B).
6. Data la care vine placa 2.8C.
7. Primele 2–3 nume de experți pe care îi contactezi.
8. Decizia despre depozitul GitHub (rămâne public sau devine privat) și dacă depui designul + marca acum prin SME Fund.
