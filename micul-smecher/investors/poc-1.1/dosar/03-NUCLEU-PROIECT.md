---
tip: finanțare
proiect: SOUL-PoC
rol: SURSA UNICĂ DE ADEVĂR pentru CF, Anexa 3 (Plan de afaceri), Anexa 16 (Raport științific), Anexa 19, CV-uri, fișe de post, Anexa 13
actualizat: 2026-09-25
stare: draft 1, de confirmat de Andu; de reverificat pe ghidul final
---

# 03 · Nucleul proiectului SOUL-PoC

> **Regula de corelare.** Orice cifră, denumire, lună, obiectiv sau indicator din CF, Planul de afaceri și Raportul științific se copiază **de aici**. Dacă se schimbă ceva, se schimbă **întâi aici**. Anexa 3 și Anexa 16 avertizează că discrepanțele se depunctează.
>
> **Regula de vocabular.** SOUL se descrie ca **„dispozitiv tangibil de interacțiune om–mașină / asistent personal AI”**. **Nu** folosim „companion emoțional”, „prieten pentru singurătate” sau „consiliere” (§5.3.3 p. 61 exclude serviciile de consiliere psihologică și de „stabilire a întâlnirilor”). Nu scriem „AI revoluționar”: grila 1.2 nu punctează afirmațiile generice despre AI/IoT.
>
> **Mărimea M** este decizia în vigoare (Jurnal decizii, 25.09.2026). `docs/00-START-HERE.md` încă descrie S (1,75″). În dosar folosim **doar M**.

---

## 1. Identificare

| Câmp | Valoare |
|---|---|
| Solicitant | ARTEMIS DIGITAL S.R.L., București (brand KREA; MundiShop), neplătitoare de TVA, micro-IMM (de confirmat) |
| Reprezentant legal | Andu (administrator) |
| Acronim | **SOUL-PoC** |
| **Titlu RO** | **SOUL — dispozitiv AI tangibil, local-first, cu interfață circulară și carcasă reparabilă din aluminiu: validarea modelului conceptual de la TRL 3 la TRL 5** |
| **Titlu EN** | **SOUL — a tangible, local-first AI interaction device with a circular interface and a repairable aluminium enclosure: proof of concept from TRL 3 to TRL 5** |
| Tip inovare | **inovare de produs** (bun fizic + firmware + serviciu software asociat) |
| TRL pornire → țintă | TRL 3 → **TRL 5** (TRL 4 = rezultat intermediar, poarta IE2) |
| Durata implementării | **24 de luni** (L1 = luna semnării contractului; estimat sept.–oct. 2027 → sept.–oct. 2029) |
| Locație | sediul social ARTEMIS, București (spațiu de birou + laborator electronic) |
| Valoare totală eligibilă = nerambursabilă | **191.308 €** (100 %), de minimis |

---

## 2. Domenii RIS3 BI (Grila 1.1, 5 p.)

Declarăm **două** domenii, argumentate pe obiective, activități și rezultate (nu pe CAEN, §5.2.1 XIV p. 47–48):

1. **Tehnologia Informației și Comunicațiilor (TIC).** Firmware embedded (C++17) pentru randare SDF în timp real; tastatură circulară cu decodare probabilistică; arhitectură AI hibridă local-first (parser offline RO/EN + modele de limbaj la alegerea utilizatorului prin tool-calling, conector MCP); flux vocal în timp real (Opus/WebSocket, servere UE); securitate cibernetică conform EN 18031 (BLE LE Secure Connections, OTA semnat, secure boot). Rezultate: firmware SoulOS, serviciul AI, protocoalele și datele de validare.
2. **Sisteme și Componente Inteligente.** Un sistem ciber-fizic integrat: ESP32-S3, afișaj rotund IPS 480×480, touch capacitiv, IMU, microfoane MEMS, PMU, baterie înlocuibilă și antenă BLE/Wi-Fi integrată într-o carcasă CNC din aluminiu cu fereastră radio polimerică. Rezultate: PCB propriu, arhitectura electromecanică, măsurătorile RF/energie/EMC.

*Opțional, de discutat cu expertul:* **Industrii Culturale și Creative** (designul industrial al obiectului, limbajul expresiv al ochilor). Doar dacă argumentul e solid; două domenii bine argumentate sunt suficiente pentru 5 puncte.

**De făcut (Claude):** citez **subdomeniile exacte** din documentul RIS3 BI 2021–2027 (adrbi.ro) după ce descărcăm strategia. Nu inventăm denumiri de subdomenii.

---

## 3. Problema, ipoteza, inovarea

### 3.1 Problema (relevanță europeană/internațională — Grila 1.2, 15 p.)
Accesul la asistenții AI generativi e captiv în telefon și în ecranul computerului. Încercările de dispozitive AI dedicate au eșuat din motive **tehnice și de arhitectură**, nu de cerere:
- **Dependența de cloud:** Humane AI Pin a fost oprit la distanță pe 28.02.2025, iar dispozitivele au devenit deșeu. Moxie s-a oprit în dec. 2024, odată cu serverul (research 04, 11).
- **Latența:** BubblePal e criticat pentru 10–15 s de așteptare, iar Rabbit r1 a ajuns la ~5 % utilizatori zilnici (research 04).
- **Interfața:** pe ecranele mici, rotunde, introducerea de text rămâne o problemă deschisă de cercetare HCI (literatură: C-QWERTY, COMPASS; §3.4).
- **Închiderea ecosistemului:** asistentul e legat de un singur furnizor și de un abonament obligatoriu (Humane: $24/lună).
- **Reparabilitatea și deșeurile electronice:** din **18.02.2027**, bateriile din aparatele portabile trebuie să poată fi **îndepărtate și înlocuite de utilizator** (Reg. (UE) 2023/1542, art. 11). Directiva (UE) 2024/1799 introduce „dreptul la reparare”, iar Delegated Reg. (UE) 2022/30 + EN 18031 impun securitate cibernetică echipamentelor radio conectate. AI Act (Reg. (UE) 2024/1689, art. 50) cere transparență din 02.08.2026.

Efectul: **un segment global în creștere** (Plaud > 2 M dispozitive; Fuzozo ~300 k; campanii de 0,3–3 M$ pentru dispozitive companion — research 01, 04, 11) e servit de produse care fie **nu fac nimic util** (obiectele expresive fără AI), fie **nu supraviețuiesc** firmei care le-a făcut (cele dependente de cloud). **Niciun produs analizat nu combină** față expresivă + obiect premium reparabil + AI la alegerea utilizatorului + acțiuni utile + funcționare offline (research 11 §1). Problema e **europeană**: Muse (Meta) e doar în SUA, Alexa+ nu există în română, iar Limitless s-a retras din UE (research 11).

**Dovezile se atașează** (Grila 1.2 cere surse verificabile): rapoarte și articole de presă cu link și dată, textele regulamentelor UE, benchmark-ul celor 24 de competitori (research 11), ≥ 3 publicații științifice recente (§3.4).

### 3.2 Ipoteza de cercetare (Anexa 16 §1.1, formularea „dacă…, atunci…”)
> **Dacă** un dispozitiv de 90 × 103 × 31 mm cu afișaj rotund de 2,8″ integrează (i) un motor de randare SDF optimizat pentru un microcontroler ESP32-S3, (ii) o tastatură QWERTY circulară cu decodare probabilistică, (iii) o arhitectură AI hibridă local-first cu degradare controlată și (iv) o carcasă din aluminiu cu fereastră radio polimerică și baterie înlocuibilă, **atunci** sistemul poate atinge simultan, în mediu relevant, **≥ 30 fps** la animație, **≥ 20 cuvinte/min** la tastare, latența vocală **p50 ≤ 1,5 s**, **≥ 90 %** comenzi executate corect fără internet, atenuare RF prin carcasă **≤ 6 dB** și **≥ 24 h** de autonomie în profil tipic.

Sub-ipotezele H1–H5 sunt în §7.

### 3.3 Ce e nou (elemente de diferențiere verificabile)
| # | Element | Stadiul actual / competitori | Contribuția SOUL-PoC (măsurabilă) |
|---|---|---|---|
| N1 | Randare SDF anti-aliased a „ochilor” parametrici pe MCU, pe un panou RGB 480×480 fără memorie proprie (framebuffer în PSRAM) | competitorii folosesc animații pre-randate (sprite-uri) sau SoC-uri scumpe | ≥ 30 fps cu Wi-Fi + BLE active; 24 de reacții procedurale; personalitate derivată din ID-ul cipului |
| N2 | Round QWERTY cu tastele de la margine „stăpâne” pe bordură, decodare probabilistică, diacritice RO automate | smartwatch-uri: 10–30 WPM în literatură; fără suport RO | ≥ 20 WPM, UER ≤ 3 %, diacritice automate |
| N3 | Arhitectură „un singur set de acțiuni, trei moduri” (fără AI / Claude / ChatGPT), fallback local, conector MCP, cheie proprie criptată | dispozitivele au un singur furnizor, au cloud obligatoriu sau merg doar offline | ≥ 90 % succes offline; continuitate 100 % la căderea rețelei |
| N4 | Carcasă CNC din aluminiu cu antenă prin fereastră polimerică în talpă + încărcare prin pini în capsula OU | carcasele metalice blochează RF; obiectele premium nu au AI | atenuare ≤ 6 dB; legătură BLE ≥ 10 m |
| N5 | Reparabilitate de la proiectare: baterie schimbabilă de utilizator (Torx), fără adeziv pe celulă, componente modulare, OTA | multe gadgeturi au baterii lipite/nedemontabile | înlocuire ≤ 5 min de către utilizatori neexperți |

### 3.4 Surse științifice (Anexa 16 cere ≥ 3 din ultimii 5 ani) — de verificat DOI înainte de citare
- Text pe smartwatch-uri circulare: **C-QWERTY** (2019, ResearchGate 337284352) — 20–30 WPM; **COMPASS** (CHI 2017, doi 10.1145/3025453.3025454) — 10–12,5 WPM. Sunt mai vechi de 5 ani: le folosim ca baseline, nu ca surse „recente”.
- **Recente (≥ 2021):** „Text entry for the blind on smartwatches” (Univ. Access Inf. Soc., 2022, doi 10.1007/s10209-022-00870-2); „A One-Page Text Entry Method Optimized for Rectangle Smartwatches” (IEEE TMC, 2022); „Text Entry for XR Trove (TEXT)” (arXiv 2503.11357, 2025). **De adăugat** (Claude caută + expertul validează): lucrări 2021–2026 despre randare pe MCU/embedded GUI, LLM on-device/edge vs. cloud, latența asistenților vocali, antene în carcase metalice, design pentru reparabilitate.
- Surse normative: Reg. (UE) 2023/1542; Dir. (UE) 2024/1799; Reg. (UE) 2024/1689; Reg. delegat (UE) 2022/30; EN 18031-1/-2/-3; EN 300 328; EN 301 489-1/-17.

---

## 4. TRL 3 — ce avem și ce mai trebuie produs până la depunere

### 4.1 Ce avem deja (dovezi, cu locul din vault)
| # | Dovada | Unde | Ce demonstrează |
|---|---|---|---|
| D1 | Firmware „Suflet” + modulele SoulOS v1 (Canvas SDF, Face, Brain, Personality, Gestures, ClaudeLink, Keyboard, TextField, Predictor, TimePicker, Alarms, Shell); **61/61 teste Unity** trec; compilează pentru `amoled143`/`amoled175`/`sim` | `firmware/` (README) | funcțiile critice validate analitic/experimental pe componente separate |
| D2 | Simulator pe PC care produce cadrele reale ale motorului (10 clipuri: idle, boop, purr, dizzy, sleep…) + cadre cu tastatura și time-picker-ul | `firmware/sim`, `media/` | comportamentul vizual și logica UI, reproductibil |
| D3 | Serviciul AI `suflet_ai` v0.2: 3 moduri, 8 acțiuni cu scheme JSON stricte, parser local RO/EN, conector MCP, cheie proprie criptată; **49/49 teste** | `ai/` | arhitectura hibridă și degradarea controlată |
| D4 | Prototipul web SoulOS (tastatura rotundă interactivă) | `os/index.html`, `os/research/04` | geometria tastaturii, testabilă cu utilizatori |
| D5 | Geometria tastaturii pe diametre (pas = 0,0944·D → 6,7 mm pe Ø70) și analiza panourilor | `research/12` §1–2 | justificarea analitică a alegerii 2,8″ |
| D6 | CAD parametric (CadQuery), STL/STEP pentru P0, randări v6/v7/M | `prototip/`, `renders/` | conceptul electromecanic |
| D7 | Istoricul git (commit-uri datate) | repo vault | cronologia CD (utilă și la Grila 3.2a) |

**Limita actuală (declarăm cinstit):** nimic nu a rulat încă pe hardware fizic, iar firmware-ul țintește ecranul AMOLED CO5300. Pentru M trebuie portat pe **ST7701 (RGB) + GT911**.

### 4.2 Ce producem ÎNAINTE de depunere (dovezile experimentale TRL 3)
Placa **Waveshare ESP32-S3-Touch-LCD-2.8C** (≈ 40 $) + un microfon I2S + un amplificator mic se cumpără **din bani proprii și NU intră în buget** (§5.2.1 IV).

| # | Experiment (T−6 … T−2 săpt.) | Metodă | Rezultat de raportat | Cine |
|---|---|---|---|---|
| X1 | **Port pe 2.8C**: driver RGB ST7701 (Arduino_GFX `Arduino_RGB_Display`), framebuffer în PSRAM, touch GT911 | build `lcd28c` | firmware rulând pe placă; video | Cl (cod) + A (flash, filmare) |
| X2 | **fps la ochi** | contor de cadre pe serial, 10 min, cu Wi-Fi oprit/pornit | median/p5 fps (baseline pentru H1) | Cl + A |
| X3 | **Precizia touch** | test „grilă de ținte” 6,7 mm, 200 de atingeri, 3 persoane | % atingeri corecte, eroare medie în mm | Cl + A |
| X4 | **Tastare pilot** pe prototipul web (desktop/tabletă la scara 70 mm) și pe placă | fraze standard (MacKenzie), N = 5 | WPM, rata de eroare (baseline pentru H2) | A + Cl |
| X5 | **Parserul offline** pe un corpus de 200 de comenzi RO/EN | `pytest` + script de corpus | % comenzi corecte (baseline pentru H3) | Cl |
| X6 | **Latența unui tur AI** (text) cu Claude/OpenAI | 50 de tururi, cronometrare | p50/p90 în secunde | Cl |
| X7 | **Împerecherea BLE** cu Claude Desktop Hardware Buddy + RSSI prin plăci de aluminiu (tablă 1,5 mm) | telefon cu nRF Connect, 1/3/5 m | atenuare orientativă în dB | A |
| X8 | Consumul plăcii (ecran aprins/stins) | multimetru USB | mA (baseline pentru H5) | A |

**Livrabil înainte de depunere:** „Raport de laborator TRL 3 — SOUL M (2.8C)”, datat și semnat, cu loguri, fotografii, video cu marcaj de timp, hash-ul commit-ului git și rezultatele X1–X8. Aceasta e anexa principală a Raportului științific (Anexa 16 §2.3 D1–D3; Grila 2.3b).

---

## 5. Obiective SMART (identice în CF, Anexa 3 §1.2, Anexa 16 §1.4)

**Obiectiv general:** validarea modelului conceptual SOUL (dispozitiv AI tangibil, local-first, cu interfață circulară și carcasă reparabilă) de la TRL 3 la TRL 5, în 24 de luni, la București.

| Cod | Obiectiv specific (SMART) | Indicator + țintă | Termen | Activități | Rezultat |
|---|---|---|---|---|---|
| **O1** | Realizarea și validarea în laborator (**TRL 4**) a modelului integrat SOUL M (afișaj 2,8″ + touch + audio + baterie + AI hibrid) | fps median ≥ 30 · precizie touch ≥ 97 % · WPM ≥ 15 (N = 6) · succes offline ≥ 90 % · latență vocală p50 ≤ 1,8 s · 8/8 protocoale rulate | **L14** | A1, A2, A3 | R1 Raport TRL 4 |
| **O2** | Proiectarea și realizarea a **15 prototipuri pre-serie** cu PCB propriu și carcasă CNC din aluminiu cu baterie înlocuibilă | 15/15 unități funcționale · atenuare RSSI ≤ 6 dB · înlocuirea bateriei ≤ 5 min · autonomie ≥ 24 h (profil tipic) | **L17** | A4 | R2 (partea 1) |
| **O3** | Validarea în **mediu relevant (TRL 5)** cu ≥ 12 utilizatori timp de 4 săptămâni + pre-testare EMC/RF | WPM ≥ 20 și UER ≤ 3 % · latență p50 ≤ 1,5 s / p90 ≤ 2,5 s · succes offline ≥ 90 % · ≥ 99 % sesiuni fără crash · SUS ≥ 75 · 0 depășiri la pre-scan (marjă ≥ 3 dB) | **L22** | A5 | R2 Raport TRL 5 |
| **O4** | Protejarea și valorificarea rezultatelor | cerere de design EUIPO (≤ L5) · cerere de marcă (≤ L6) · 1 articol OA peer-review trimis (≤ L20) · ≥ 2 acorduri de pilot/distribuție + plan de comercializare (L24) | **L24** | A6, A7 | R3, R4, R5 |

### Rezultatele așteptate (max. 5, §3.9 p. 27)
- **R1** — Model de laborator SOUL M validat la TRL 4 + Raport de validare TRL 4 (L14).
- **R2** — 15 prototipuri SOUL M pre-serie validate la TRL 5 în mediu relevant + Raport TRL 5 + raport de pre-testare EMC/RF (L22).
- **R3** — 2 cereri de protecție IP depuse (desen/model industrial UE; marcă UE) + raport de brevetabilitate (L18).
- **R4** — 1 articol științific trimis la o revistă open-access peer-review + 1 comunicare la o conferință (L20–L24).
- **R5** — Plan de valorificare comercială + ≥ 2 acorduri de pilot/distribuție semnate (L24).

---

## 6. Activități (A0–A8) și calendar lunar

Tip: **CDI** = activitate de bază (I.1–I.4, ≥ 50 % din buget); **Conex** = II.1–II.5.

| Cod | Activitate | Tip (ghid) | Luni | Sub-activități | Livrabile |
|---|---|---|---|---|---|
| **A0** | Pregătirea CF, a Planului de afaceri, a Raportului științific + validarea de către expert | Conex **II.2**, *precontractuală* | înainte de depunere | – | CF, Anexa 3, Anexa 16 semnată |
| **A1** | Specificații, protocoale experimentale, setup de laborator | CDI **I.3** (+ **I.1** echipamente) | L1–L3 | 1.1 specificația sistemului M; 1.2 protocoalele P1–P10 cu praguri; 1.3 achiziția aparatelor de măsură și a PC-ului; 1.4 bancul de test (cutie ecranată, analizor de consum) | L1.1 Specificație; L1.2 Protocoale; **M1 Banc de test validat (L3)** |
| **A2** | Modelul de laborator M integrat: port RGB/ST7701, GT911, audio I2S (2 mic + amplificator), baterie 2500–3000 mAh, carcasă SLA la scara M, flux vocal (xiaozhi-esp32 adaptat + server UE `suflet_ai`), scalarea tastaturii la 480 px | CDI **I.3** + materiale | L2–L8 | 2.1 firmware afișaj/touch; 2.2 subsistem audio + AEC; 2.3 alimentare/PMU; 2.4 carcasă SLA; 2.5 server vocal UE; 2.6 integrare | L2.1 Model de laborator funcțional; **IE1 (L6): raport intermediar CDI** |
| **A3** | Validarea TRL 4 în laborator (protocoalele P1–P8, §7) + analiza rezultatelor + **raportul de etapă TRL 4** | CDI **I.3** | L6–L14 | 3.1 teste de componente; 3.2 teste de sistem; 3.3 studiu de tastare N = 6; 3.4 analiză + decizie de poartă | **R1 Raport TRL 4 (L14) = IE2**; decizia go/no-go TRL 5 |
| **A4** | Prototipul pre-serie: PCB propriu (ESP32-S3-WROOM-1, ST7701, GT911, ES8311/ES7210, PMU, IMU, RTC, pini de încărcare), antenă prin fereastră polimerică, carcasă CNC Al 6061 rev A (3 seturi) și rev B (5 + 15 seturi), baterie înlocuibilă, capsula OU; securitatea EN 18031 (secure boot, OTA semnat) | CDI **I.3/I.4** + servicii | L9–L17 | 4.1 schema și layout rev A (L9–L11); 4.2 fabricare + test rev A (L11–L13); 4.3 antenă + RF (serviciu extern); 4.4 **după poarta L14**: rev B + lotul de 15 carcase; 4.5 asamblare și QC | L4.1 PCB rev A testat; **M3 15 prototipuri (L17)** |
| **A5** | Validarea TRL 5 în mediu relevant: 15 unități la 12–15 utilizatori din BI (case, birouri, un living lab), 4 săptămâni, telemetrie opt-in; protocoalele P1–P10; 2 workshop-uri de testare; pre-testare EMC/RF (2 sesiuni) | CDI **I.3** + servicii de testare | L16–L22 | 5.1 recrutarea panelului (≥ 40 % femei, ≥ 2 persoane cu deficiențe de vedere/motorii); 5.2 teren; 5.3 pre-scan; 5.4 analiza + raportul TRL 5 | **R2 Raport TRL 5 (L22) = IE3** |
| **A6** | Protecția IP și valorificarea: căutare de anteriorități (L1–L3), design UE (≤ L5), marcă UE (≤ L6), evaluarea brevetabilității/modelului de utilitate (L12–L18); customer discovery (≥ 30 de interviuri), transformarea scrisorilor de intenție în acorduri, planul de comercializare | CDI **I.2/I.4** + conex **II.1** (promovare pentru validare comercială) | L1–L24 | – | **R3** (L18), **R5** (L24) |
| **A7** | Diseminare: manuscris (după depunerea IP), trimitere la o revistă OA peer-review (≤ L20), preprint în repozitoriu OA (Zenodo), prezentare la o conferință/târg, demo public | Conex **II.1** | L14–L24 | – | **R4** |
| **A8** | Management, audit financiar, comunicare și vizibilitate | Conex **II.3, II.4, II.5** | L1–L24 | – | rapoarte de progres, raport de audit, afiș/panou, comunicate |

### Diagrama Gantt (L1…L24)

| Activitate | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 Specificații, protocoale, setup laborator | ■ | ■ | ■ |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
| A2 Model de laborator M integrat |   | ■ | ■ | ■ | ■ | ■ | ■ | ■ |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
| A3 Validare TRL 4 + raport TRL 4 |   |   |   |   |   | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ |   |   |   |   |   |   |   |   |   |   |
| A4 PCB propriu + carcasă Al, pre-serie |   |   |   |   |   |   |   |   | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ |   |   |   |   |   |   |   |
| A5 Validare TRL 5 în mediu relevant + pre-scan |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | ■ | ■ | ■ | ■ | ■ | ■ | ■ |   |   |
| A6 Protecție IP + valorificare | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ |
| A7 Diseminare |   |   |   |   |   |   |   |   |   |   |   |   |   | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ |
| A8 Management, audit, vizibilitate | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ |

**Dependențe:** A2 depinde de M1 (L3). A3 depinde de L2.1. Rev B și lotul de 15 din A4 depind de **poarta IE2 (L14)**. A5 depinde de M3 (L17). Manuscrisul din A7 se trimite **după** depunerea cererilor IP (A6).

### Milestone-uri și indicatori de etapă (Anexa 13; §6 p. 64–65; §8.9.3 p. 85)
| Cod | Milestone | Luna | Criteriu de îndeplinire | Tip |
|---|---|---|---|---|
| M1 | Banc de test validat | L3 | aparatele recepționate și calibrate; protocoalele P1–P10 aprobate de coordonator | management/CDI |
| **IE1** | Raport intermediar CDI: modelul de laborator rulează integrat | **L6** (≤ 6 luni) | afișaj + touch + audio + AI funcționale; primele măsurători P1, P2, P5 | **calitativ CDI (obligatoriu)** |
| **IE2** | **Raportul de etapă TRL 4** + obiectivele TRL 5 | **L14** (≤ 2/3 = L16) | pragurile O1 atinse sau abaterile motivate; decizia go/no-go; dacă e no-go → Anexa 17 (eșec de cercetare) | **calitativ CDI (obligatoriu)** |
| M3 | 15 prototipuri pre-serie | L17 | QC trecut 15/15 | CDI |
| **IE3** | Raportul TRL 5 | **L22** | pragurile O3 atinse | calitativ CDI |
| IE-M1..M3 | Achiziții (L4, L15), progres financiar (≥ 30 % la L10, ≥ 70 % la L18), cerere IP depusă (L6) | – | – | management |

---

## 7. Protocoalele de validare TRL 4 și TRL 5 (indicatori măsurabili)

Ipoteze: **H1** randare · **H2** tastare/touch · **H3** AI hibrid și voce · **H4** RF prin aluminiu · **H5** energie și reparabilitate.

| Cod | Protocol | Ipoteză | Metodă de măsurare | Baseline (TRL 3, se completează din X1–X8) | Prag TRL 4 (laborator, L14) | Prag TRL 5 (mediu relevant, L22) |
|---|---|---|---|---|---|---|
| **P1** | fps la animația ochilor | H1 | contor de cadre în firmware, log serial/telemetrie; 60 min; Wi-Fi + BLE active; 24 de reacții | X2 | median ≥ 30 fps, p5 ≥ 24 | median ≥ 30, p5 ≥ 24 pe 15 unități; 0 artefacte de drift raportate |
| **P2** | Precizia touch | H2 | grilă de ținte de 6,7 mm pe tot discul (inclusiv bordura), 200 de atingeri/persoană | X3 | ≥ 97 % (N = 6) | ≥ 97 % (N ≥ 12) |
| **P3** | Viteza și acuratețea tastării | H2 | set de fraze MacKenzie–Soukoreff (EN) + set RO; 15 min de acomodare; WPM, UER, CER | X4 | ≥ 15 WPM, UER ≤ 5 % (N = 6) | **≥ 20 WPM, UER ≤ 3 %** (N ≥ 12) |
| **P4** | Diacritice RO automate | H2 | corpus de 300 de cuvinte RO | – | ≥ 90 % corecte | ≥ 95 % corecte |
| **P5** | Succesul offline | H3 | corpus de 200 de comenzi RO/EN (alarme, mementouri, notițe, cronometre, liste), fără internet | X5 | ≥ 90 % | ≥ 90 % pe comenzile reale din teren |
| **P6** | Latența vocală end-to-end | H3 | de la sfârșitul rostirii la primul sunet; 100 de ture; Wi-Fi casnic; servere UE | X6 (text) | p50 ≤ 1,8 s, p90 ≤ 3 s | **p50 ≤ 1,5 s, p90 ≤ 2,5 s** |
| **P7** | Degradarea controlată | H3 | se taie rețeaua sau cheia API în 50 de scenarii | – | 100 % fără blocare; răspuns local | 100 %; ≥ 99 % sesiuni fără crash (telemetrie) |
| **P8** | RF prin carcasă | H4 | RSSI în cutia ecranată și la 1/3/5/10 m: placă goală vs. SLA vs. Al rev A/B; pachete pierdute BLE | X7 | atenuare ≤ 8 dB (rev A) | **≤ 6 dB (rev B)**; legătură stabilă ≥ 10 m în interior; PDR ≥ 99 %; reconectare ≤ 3 s |
| **P9** | Autonomie și consum | H5 | analizor de consum; profil tipic definit (ecran activ 25 % din timp, 30 de interacțiuni vocale, BLE conectat); standby | X8 | modelul de consum validat ± 15 % | **≥ 24 h** în profil tipic; ≥ 7 zile standby |
| **P10** | Reparabilitate + utilizabilitate | H5 | cronometrarea înlocuirii bateriei (Torx) de către utilizatori neexperți; chestionar SUS; test de accesibilitate (voce, modul „taste mari”, contrast) | – | procedura documentată; ≤ 10 min (N = 3) | **≤ 5 min, 100 % reușită (N ≥ 10)**; SUS ≥ 75 |
| (P11) | Pre-scan EMC/RF (EN 300 328, EN 301 489-1/-17) | – | laborator acreditat, 2 sesiuni (rev A, rev B) | – | – | 0 depășiri, marjă ≥ 3 dB (rev B) |

**Mediul relevant la TRL 5 (Anexa 18):** configurația e „similară aplicației finale în aproape toate aspectele” (PCB propriu, carcasă finală din aluminiu, baterie finală, firmware + server UE) și rulează în condițiile reale de utilizare (locuințe și birouri din BI, rețele Wi-Fi casnice, zgomot ambiental, utilizatori reali), completate cu reproducerea controlată în laborator (cutie ecranată, atenuare calibrată). Diferențele față de produsul final (fără certificare CE, fără ambalaj, fără producție în serie) se analizează explicit în raportul TRL 5.

**Etică și date:** consimțământ informat, telemetrie opt-in, pseudonimizare, ștergerea datelor la final, fără înregistrarea audio brută (GDPR). Informare AI Act art. 50 la prima pornire.

---

## 8. Livrabile (Anexa 16 §5.4)

| Cod | Livrabil | Activitate | Luna | Responsabil |
|---|---|---|---|---|
| L1.1 | Specificația sistemului SOUL M | A1 | L2 | coordonator tehnic |
| L1.2 | Protocoalele experimentale P1–P11 cu praguri | A1 | L3 | coordonator tehnic |
| L2.1 | Modelul de laborator integrat + raportul IE1 | A2 | L6 | inginer embedded |
| **R1** | **Raportul de validare TRL 4** | A3 | L14 | coordonator tehnic |
| L4.1 | Documentația PCB rev A/B (scheme, Gerber, BOM) + CAD-ul carcasei rev B | A4 | L12 / L16 | inginer embedded |
| L4.2 | 15 prototipuri pre-serie + fișele QC | A4 | L17 | echipa |
| L5.1 | Rapoartele de pre-testare EMC/RF | A5 | L18 / L21 | laborator + coordonator |
| **R2** | **Raportul de validare TRL 5** (+ setul de date anonimizat) | A5 | L22 | coordonator tehnic |
| **R3** | Cererile IP (design UE, marcă UE) + raportul de brevetabilitate | A6 | L5 / L6 / L18 | Andu + consilier PI |
| **R4** | Manuscris trimis OA peer-review + preprint + prezentare la conferință | A7 | L20 / L24 | coordonator + student |
| **R5** | Planul de valorificare + ≥ 2 acorduri | A6 | L24 | Andu |

---

## 9. Echipa și salariile

### 9.1 Plafoanele legale (verificate azi pe textul HG 1188/2022)
**HG 1188/2022, Anexa nr. 2** — „Plafoane în limita cărora se calculează costurile salariale directe”, în **euro/oră**. Limita cuprinde toate taxele și impozitele datorate de angajat (adică se aplică salariului **brut**) și **tuturor veniturilor** unei persoane din unul sau mai multe proiecte. Conversia în lei se face la cursul BNR de la data contractului.

| Cat. | Activități | Funcții (text HG) | Plafon €/oră brut |
|---|---|---|---|
| 1 | creativitate înaltă și/sau experiență și abilități de conducere/management | CS I, CS II, IDT I, IDT II, profesor, conferențiar, **director/responsabil/manager de program/proiect** | **50** |
| 2 | cunoașterea aprofundată a metodelor de analiză și sinteză | CS III, IDT III, CS, IDT, lector, asistent universitar, **responsabil juridic/tehnic/achiziții/financiar proiect**, **personal de specialitate** | **35** |
| 3 | cunoașterea metodelor de analiză și a metodologiilor cercetării | asistent de cercetare, doctorand, masterand | **25** |
| 4 | activități suport | TI, TII, TIII, **student**, altele | **15** |

- **CAM (2,25 %) nu intră în plafon, dar e eligibilă** (ghid §5.3.2 p. 55).
- **Legea 183/2024** (statutul personalului CDI): funcțiile de cercetare sunt ACS, CS, CS III, CS II, CS I (CS III–I cer doctorat). Gradele **IDT nu se mai ocupă prin angajări noi** (art. 12). Într-un IMM, încadrăm pe **funcția din proiect** după Anexa 2, nu pe un grad de cercetare pe care persoana nu îl are.
- Timpul lucrat se ține în **pontaje lunare pe proiect**. Se respectă Codul muncii (max. 48 h/săpt. pe toate contractele).
- **Beneficiu fiscal:** salariații care lucrează efectiv într-un proiect CD pot fi **scutiți de impozitul pe venit** (Cod fiscal art. 60 pct. 3, cu documentația din Ordinul 2326/2855/2017). Contabilul verifică aplicarea.
- ⚠ HG 1188 poate fi modificată până la depunere. Verificăm forma în vigoare (Grila 2.2c: o singură depășire costă 1 punct, două costă 2 puncte).

### 9.2 Echipa propusă
| Rol în proiect | Cine | Categoria HG / plafon | Tarif bugetat (brut) | Ore | Contract | Criterii din grilă acoperite |
|---|---|---|---|---|---|---|
| **Coordonator tehnic/științific** (arhitectura sistemului, protocoale, rapoarte TRL, articol) | de recrutat: inginer embedded/electronist, **≥ 5 ani** în TIC/sisteme embedded (ideal doctor, ex. cadru didactic UPB) | cat. 2 „responsabil tehnic proiect” → **35 €/h** (cat. 1 = 50 €/h doar dacă e conferențiar/CS II etc.) | **34 €/h** | 50 h/lună × 24 = 1.200 h | CIM part-time sau detașare de la o organizație de cercetare | 3.1a (i) |
| **Inginer embedded/firmware** (port RGB, audio, PCB, EN 18031, teste) | de recrutat: studii superioare în domeniu, **≥ 2 ani** experiență (sau ≥ 1 publicație WoS/Scopus) | cat. 2 „personal de specialitate” → 35 €/h | **25 €/h** | 80 h/lună × 21 luni = 1.680 h | CIM part-time | 3.1a (ii) |
| **Student cercetare** (teste cu utilizatori, analiza datelor, corpusuri RO, documentație) | de recrutat: **≤ 24 ani, înmatriculat** (UPB ETTI/ACS), vârsta ≤ 24 la depunere și dovedită | cat. 4 „student” → 15 €/h | **12 €/h** | 60 h/lună × 20 luni = 1.200 h | CIM part-time | **4.3a (3 p.)** |
| **Manager de proiect** (coordonare, achiziții, raportare, relația cu AM PR BI, valorificare) | **Andu** | cat. 1 „manager de proiect” → 50 €/h | **18 €/h** | 20 h/lună × 24 = 480 h | CIM (❓ contabilul confirmă CIM-ul administratorului) sau serviciu extern | 3.2b (dacă i se documentează experiența CDI SOUL) |
| Designer industrial / mecanic (opțional) | serviciu extern sau inclus la coordonator | – | – | – | – | – |

**Pentru 3.2b** (un membru, altul decât cei de la 3.1, cu experiență CDI similară): fie Andu (cu dovezile activității CD SOUL: git, rapoarte, prototip), fie un al doilea inginer part-time. **Recomandare:** documentăm solid rolul lui Andu și **căutăm un inginer embedded care are și publicații/proiecte CDI**.

---

## 10. Bugetul (țintă 191.308 € eligibil = nerambursabil, 100 %)

Ipoteze: **TVA 21 % inclusă** pe achiziții (ARTEMIS e neplătitoare, deci TVA e eligibilă §5.3.2 p. 59); taxele EUIPO sunt fără TVA; serviciile din străinătate au TVA prin taxare inversă (nerecuperabilă, deci eligibilă — Ct confirmă). Salariile sunt brute + CAM 2,25 %. Curs orientativ ≈ 5,09 lei/€ (**se înlocuiește cu InforEuro din ghidul final**). Prețurile sunt **[E] până sosesc ofertele**.

### 10.1 Buget pe linii
| # | Linie | Categorie MySMIS / tip activitate | Activitate | € (cu TVA) |
|---|---|---|---|---|
| **I. ACTIVITATEA DE BAZĂ (CDI)** | | | | |
| 1 | Salariu coordonator tehnic/științific (1.200 h × 34 €) | Cheltuieli salariale CDI (I.3) | A1–A5, A7 | 40.800 |
| 2 | Salariu inginer embedded/firmware (1.680 h × 25 €) | Cheltuieli salariale CDI (I.3) | A2–A5 | 42.000 |
| 3 | Salariu student cercetare (1.200 h × 12 €) | Cheltuieli salariale CDI (I.3) | A3, A5, A7 | 14.400 |
| 4 | CAM 2,25 % pe liniile 1–3 | Cheltuieli salariale CDI | – | 2.187 |
| 5 | Osciloscop digital 4 canale ≥ 200 MHz (1.500 + TVA) | Active corporale – dezvoltare experimentală (subgr. 2.2) | A1–A5 | 1.815 |
| 6 | Analizor de spectru ≥ 3 GHz (3.500 + TVA) | Active corporale (2.2) | A3, A4, A5 | 4.235 |
| 7 | Analizor de consum / source-measure (1.000 + TVA) | Active corporale (2.2) | A3, A5 | 1.210 |
| 8 | Cutie ecranată RF ≥ 60 dB (900 + TVA) | Active corporale (2.2) | A3, A5 | 1.089 |
| 9 | Stație de lucru PC (2.000 + TVA) | Active corporale (grupa 3, echipamente informatice) | A2–A5 | 2.420 |
| 10 | Imprimantă 3D SLA (3.900 + TVA) | Active corporale (2.1) | A2, A4 | 4.719 |
| 11 | Materiale: 8 plăci 2.8C, 20 de panouri de 2,8″, 25 de seturi audio, 30 de celule Li-ion, componente, rășină, obiecte de inventar (3.725 + TVA) | Materiale, consumabile, obiecte de inventar | A2, A4 | 4.507 |
| 12 | CNC + anodizare carcase Al 6061 (3 + 5 + 15 seturi) (5.550 + TVA) | Servicii (echivalente) pentru dezvoltare experimentală | A4 | 6.716 |
| 13 | Fabricare + asamblare PCB propriu rev A/B (3.000 + TVA) | Servicii pentru dezvoltare experimentală | A4 | 3.630 |
| 14 | Pre-testare EMC/RF, 2 sesiuni (4.000 + TVA) | Servicii de sprijinire a inovării (testare) | A5 | 4.840 |
| 15 | Evaluare preliminară EN 18031 (2.500 + TVA) | Consultanță în inovare (utilizarea standardelor) | A4 | 3.025 |
| 16 | Servicii CDI externalizate: proiectarea/validarea antenei prin carcasa din aluminiu (4.500 + TVA) | Servicii CDI externalizate (I.3) | A4 | 5.445 |
| 17 | 2 workshop-uri/sesiuni de testare cu utilizatori | Workshop-uri colaborative (validare TRL 4–5) | A5 | 2.500 |
| 18 | SaaS: API AI (LLM/STT/TTS), găzduire UE, CAD (≈ 4.132 + TVA) | Servicii SaaS pentru CDI | A2–A5 | 5.000 |
| 19 | Taxe EUIPO: marcă UE (3 clase ≈ 1.050) + desen industrial multiplu (≈ 940) | Obținerea/protejarea activelor necorporale | A6 | 1.990 |
| 20 | Consilier în proprietate industrială: anterioritate, depunere, brevetabilitate (1.250 + TVA) | Consultanță în inovare (protecția activelor necorporale) | A6 | 1.512 |
| | **Subtotal activitate de bază** | | | **154.040** |
| **II.1 DISEMINARE (conex, în afara plafonului de 10 %)** | | | | |
| 21 | Taxă de publicare open-access peer-review (APC ≈ 2.800 + TVA) | Publicarea rezultatelor | A7 | 3.388 |
| 22 | Conferință/târg internațional: taxă, transport, cazare, diurnă, max. 2 persoane | Participare la conferințe/târguri | A7 | 2.900 |
| 23 | Customer discovery / focus-grupuri (1.240 + TVA) | Promovare pentru validare comercială | A6 | 1.500 |
| | **Subtotal II.1** | | | **7.788** |
| **II.2–II.5 (plafon cumulat 10 % din total)** | | | | |
| 24 | II.2 Consultanță pentru CF + validarea Raportului științific de către expert | Consultanță pentru CF (precontractuală) | A0 | 4.500 |
| 25 | II.3 Salariu manager de proiect (480 h × 18 €) + CAM | Management | A8 | 8.834 |
| 26 | II.4 Audit financiar (2.000 + TVA) | Audit | A8 | 2.420 |
| 27 | II.5 Comunicare și vizibilitate (1.000 + TVA) | Informare și publicitate | A8 | 1.210 |
| | **Subtotal II.2–II.5** | | | **16.964** |
| | **TOTAL COSTURI DIRECTE** | | | **178.793** |
| 28 | Costuri indirecte **7 %** × costuri directe (chirie, utilități, personal suport) | Rată forfetară | – | **12.515** |
| | **TOTAL ELIGIBIL = NERAMBURSABIL (100 %)** | | | **191.308** |

### 10.2 Verificarea pragurilor
| Prag | Valoare | Stare |
|---|---|---|
| 50.000 € ≤ nerambursabil ≤ 200.000 € | 191.308 € (rezervă de curs ~4,3 %) | ✅ |
| Activitatea de bază ≥ 50 % din eligibil | 154.040 / 191.308 = **80,5 %** | ✅ |
| II.2 + II.3 + II.4 + II.5 ≤ 10 % din eligibilul total | 16.964 / 191.308 = **8,9 %** (plafon 19.131 €) | ✅ |
| Indirecte = exact 7 % din directe | 12.515 € | ✅ |
| De minimis: 191.308 € + ajutoarele anterioare ≤ 300.000 € | spațiu necesar ≥ 108.692 € liber | ❓ |
| Salarii ≤ HG 1188 Anexa 2 | 34 ≤ 35 · 25 ≤ 35 · 12 ≤ 15 · 18 ≤ 50 | ✅ |
| Nimic neeligibil (telefoane, tablete, second-hand, leasing, vehicule) | – | ✅ |
| Eșec de cercetare: max. 50 % decontat; activele pentru TRL 5 cad | liniile 12 (lotul de 15), 13 (rev B), 14 se angajează **după IE2** | ✅ |

**Proporții:** personal CDI 52 % · echipamente 8 % · materiale + servicii de prototipare/testare/SaaS 19 % · IP + publicare + diseminare 6 % · conexe II.2–II.5 9 % · indirecte 7 %.

### 10.3 Justificarea valorii (pentru CF, secțiunea „Buget – Justificare”)
- Salariile acoperă ~3.900 de ore de CD pe 24 de luni: minimul realist pentru a porta, integra, proiecta un PCB, face două iterații de carcasă și rula două campanii de validare. Tarifele sunt **sub plafoane** și la nivelul pieței embedded din București.
- Echipamentele sunt strict cele de măsură fără de care nu se pot verifica H1–H5 (RF, consum, semnale). Nu cumpărăm aparatură „de confort”.
- Prototiparea (CNC, PCB) se face în două iterații (A → B), plus un lot de 15 unități, minimul pentru N ≥ 12 utilizatori + rezervă.
- Pre-testarea EMC/RF și EN 18031 reduc riscul fazei următoare (CE) fără să intre în certificarea finală, care e TRL 7–8 și **nu e cerută în proiect**.

---

## 11. Indicatorii programului (§3.8)
| Cod | Indicator | Țintă | Dovadă |
|---|---|---|---|
| RCO 01 | Întreprinderi sprijinite (din care micro) | **1** (micro) | raportul de progres final |
| RCO 02 | Întreprinderi sprijinite prin granturi | **1** | idem |
| RCR 03 | IMM-uri care introduc inovații de produs/proces | **1** | primul raport de durabilitate (la 1 an după plata finală): **prototipurile TRL 5 validate cu utilizatori reali + cererile IP + acordurile de pilot/distribuție** (categoriile 1 și 2, p. 26) |

Nu se adaugă alți indicatori în CF. Metricile tehnice P1–P11 apar în „Rezultate așteptate”, în Raportul științific și în Planul de monitorizare.

---

## 12. Economia circulară (Grila 1.5, 5 p. — trebuie să fie în **produs**, nu în echipamentele cumpărate)
| Principiu | Cum se regăsește în SOUL M | Cum se verifică în proiect |
|---|---|---|
| **Prelungirea duratei de viață / reparabilitate** | **baterie înlocuibilă de utilizator** (conector MX1.25, spumă, nu adeziv; Reg. 2023/1542 art. 11); închidere cu **șuruburi Torx** standard; module înlocuibile (panou, placă, difuzor) | P10: înlocuire ≤ 5 min; ghid de reparare publicat |
| **Design pentru dezasamblare și reciclare** | carcasă **monomaterial Al 6061** (reciclabil nelimitat), fără adezivi structurali; talpă polimerică detașabilă; marcarea materialelor | raport de dezasamblare: ≥ 90 % din masă separabilă pe fracții |
| **Actualizare software (OTA)** în loc de înlocuire hardware | funcții noi livrate prin OTA semnat; hardware-ul nu se învechește la schimbarea modelului AI (BYO-AI) | OTA semnat demonstrat la TRL 5 |
| **Independența de server** (evită „bricking”-ul de tip Humane) | modul offline complet + serverul AI publicabil/escrow | P5, P7 |
| **Reducerea resurselor pe unitatea de output** | un singur obiect pentru notițe/alarme/remindere/aprobări Claude; capsula OU fără baterie; ambalaj din pulpă/carton | BOM + fișa materialelor |
| **Piese de schimb** | angajament: baterii și piese de schimb 5 ani | Plan de afaceri §6 |

---

## 13. Principii orizontale și DNSH (§3.16–3.19; Grila 4.3)
**Egalitate de șanse și nediscriminare (măsuri minime):** recrutare nediscriminatorie (anunțuri neutre ca gen, criterii obiective); program flexibil și muncă hibridă; politica internă de egalitate de șanse (decizia administratorului, anexată); salarizare pe grilă transparentă.

**Măsură suplimentară (4.3b, 2 p.) — alegem cel puțin una, documentată:**
1. Panelul de validare TRL 5 are **≥ 40 % femei**, **≥ 3 persoane peste 55 de ani** și **≥ 2 persoane cu deficiențe de vedere sau motorii**, recrutate printr-o asociație de profil.
2. **Test de accesibilitate** al interfeței (voce, modul „taste mari” T9 cu taste de 10,3 × 7,7 mm, contrast ridicat, feedback haptic/sonor, dimensiunea textului) împreună cu o asociație de persoane cu dizabilități, cu raport public.
3. Stagiu plătit pentru un al doilea student dintr-un grup subreprezentat (opțional, fără cost suplimentar dacă îl înlocuiește pe primul la jumătatea proiectului).

**Tineri (4.3a, 3 p.):** studentul ≤ 24 ani, înmatriculat, angajat pe activități de CD (A3, A5, A7).

**Accesibilitatea produsului** (obligatorie, p. 32): control vocal, modul „taste mari”, text scalabil, paletă sigură pentru daltonism, fără dependență exclusivă de gesturi fine.

**DNSH (§3.17):** echipamentele respectă ecodesign-ul (Dir. 2009/125/CE) și **RoHS** (cerințe în specificațiile de achiziție); predarea rebuturilor de prototip (DEEE, baterii) la un colector autorizat, cu proces-verbal (OUG 5/2015); fără combustibili fosili; consum redus prin managementul luminii de fundal. Obiectivul de economie circulară e acoperit de §12.

---

## 14. Planul IP: „întâi protecția, apoi publicarea” (Plan de afaceri §6.2; Grila 1.4 + 2.1d)
| Pas | Ce | Când | Cost / linie |
|---|---|---|---|
| 0 | Căutare **TMview + DesignView** pentru „SOUL” (clasele 9, 42, 14, 28) — risc mare de conflict (SOUL Electronics etc.) | **acum**, înainte de depunere | 0 € |
| 0b | **Dacă** marca verbală e liberă: poate fi depusă **înainte** de proiect prin **EUIPO SME Fund** (voucher 75 %, până la 04.12.2026). Atunci **nu** mai apare în bugetul PoC (fără dublă finanțare, §5.2.1 V), iar linia 19 se folosește pentru **marca figurativă/clase suplimentare** și design | T−8 săpt. | în afara proiectului |
| 1 | Consilier PI: anterioritate + strategie (design / model de utilitate OSIM / brevet) | L1–L3 | linia 20 |
| 2 | **Desen/model industrial UE multiplu**: corpul SOUL M + capsula OU (+ eventual interfața grafică a ochilor) | **≤ L5**. ⚠ Grație de 12 luni de la **prima divulgare publică**: dacă randările v6/M sunt publice din sept. 2026, cererea trebuie depusă până în **sept. 2027**. Dacă asta cade înainte de contract, o depunem **după depunerea CF, ca activitate precontractuală** (la risc propriu) | linia 19 |
| 3 | **Marcă UE** (verbală sau figurativă, 3 clase) | ≤ L6 | linia 19 |
| 4 | Evaluarea brevetabilității/modelului de utilitate: carcasa cu fereastră radio polimerică + mecanismul bateriei înlocuibile + contactele OU; metoda de decodare a tastaturii circulare | L12–L18 | linia 20; depunerea OSIM, dacă merită, în perioada de durabilitate |
| 5 | **Publicare** (articol OA, preprint Zenodo) doar **după** depunerea cererilor de la pașii 2–3 | trimitere ≤ L20 | linia 21 |
| 6 | Secret comercial: parametrii decodorului, datele de antrenare, tuning-ul antenei | continuu | – |
| 7 | Cesiunea drepturilor Andu → ARTEMIS (codul și designul pre-proiect) + registrul licențelor open-source (MIT/OFL) | **înainte de depunere** | 0 € |

Calendarul (IP la L5–L6, publicare la L20) respectă regula grilei 1.4 „Patent first, publish later”: evaluatorul verifică doar coerența calendarului.

**Revista țintă (10 p. la 1.4):** o revistă OA peer-review indexată (ex. MDPI *Electronics* sau *Sensors*; IEEE *Access*), APC ≈ 2,5–3 k€. Alternativă fără cost: o revistă „diamond OA”. Includem și preprintul în Zenodo (repozitoriu OA).

---

## 15. Riscuri (Plan de afaceri §6.4 + CF; Grila 2.1e, 4 p.)
| # | Risc | Prob. | Impact | Măsuri |
|---|---|---|---|---|
| R1 | **Eșec de cercetare**: H1/H3/H4 nu se validează (fps < 30 pe RGB, atenuare RF > 6 dB, latență > prag) | medie | mare | poarta IE2 la L14 (≤ 2/3); alternative tehnice pregătite (randare parțială, bounce-buffers, fereastră radio mai mare, antenă externă în talpă, server mai aproape/model mai mic); dacă tot nu merge → **Anexa 17**, se decontează max. 50 % și **nu cumpărăm activele pentru TRL 5 înainte de poartă** |
| R2 | Recrutarea coordonatorului/inginerului întârzie | medie | mare | declarații de disponibilitate semnate **înainte de depunere**; detașare de la o organizație de cercetare ca variantă |
| R3 | Lanțul de aprovizionare (panouri, module, CNC) | medie | mediu | 2 furnizori pe linie; stoc tampon la L2 |
| R4 | Ghidul final schimbă plafoanele (Anexa 20) sau calendarul | medie | mediu | buget modular; rezervă de curs 4 % |
| R5 | Curs valutar: plafonul de minimis/200 k€ depășit la semnare | mică | mediu | 191 k€ în loc de 200 k€ |
| R6 | ARTEMIS devine plătitoare de TVA → TVA neeligibilă | medie | mediu | monitorizare lunară a CA; notificarea AM-ului; reducerea TVA din buget |
| R7 | Cash-flow până la rambursare | medie | mare | prefinanțare (§12.1), cereri de plată (§12.2), linie de credit FNGCIMM |
| R8 | Dependența de API-uri terțe (Claude/OpenAI/STT/TTS) | mică | mediu | modul offline; mai mulți furnizori; server UE propriu |
| R9 | Conformitate (AI Act art. 50, GDPR, EN 18031) | mică | mediu | informare AI la pornire; DPA; evaluarea EN 18031 (linia 15) |
| R10 | **Conflict cu planul Founders 00** (vânzarea a 25 buc. cu CE în primăvara 2027): dacă SOUL M e vândut/certificat înainte de contract, proiectul pare „demarat/finalizat” și TRL > 5 | **mare, dacă nu se decide** | **eliminatoriu** | **Decizie Andu (recomandare):** nu certificăm CE și nu vindem SOUL M înainte de contract; waitlist-ul rămâne (e dovadă de piață); Founders 00 devine **pasul post-PoC** (§16). Varianta B: lansare rapidă fără grant (equity) + PR BI 1.2 în loc de PoC |
| R11 | Schimbări de acționariat (ex. un investitor angel intră în ARTEMIS) | medie | **eliminatoriu** (condiții artificiale, §5.1.2) | investiția se face **într-un vehicul separat** sau **după durabilitate**, cu avizul AM; fără transfer de IP în durabilitate |
| R12 | Conflict de marcă „SOUL” | mare | mediu | căutare acum; marcă figurativă/compusă ca rezervă; designul protejează forma oricum |

---

## 16. Strategia post-PoC pe 5 ani (Plan de afaceri §6.1, §6.3; Grila 4.1 — toate cele 5 elemente)
Pornim de la rezultatul validat la TRL 5 (15 prototipuri, R2).

| Etapa | TRL | Perioada (An 1 = primele 12 luni după finalizare, ≈ 2029–2030) | Ce | Finanțare |
|---|---|---|---|---|
| **Founders 00** (pilot) | 6 → 7 | An 1 (S1) | 25 de unități numerotate, PCB rev C, **certificare CE/RED + EN 18031** (5–12 k€ + 0–9 k€), înregistrări ANMAP, GPSR; vânzare în RO; feedback | venituri din precomenzi (25 × 349 €), fonduri proprii, EUIPO SME Fund (IP), EDIH (testare) |
| **Batch 1 / CE complet** | 7 → 8 | An 1 (S2) – An 2 | 300 de unități, scule (matrițe parțiale), aplicația de telefon, 3–5 piețe UE (EPR, reprezentant autorizat) | **PR BI 1.2** (produse noi în IMM) sau **Eurostars Call 12/13**, pre-seed/angel **într-un vehicul care nu afectează PoC-ul**, crowdfunding (Indiegogo/Gamefound — Kickstarter nu e disponibil din RO) |
| **SOUL Standard** | 9 | An 2 – An 3 | 1–10 k unități/an, PCB cu modul certificat, cost < 60 €/buc., canale: online direct + retail de design + B2B (echipe care folosesc Claude Code) | venituri, **EIC Accelerator** (la TRL 6–8), credit garantat FNGCIMM pentru stoc |
| **Platforma** | 9 | An 3 – An 5 | abonament opțional (voce/memorie), accesorii, SoulOS pentru parteneri, licențierea designului/firmware-ului | venituri recurente, licențe |

**Modelul de valorificare:** comercializare directă a hardware-ului (349 € Founders → 199–299 € Standard) + serviciu opțional (voce/memorie) + licențiere B2B. **Proiecția financiară pe 5 ani** (Anexa 3 §6.3) se construiește din ipoteze explicite (preț, unități, COGS €190 → €60, marjă, CAC) — Claude o calculează separat, cu contabilul.

**Resursele umane în durabilitate (Anexa 3 §5.4):** păstrăm inginerul embedded (1 FTE din An 1), angajăm 1 suport/QA în An 2 și 1 inginer hardware în An 2–3; finanțate din venituri + rundă.

---

## 17. Grupul țintă (§3.7 NOTA)
1. Utilizatorii-pilot din București-Ilfov (≥ 12) care participă la validarea TRL 5.
2. Profesioniștii care lucrează zilnic cu asistenți AI (dezvoltatori care folosesc Claude Code/Cowork, creatori, freelanceri): nevoia de aprobări și notițe rapide, fără telefon.
3. Utilizatorii care vor un asistent **privat, cu funcționare offline**, fără abonament obligatoriu.
4. Persoanele cu nevoi de accesibilitate (control vocal, taste mari).
5. Ecosistemul regional: laboratoare universitare (UPB), ateliere CNC/PCB, laboratoare de testare.

---

## 18. Resursele și infrastructura (Anexa 16 §IV; Grila 2.3d, 3 p.)
| Resursă | Ce | Proprietar / acces | Activități | Dovadă la depunere |
|---|---|---|---|---|
| Laborator electronic ARTEMIS | bancul de lucru, aparatele din liniile 5–10 (după contract), stația de lipit | propriu | A1–A5 | Plan de afaceri §4.4 + fotografii |
| Laborator EMC/RF acreditat | pre-scan EN 300 328 / 301 489 | contract de servicii | A5 | ofertă + scrisoare de disponibilitate |
| Organizație de cercetare parteneră (UPB ETTI / IMT / ICI) | expertiză RF/antene, eventual acces la camera anecoică, recrutarea studentului | acord de colaborare | A4, A5 | **scrisoare de intenție** (se poate număra și la 4.2 dacă are cele 7 elemente) |
| Ateliere CNC, PCB | prototipare | contracte de servicii | A4 | oferte |
| Software | Git, PlatformIO, KiCad (gratuit), CAD (SaaS), servere UE | licențe/SaaS | toate | – |
| Date | corpusuri RO/EN (comenzi, fraze de tastare) | proprii | A3, A5 | – |

---

## 19. Reguli de redactare comune (checklist de corelare)
- Același **titlu**, aceleași **O1–O4**, **A0–A8**, **P1–P11**, **R1–R5**, aceleași **luni** în CF, Anexa 3, Anexa 16, Anexa 13.
- Aceleași **sume** în CF, Anexa 3 §4.5–4.7/§5.2–5.3 și Anexa 19.
- Același **TRL**: pornire 3, intermediar 4 (L14), țintă 5 (L22).
- Aceleași **domenii RIS3**: TIC + Sisteme și Componente Inteligente.
- Același vocabular (vezi nota din capul fișierului).
- Orice afirmație de piață are o sursă (link + dată) în Anexa 3 §III.
