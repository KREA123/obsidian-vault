---
tip: finanțare
proiect: SOUL-PoC
rol: autoverificarea draft-urilor Anexa 3 + Anexa 16 + modele, față de Grila ETF (Anexa 10)
actualizat: 2026-10-12
stare: draft 3 (12.10.2026, după verificarea dosarului); de citit de Andu; Anexa 16 NU se semnează până la D8
---

# REVIEW · Autoverificare pe Grila ETF

**Fișiere din `dosar/draft/`:**

| Fișier | Ce este | Pagini (PDF, LibreOffice) |
|---|---|---|
| `Anexa_3_Plan_Afaceri_SOUL_DRAFT.docx` + `out_a3.pdf` | modelul oficial Anexa 3 completat secțiune cu secțiune | 34 |
| `Anexa_16_Raport_Stiintific_SOUL_DRAFT.docx` + `out_a16.pdf` | modelul oficial Anexa 16 completat, gata de revizuirea expertului; **nu se semnează până la D8** | 24 |
| `Scrisoare_de_intentie_MODEL.docx` + `.pdf` | ghid + 3 variante de o pagină (A retailer/distribuitor, B laborator universitar, C utilizator pilot), fiecare cu cele 7 elemente din Grila 4.2 | 4 |
| `Declaratie_cesiune_drepturi_MODEL.docx` + `.pdf` | contract de cesiune gratuită Andu → ARTEMIS (cod, design, CAD, ochi, brand) + inventar + componentele open-source. **⚠ De revizuit de un avocat** | 3 |

**Cum se refac.** Totul se generează din `_build/data.py` (aceleași date ca `03-NUCLEU-PROIECT.md`). Comanda: `bash _build/build.sh` (copiază șabloanele oficiale din `apel/`, rulează `build_a3.py`, `build_a16.py`, `build_models.py`, apoi LibreOffice → PDF). Șabloanele oficiale au fost editate direct: structura, titlurile, numerotarea, tabelele, antetul și subsolul au rămas cele din model. S-au șters doar instrucțiunile (✏), sfaturile (✔) și secțiunea „Ghid de utilizare”. Avertismentele (⚠) au rămas. Tot ce nu știm e marcat **[între paranteze, cu fundal galben]**.

## Ce s-a schimbat la 22.10.2026: produsul e mărimea S
Decizia din 20.10.2026 (`03 Decizii/Jurnal decizii.md`): **produsul final e SOUL S** — forma MĂRGĂRITAR, **~63 × 70,8 × 23 mm**, sticlă plată Ø52, afișaj rotund **AMOLED 1,75″ 466×466**, placa de dezvoltare **Waveshare ESP32-S3-Touch-AMOLED-1.75** (2 microfoane, ES7210 + ES8311, difuzor, AXP2101), baterie **LiPo 750 mAh (603040)**, autonomie **~27 h [estimare]** (`docs/size-s.json`, `docs/12-SIZE-S.md`). În Anexa 3, Anexa 16, scrisoarea de intenție și cesiune: ipoteza, O1, A2/A4, R1/R2, H1/H2/H5, P2/P9, D5/D6, N1, bugetul de materiale (linia 11, aceeași sumă, defalcare refăcută [E]) și arhitectura sunt acum pe S. **SOUL M** (placa 2.8C, ~90 × 101 × 31,5 mm, 1500 mAh) rămâne **doar prototipul de banc** pentru dovada TRL 3 (D8, X1–X8) și e etichetat așa peste tot. Punctele 2 și 6 de mai jos sunt istorice.

## Ce s-a schimbat la 12.10.2026 (față de draftul din 25.09)
1. **Firma:** CUI 53145290, J2025098748009, EUID, data înregistrării 17.12.2025, sediul din Sector 3, CAEN 7311 + codurile de adăugat, neplătitoare de TVA — completate în Anexa 3 §2.1, Anexa 16, scrisori și cesiune.
2. **Produsul (istoric, înlocuit la 22.10.2026 de mărimea S):** forma MĂRGĂRITAR, ~90 × 101 × 31,5 mm, 5 culori; placa ESP32-S3-Touch-LCD-2.8C (ESP32-S3R8, 8 MB PSRAM, 16 MB flash), QMI8658, RTC, buzzer, microfon + difuzor I²S opționale, **LiPo 1500 mAh** (în loc de 2500–3000 mAh și codecul ES8311/ES7210).
3. **Software:** firmware **SoulOS 1.8.0** (198+ teste native, fără avertismente; „Alive” 1.9.0 în lucru), **SOUL Cloud** (283 de teste), SOUL Bridge (open source), SOUL Memory, comenzi vocale offline EN (ESP-SR) — în locul „61/61 teste” și „serviciul AI suflet_ai 49/49”.
4. **AI:** fiecare proprietar își conectează **propriul AI**; SOUL nu include și nu revinde AI. Ipoteza H3 și protocoalele P5–P7 s-au schimbat: **latența unui tur AI** (nu latența vocală prin server UE), comenzi offline scrise + vocale, **memoria păstrată la schimbarea AI-ului**. Pragurile numerice au rămas aceleași.
5. **Comercial:** preț **de la 249 €**, fără ediție Founders, doar listă de așteptare, fără CE azi, prima serie 10–25 buc. după proiect. Riscul R10 a devenit „redus” (decizia e luată). Proiecția pe 5 ani a fost refăcută (`_build/proj.py`): fără venituri din AI/abonamente, preț net 249 → 219 €.
6. **H5:** ținta „≥ 7 zile standby” a fost scoasă (nu e susținută cu 1500 mAh); rămâne **≥ 24 h** în profil tipic (estimarea de azi ≈ 32 h [E], `docs/09` §3).

## Corecturi după verificarea dosarului (12.10.2026, draft 3)
1. **TRL 3 declarat, nu atestat.** Anexa 18 cere măsurători inițiale de laborator; D1–D7 sunt analitice/software. Anexa 16 §2.1, §2.2 (rândul TRL 3), §2.4, datele generale și Anexa 3 (antet, §1.1, §4.2) spun acum „TRL 3 — **de atestat după D8**”, fără „ATINS” și fără „în laborator”. **Poarta de lansare** în `_build/data.py`: `D8_DONE = False` pune pe Anexa 16 mesajul roșu „NU SE SEMNEAZĂ ȘI NU SE DEPUNE”, iar `SOUL_FOR_SIGNATURE=1 bash _build/build.sh` se oprește cu eroare. Când raportul D8 există, `D8_DONE = True` readuce automat formularea „atestat”.
2. **IP: depozitul vault e public** (GitHub, din 24.09.2026). Data primei publicări e completată din git (randări 24.09.2026, MĂRGĂRITAR v9 26.09.2026, decodorul tastaturii și fereastra radio 25.09.2026). Designul MĂRGĂRITAR se depune **înainte de 24.09.2027** (SME Fund acum sau imediat după depunerea CF, în afara bugetului); O4, A6, R3, IE-M, Anexa 3 §3.4/§6.2, Anexa 16 §6.4 și `03-NUCLEU` §14 nu mai spun „design ≤ L5”. Brevetul și secretul comercial se limitează la ce nu e public; „motorul ochilor poate fi publicat open-source după IP” a fost scos. Întrebare pentru Andu: depozitul devine privat?
3. **Decembrie — o singură regulă** în `00` și `04`: ghidul final cel târziu pe ~1 decembrie (MySMIS ~31 decembrie); realist, până la începutul lui noiembrie [estimare].
4. **Expertul:** citată **Decizia CM PR BI nr. 54/29.09.2026** (a + (b sau c)) în `00` (rândul 0, E4, respingeri), `01`, `02`, `04` și în Anexa 16; ținta sigură rămâne a + b + c.
5. **TVA în proiecție:** 249 € e preț de listă **cu TVA**; `proj.py` calculează veniturile **fără TVA** (÷ 1,21, ≈ 206 € net), cu trecerea la plătitor de TVA și OSS în Ipoteza 1, Ipoteza 6 și R6.
6. **Anexa 3 §1.4** scurtată la ~½ pagină: tabelul N1–N5 mutat în §4.3.
7. **ChatGPT** nu mai e prezentat ca funcțional: scrisorile (A, B, C), Anexa 3 §1.1/§1.4/§3.5/SWOT/§4.1/§4.3 și Anexa 16 §1.3/§1.5 spun „Claude, cu contul sau cheia proprie; în curând și ChatGPT, cu cheie proprie — în lucru”. H3, N3 și P6/P7 rămân ținte de cercetare.
8. **Anexa 3 §2.2:** activitatea CD SOUL a fost realizată de fondator din 24.09.2026 și e transferată prin cesiune; ARTEMIS o continuă (CAEN 7210 de adăugat). Aceeași formulare în `02` (3.2a).
9. **Linia 18 împărțită:** 18a SaaS (API AI pentru teste + CAD, 3.800 €) și 18b infrastructură cloud de test în UE (1.200 €, folosită doar în validare) — totalul neschimbat; întrebare la helpdesk în `04` Pasul 2.

## 1. Scor pe subcriterii (evaluarea draft-urilor, nu a dosarului complet)

Legendă: **Complet** = textul acoperă tot ce cere grila · **Parțial** = punctajul depinde de un document sau de un nume care lipsește · **0** = nu se poate puncta încă.

### 1. Contribuția la OS 1.1 (40)
| Sub | Max | Stare | Ce lipsește | Estimare |
|---|---|---|---|---|
| 1.1 RIS3 (≥ 2 domenii) | 5 | **Complet*** | *subdomeniile exacte din RIS3 BI (Cl) | 5 |
| 1.2 Relevanța problemei | 15 | **Complet** | punctajul real ține de dovezile pe hardware (D8) | 10–15 |
| 1.3 Sediu în BI ≤ 31.12.2025 | 5 | **Complet** | firma e înregistrată la 17.12.2025 în Sector 3; se dovedește prin certificatul constatator (≤ 30 de zile) | 5 |
| 1.4 Publicare OA | 10 | **Complet*** | *revista țintă nenumită încă (Cl + captura APC) | 10 |
| 1.5 Economie circulară | 5 | **Complet** | – | 5 |

### 2. Calitatea documentației (37)
| Sub | Max | Stare | Ce lipsește | Estimare |
|---|---|---|---|---|
| 2.1a Piață + grup țintă | 2 | Complet | – | 2 |
| 2.1b Etape | 2 | Complet | – | 2 |
| 2.1c Poziționare | 2 | Complet | – | 2 |
| 2.1d IP | 5 | Complet* | *depozitul public din 24.09.2026: designul MĂRGĂRITAR înainte de 24.09.2027; mai puternic cu căutarea TMview/DesignView atașată | 4–5 |
| 2.1e Riscuri + eșec de cercetare | 4 | Complet | – | 4 |
| 2.2a Încadrarea liniilor + praguri | 2 | Complet* | *reverificare pe Anexa 20 finală și la helpdesk (CNC/PCB) | 1–2 |
| 2.2b ≥ 2 surse pe linie | 3 | **0 azi** | ofertele | 0 → 3 |
| 2.2c Salarii ≤ HG 1188 | 2 | Complet | – | 2 |
| 2.3a Problemă, ipoteză, obiective | 3 | Complet | – | 3 |
| 2.3b TRL 3 cu dovezi | 2 | **Parțial — risc de eligibilitate** | placa e comandată, netestată; lipsesc X1–X8 + video pe placa reală. Fără D8, TRL 3 nu poate fi atestat (respingere) | 1 → 2 |
| 2.3c Activități TRL 4–5 | 3 | Complet | – | 3 |
| 2.3d Resurse pentru TRL superior | 3 | **Parțial** | scrisori de la laborator universitar/EMC, oferte | 1,5 → 3 |
| 2.3e Plan de lucru | 2 | Complet | – | 2 |
| 2.3f Ipoteze, indicatori | 2 | Complet | – | 2 |

### 3. Capacitatea de implementare (9)
| Sub | Max | Stare | Ce lipsește | Estimare |
|---|---|---|---|---|
| 3.1 Echipa nominalizată | 5 | **0 azi** | coordonator (≥ 5 ani / doctor) + inginer (≥ 2 ani), cu CV și dovezi | 0 → 5 |
| 3.2a Experiența CDI a firmei | 2 | **Parțial** | firmă înregistrată la 17.12.2025, CAEN principal de publicitate; avem doar dovezile SOUL din sept.–oct. 2026 (raport tehnic semnat + anexe) | 1 |
| 3.2b Încă un membru cu experiență CDI | 2 | Parțial | CV-ul lui Andu cu activitatea CD SOUL sau un al doilea inginer | 1–2 |

### 4. Sustenabilitate și teme orizontale (14)
| Sub | Max | Stare | Ce lipsește | Estimare |
|---|---|---|---|---|
| 4.1 Strategie post-PoC | 5 | Complet | contabilul completează „alte venituri” | 5 |
| 4.2 ≥ 2 scrisori valide | 4 | **0 azi** | scrisorile semnate (modelul e gata) | 0 → 4 |
| 4.3a Tânăr ≤ 24 ani | 3 | Parțial | studentul + adeverința 2026–2027 | 0 → 3 |
| 4.3b Măsură suplimentară | 2 | Complet | politica internă semnată | 2 |

### Total
| | 1 (40) | 2 (37) | 3 (9) | 4 (14) | **Total** |
|---|---|---|---|---|---|
| **Draft-urile azi** | 35–40 | 30,5–31,5 | 2–3 | 7 | **≈ 75–82** |
| **Cu tot ce e în `04-CE-TREBUIE-SA-FACA-ANDU.md`** | 37–40 | 33–36 | 6–8 | 13–14 | **≈ 89–98** (realist ~91, cu subiectivitatea evaluatorilor) |

**Pe scurt:** textul acoperă integral 19 din 26 de subcriterii. Celelalte 7 (2.2b, 2.3b, 2.3d, 3.1, 3.2, 4.2, 4.3a) depind de **documente și nume**, nu de redactare.

## 2. Placeholder-ele rămase și cine le completează

**A** = Andu · **Ct** = contabilul · **E** = expertul · **Cl** = Claude · **M** = membrii echipei · **F** = parteneri/furnizori · **Av** = avocat

### Anexa 3 (54 de marcaje)
| Unde | Placeholder | Cine |
|---|---|---|
| antet, semnătura | data completării / data semnării | A |
| §2.1 | locul de implementare (apartamentul e adecvat sau spațiu închiriat în BI) | A |
| §2.1 | codurile CAEN de adăugat (verificare pe CAEN Rev.3) | Ct |
| §2.1 | capital social, acționariat, număr mediu de angajați, categoria IMM (Anexa 7) | Ct / A |
| §2.1, declarația | numele complet al reprezentantului legal | A |
| §1.3, §2.4 | confirmarea „fără proiecte anterioare cu finanțare europeană” | A |
| §1.3, §5.2, §5.3 | numele coordonatorului, inginerului, studentului + CV/diplome/adeverință | A + M |
| §2.2 | 2–3 fraze cu cifre despre KREA/MundiShop | A |
| §2.3 | semnarea cesiunii; licența ESP-SR | A (+ Av); Cl |
| §2.3 (D1) | exportul logurilor + hash-ul git la depunere | A + Cl |
| §2.5 | organizația de cercetare, laboratorul EMC/RF, asociația, expertul; scrisori/oferte | A + F |
| §4.1 | subdomeniile RIS3 BI | Cl |
| §4.4 | suprafața, dreptul de folosință | A |
| §4.7 | spațiul de minimis în RegAS | Ct |
| §5.1 | politica de egalitate de șanse; scutirea de impozit CD | A; Ct |
| §5.3 | CIM pentru administrator sau serviciu extern | Ct |
| §6.2 | decizia despre depozitul public; revista OA + captura APC (data primei publicări e completată din git: 24.09.2026) | A; Cl |
| §6.3 | „alte venituri” An 1–5; regimul fiscal | Ct |

### Anexa 16 (67 de marcaje)
| Unde | Placeholder | Cine |
|---|---|---|
| date generale | tipul de expert (independent sau colectiv) | A + E |
| identificarea expertului, semnături | nume, afiliere, domeniu, dovezile a) b) c); semnătura și data | **E** |
| §1.2 | validarea bibliografiei | **E** |
| §1.3 | subdomeniile RIS3 BI | Cl |
| §2.2, §2.3 (D8), §6.3, X1–X8 (×10 „în curs”) | rezultatele X1–X8 pe placa reală + raportul TRL 3 + video | **A + Cl** |
| §2.3 (D1), §7.2 | exportul git + hash-ul | A + Cl |
| §2.3 | cesiunea semnată | A (+ Av) |
| §4.1–4.2 | spațiul; laboratorul EMC/RF; partenerii + documentele lor | A + F |
| §4.2, §5.4 (×9 „[Nume]”) | coordonator, inginer, student | A + M |
| §6.4 | revista țintă | Cl |
| VIII | semnătura solicitantului + data | A |

### Modele
- **Scrisoarea de intenție:** se completează de fiecare emitent (antet, număr, dată ≤ 6 luni înainte de depunere, reprezentant legal, CUI, contact, semnătură). Datele ARTEMIS sunt deja completate.
- **Cesiunea:** datele lui Andu (CNP, CI, domiciliu), data (anterioară depunerii), hash-urile commit-urilor, ce e deja public open source (SOUL Bridge, MIT), licențele dependențelor Python/Node și ESP-SR. **Av** verifică cele 5 puncte din caseta roșie.

## 3. Cerințe din ghid pe care încă nu le îndeplinim
1. **Dovezile TRL 3 pe hardware** (Anexa 16 §II; Grila 2.3b): placa e comandată, netestată. **Fără D8, TRL 3 nu poate fi atestat** — poarta `D8_DONE` blochează semnarea Anexei 16.
2. **Expertul** eligibil (Decizia CM 54/29.09.2026: a + (b sau c); ținta sigură a + b + c) care semnează Anexa 16 — lipsă (fără el: respingere).
3. **Echipa nominalizată** (Grila 3.1, 4.3a) și **CV + fișe de post** pentru toate pozițiile (§7.4 poz. 4).
4. **≥ 2 surse pe linie** (Anexa 19 + oferte) — Anexa 19 nu o avem încă.
5. **≥ 2 scrisori de intenție** valide (Grila 4.2).
6. **Locația adecvată** (§5.2.1 XII): sediul e un apartament — de lămurit.
7. **Codurile CAEN** pentru CD (Anexa 3 §2.1 le cere) — de adăugat.
8. **Verificările firmei:** RegAS/de minimis, IMM cu firmele legate, zero datorii, nicio schimbare de asociați după 03.06.2026.
9. **Cesiunea drepturilor** semnată înainte de depunere.
10. **Anexele 19, 20 și ghidul final** nu sunt publicate; bugetul se reverifică pe ele (inclusiv linia 18b).
11. **Designul MĂRGĂRITAR** se depune înainte de 24.09.2027 (depozitul GitHub e public din 24.09.2026), în afara bugetului.
