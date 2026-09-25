# 12 · Ecran mai mare pentru SOUL: ce panouri există, ce tastatură iese, ce corp rezultă (2026-09-25)

Etichete: **[V]** pagină deschisă azi cu WebFetch sau fișier verificat local (URL / cale în §9) · **[V-s]** doar rezumat de căutare, pagina nu a fost deschisă · **[K]** cunoștințe generale, de verificat · **[E]** estimare / calcul propriu.
Pleacă de la: SOUL v6 = aluminiu, **63 × 72 × 27 mm**, AMOLED rotund **1,75″, 466×466, Ø43,76 activ** (Waveshare ESP32-S3-Touch-AMOLED-1.75, CO5300 pe QSPI); tastatura rotundă din `os/research/04` (taste de **4,13 × 4,88 mm**). Randările comparative sunt în `renders/v7/`.

Cererea fondatorului: „e prea mic, cum scrii pe el? mai mare".

---

## 0. Pe scurt
1. **Nu există AMOLED rotund mai mare de 1,75″ care să se poată cumpăra în cantități mici cu placă de dezvoltare.** Waveshare, Viewe, Elecrow, LilyGO și Makerfabs se opresc toți la 1,75″ / 466×466 pentru AMOLED rotund [V]. AMOLED-urile de 1,96–2,13″ sunt dreptunghiulare (ceasuri, 410×502) [V-s], iar AMOLED-ul „mare" de 2,16″ de la Waveshare e **pătrat** 480×480 [V]. Are practic **aceeași suprafață** ca rotundul de 1,75″ (1 505 mm² față de 1 504 mm²) și taste mai înguste (3,9 mm) [E]. Deci **„mai mare" înseamnă IPS**, nu AMOLED.
2. **Geometria tastaturii e liniară cu diametrul:** pasul tastei ≈ **0,094 × Ø** [E]. Taste de **6 mm** cer **Ø ≥ 63,5 mm**, iar de **7 mm** cer **Ø ≥ 74 mm**. Rotundele IPS care trec pragul: **2,8″ (Ø70–71, 480×480, ESP32-S3)** → taste de **6,6–6,7 mm**. Apoi **3,4″ (Ø86–88, 800×800, ESP32-P4)** → **8,2 mm** și **4″ (Ø101,5, 720×720, P4)** → 9,6 mm [V + E]. Rotundul IPS de 2,1″ (Ø53) dă doar **5,0 mm**.
3. **Recomandare (3 variante, randate în v7):**

| | Ecran | Corp (l × h × a) | Taste | Negru | Pentru |
|---|---|---|---|---|---|
| **S** (azi) | 1,75″ AMOLED 466², Ø43,8 | **63 × 72 × 27 mm** | 4,1 mm | adevărat | buzunar, noptieră, „ochi vii"; scrisul se face pe telefon sau cu vocea |
| **M** ★ | 2,8″ IPS 480², Ø70–71 | **≈ 93 × 106 × 31 mm** | **6,7 mm** | gri (IPS) | se poate tasta direct pe el, dar e obiect de geantă, nu de buzunar |
| **L** | 3,4″ IPS 800², Ø86–88 | **≈ 113 × 129 × 34 mm** | 8,2 mm | gri (IPS) | obiect de birou sau noptieră; tastare confortabilă; MCU diferit (P4) |

4. **Recomandarea mea [E]:** păstrăm **S** ca produs-erou, cu scrisul rezolvat „în afara ecranului": **telefonul ca tastatură prin BLE, dictare și tastatură Bluetooth**, toate posibile pe hardware-ul de azi (§6). În paralel construim **M** ca prototip: aceeași familie ESP32-S3, driverul e deja în Arduino_GFX și costă ~$40 cu placă cu tot. Îl punem în mâna fondatorului lângă S înainte de a decide. **L** nu e pentru buzunar. E un „SOUL de birou" și cere alt MCU (P4 + C6 pentru radio), deci mai multă muncă de firmware.
5. **Prețul real al lui M:** pierdem negrul adevărat. Ochii nu mai „plutesc" în sticlă neagră, iar noaptea, pe OU, discul IPS luminează gri. Consumul ecranului crește de ~5–10× cât timp e aprins, iar corpul are volumul de ~2,5× și masa de ~2× (§5).

---

## 1. Ce înseamnă „mai mare" pentru tastatură (geometrie)
Tastatura SoulOS de azi (os/research/04 §1) pe discul de 466 px are rândul 1 cu 10 taste × 44 px. Rândul folosește 440 px din coarda de 447 px, iar tastele au 52 px înălțime. Totul scalează liniar cu diametrul activ D:
- **pas tastă = D × 44/466 = 0,0944·D**, **înălțime = 0,1116·D** [E, din layout].
- **Taste de 6 mm → D ≥ 63,5 mm. Taste de 7 mm → D ≥ 74 mm** [E].
- Pentru comparație: tastele iPhone în portret au ≈ 5,5–6 mm lățime [K], iar minimul watchOS e ~4,4 mm (04 §1).

| Ecran | D activ (mm) | Pas × înălțime tastă (mm) | Coarda rândurilor 1/2/3 (mm) | Taste de 7 mm pe rând (1/2/3) | QWERTY cu 10 pe rând? |
|---|---|---|---|---|---|
| 1,75″ AMOLED (azi) | 43,76 | **4,13 × 4,88** | 43,5 / 43,4 / 41,0 | 6 / 6 / 5 | da, dar la limită (decodorul face treaba) |
| 1,85″ IPS rotund 360² | 47,0 | 4,44 × 5,24 | 46,8 / 46,6 / 44,1 | 6 / 6 / 6 | la limită |
| 2,1″ IPS rotund 480² | 53,3 | **5,03 × 5,95** | 53,0 / 52,9 / 50,0 | 7 / 7 / 7 | da, 5 mm |
| 2,16″ AMOLED **pătrat** 480² | latură 38,8 | 3,88 × ~5 | 38,8 la toate | 5 | mai rău decât azi |
| 2,41″ AMOLED dreptunghi 450×600 | 36,7 × 49,0 | 3,7 (portret) / 4,9 (peisaj) | — | — | nu ajută |
| **2,8″ IPS rotund 480²** | **70,1–71,1** | **6,6–6,7 × 7,8–7,9** | 69,8 / 69,6 / 65,8 | 9–10 / 9–10 / 9 | **da, ≥ 6,5 mm** |
| 3,4″ IPS rotund 800² | 86,4–87,6 | **8,2 × 9,7** | 86,0 / 85,7 / 81,0 | 12 / 12 / 11 | da, confortabil |
| 4″ IPS rotund 720² | 101,5 | 9,6 × 11,3 | 101 / 100,7 / 95,2 | 14 / 14 / 13 | da, mai mult decât trebuie |

Cum citești tabelul:
- Ca să treci de ~6,5 mm cu QWERTY-ul actual (10 taste pe rând) îți trebuie un disc de ~70 mm. Asta e **exact 2,8″**.
- Sub asta, singura cale spre taste mari rămâne ce avem deja pe 1,75″: modul **„Taste mari"** (T9 predictiv 3×4, taste de 10,3 × 7,7 mm, 04 §12) și vocea.
- Densitatea de pixeli scade de la 10,65 px/mm (1,75″) la 6,8 px/mm (2,8″, 480 px pe 70 mm) [E]. Textul Nunito de 22 px arată mai mare fizic, dar mai puțin fin. Pe 3,4″ / 800 px revenim la 9,2 px/mm.

---

## 2. Panouri candidate (cumpărabile la 1–25 buc., cu placă de dezvoltare)

### 2a. AMOLED rotund (negru adevărat)
| Produs | Dim. / px | D activ | IC display · interfață | Touch | MCU / placă | Preț | Notă |
|---|---|---|---|---|---|---|---|
| **Waveshare ESP32-S3-Touch-AMOLED-1.75** (azi) | 1,75″ · 466×466 | 43,76 | **CO5300 · QSPI** | CST9217 | ESP32-S3R8, 2 mic + ES8311/ES7210, AXP2101 | **$29,99–39,99** [V] | 700 cd/m², 100 000:1 [V] |
| Viewe ALL-UEOL018VG (panou) | 1,75″ · 466×466 | ~43,8 | MIPI / QSPI | da | doar panou | la cerere [V-s] | același diametru |
| Viewe / Waveshare 1,43″, 1,5″ | 466×466 | 35–38 | CO5300 / SH8601 · QSPI | da | S3 | $22–32 [V] | mai mici |
| **Waveshare ESP32-S3-Touch-AMOLED-2.16** | 2,16″ · **480×480, PĂTRAT** | latură ~38,8 [E] | **CO5300 · QSPI** | CST9220 | ESP32-S3R8, 2 mic, ES8311, AXP2101, IMU, RTC | **$29,99–31,99** [V] | 600 cd/m² [V]; nu e rotund, deci „ochii în cerc" ar sta într-un pătrat |
| LilyGO T4-S3 | 2,41″ · 450×600 dreptunghi | 36,7 × 49 [E] | RM690B0 · QSPI | da | S3 | ~$59–74 [V-s] | dreptunghi |
| Panouri de ceas 1,96–2,13″ | 410×502 / 416×502 | dreptunghi | QSPI/MIPI | da | — | [V-s] | dreptunghiulare |

**Concluzie:** Round AMOLED > 1,75″ nu apare la niciunul dintre vânzătorii verificați (Waveshare, Viewe, Elecrow, LilyGO, Makerfabs), iar listele „1,04–2,1″" ale integratorilor chinezi au în zona de 2″ doar TFT-uri rotunde [V/V-s]. Un AMOLED rotund custom de ~2″ ar cere NRE la un producător de panouri (Visionox/BOE/Tianma, prin integratori) și MOQ de mii de bucăți [K/E]. Nu e o opțiune pentru primele 10–25 de bucăți.

### 2b. IPS rotund (negru = gri; lumina de fundal se vede)
| Produs | Dim. / px | D activ | IC · interfață | Touch | MCU / placă | Preț | Putere / notă |
|---|---|---|---|---|---|---|---|
| Waveshare ESP32-S3-Touch-LCD-1.85 | 1,85″ · 360×360 | ~47 | ST77916 · QSPI [K] | da | S3 | ~$20–25 [K] | aproape același diametru; nu merită |
| **Waveshare ESP32-S3-Touch-LCD-2.1** | 2,1″ · 480×480 | 53,3 | **ST7701 · RGB** | CST820 (1 punct) | ESP32-S3R8, IMU, RTC, TF, încărcare Li-ion MX1.25 | **$32,99** [V] | contur placă Ø75 [V]; 262K culori |
| LilyGO T-RGB 2.1 | 2,1″ · 480×480 | 53,3 | ST7701S · 3-wire SPI + RGB 18-bit | CST820 / FT3267 | S3R8, 16 MB PSRAM | ~$28–35 [V/V-s] | are și variantă 2,8″ (GT911) [V] |
| Makerfabs MaTouch Rotary 2.1 | 2,1″ · 480×480 | 53,3 | ST7701S · RGB565 | CST8266 | S3R8 + encoder rotativ | **$38,80** [V] | USB, fără baterie [V] |
| Elecrow CrowPanel 2.1″ Rotary | 2,1″ · 480×480 | 53,3 | IPS | da | ESP32-S3 + buton rotativ | **$35,70** [V-s] | |
| **Waveshare ESP32-S3-Touch-LCD-2.8C** | **2,8″ · 480×480** | **~70–71** | **ST7701 · RGB** | **GT911** | ESP32-S3R8, IMU QMI8658, RTC, TF, **încărcare Li-ion MX1.25**, buzzer | **$39,99** cu touch / $32,99 fără [V] | 1200:1, 160° [V]; placa are contur Ø≈95,9 [V], deci în corpul M intră doar panoul gol |
| Panou 2,8″ gol (Twoyas și alții) | 2,76–2,8″ · 480×480 | **70,13 × 70,13** | ST7701S · RGB | opțional | — | **$11,50** [V] | contur **73 × 77,6 × 2,3 mm** [V], deci bordura e de doar ~1,5 mm |
| Elecrow 2,8″ Round IPS | 2,8″ · 480×480 | ~70 | IPS | — | modul | $36,90 [V-s] | |
| **Waveshare ESP32-P4-WIFI6-Touch-LCD-3.4C** | **3,4″ · 800×800** | **87,6** (zona afișată) [V] | **JD9365 · MIPI-DSI 2 benzi** [V] | GT9271, 10 puncte | **ESP32-P4** (32 MB PSRAM) + **ESP32-C6** pentru Wi-Fi 6/BLE, 2 mic | **$64,99–74,99** [V] | 300 cd/m²; contur 115 × 115 [V]; **fără încărcător Li-ion** pe placă (doar baterie RTC) [V] |
| Waveshare ESP32-P4-WIFI6-Touch-LCD-4C | 4″ · 720×720 | 101,5 | JD9365 · MIPI-DSI | GT9271 | P4 + C6 | $74,99 [V] | 350–550 cd/m²; contur 126 × 126 [V] |
| Waveshare 3.4/4-DSI-TOUCH-C (doar panou) | 3,4″ / 4″ | 87,6 / 101,5 | JD9365 · DSI | GT9271 | — | $59,99–69,99 [V] | pentru P4 sau alt host DSI |

### 2c. Poate firmware-ul nostru să le conducă?
Stiva de azi: Arduino + **Arduino_GFX 1.6.8** + `Canvas` SDF propriu (randare anti-aliased în RAM, apoi push) [V local: `firmware/platformio.ini`, `firmware/README.md`].
- **CO5300 (1,75″ și 2,16″ pătrat):** e deja driverul nostru. Pentru 2,16″ se schimbă doar dimensiunea și offset-ul. **Efort ~0** [V local].
- **ST7701 pe RGB (2,1″ / 2,8″ pe S3):** Arduino_GFX are `Arduino_RGB_Display` cu 9 tabele de init `st7701_type1…9` [V local, `…/display/Arduino_RGB_Display.h`]. Diferențele față de azi:
  - Panoul RGB **nu are memorie proprie**, deci framebuffer-ul de 480×480×2 = **460 KB stă în PSRAM** și e scanat continuu. Randarea parțială de azi (doar zona ochilor) devine scriere în framebuffer, apoi DMA. Merge; T-RGB și MaTouch rulează LVGL la 30–75 fps [V-s].
  - Magistrala RGB ocupă ~16–18 GPIO și lățime de bandă PSRAM, iar Wi-Fi + RGB pe S3 cere bounce-buffers ca să nu apară drift [K].
  - Tastatura, fonturile și Canvas scalează: layout-ul e în px pe un disc de 466. Pe 480 facem un factor 480/466 sau un layout separat [E].
  - **Efort: ~1–2 săptămâni** [E].
- **JD9365 pe MIPI-DSI (3,4″ / 4″ pe P4):** Arduino_GFX are `Arduino_DSI_Display` cu `jd9365_init_operations` și `Arduino_ESP32DSIPanel` [V local]. Tabelul de init pentru panoul rotund 800×800 trebuie însă luat din BSP-ul ESP-IDF de la Waveshare [E]. **P4 nu are radio**: Wi-Fi și BLE vin prin C6 (esp-hosted), deci legătura noastră BLE „Claude Hardware Buddy" (NimBLE pe S3) trebuie mutată pe C6 sau tunelată [K]. **Efort: 3–6 săptămâni** [E]. Avantaj: P4 are PPA/2D-DMA și 32 MB PSRAM, deci 800×800 e fluid.
- **Touch:** CST820 (1 punct) ajunge pentru tastatură. GT911/GT9271 sunt multi-touch, cu biblioteci disponibile (SensorLib e deja în proiect) [V local].

---

## 3. AMOLED vs IPS: ce pierdem vizual (cinstit)
- **Negru:** AMOLED stinge pixelul, contrast ~100 000:1 [V]. IPS are 1200:1 [V]: negrul e ~0,1 % din alb din față și mai mult din unghi, cu „glow" argintiu-violet în colțuri [K]. Pe sticla neagră a lui SOUL, discul IPS se vede ca un **cerc gri închis** în interiorul inelului negru, cu ochii pe el. Randările v7 M și L au un glow mic pus intenționat [E].
- **Noaptea (OU, noptieră):** cel mai mare cost. Pe AMOLED, ochii chihlimbar plutesc în întuneric. Pe IPS, tot discul luminează. Ca să atenuăm, oprim complet lumina de fundal când ochii sunt închiși, iar noaptea folosim PWM foarte jos. Chiar și așa, ochii deschiși vin cu un halou gri [E].
- **Consum:** fața SOUL e ~90 % neagră, deci AMOLED-ul consumă ~15–40 mW. Lumina de fundal a unui IPS de 2,8″ consumă ~0,25–0,4 W cât timp e aprinsă, indiferent de conținut [K/E], adică de **~5–10× mai mult**. Corpul mai mare compensează parțial cu o baterie mai mare (§5).
- **Unghi de vizualizare:** ambele sunt bune (IPS 160–170° [V]).
- **Luminozitate:** AMOLED 1,75″ 700 cd/m² [V]; IPS 2,8″ ~300–400; P4 3,4″ 300 cd/m² [V]. Afară, AMOLED-ul mic se vede mai bine.

---

## 4. Alternative de scris, indiferent de mărime
| Metodă | Cum | Hardware nou? | Pentru RO | Efort [E] | Notă |
|---|---|---|---|---|---|
| **Telefonul ca tastatură (BLE)** | SOUL expune un serviciu GATT „text in". Pe **Android**, o pagină web cu Web Bluetooth (Chrome) [V caniuse]. Pe **iOS**, Safari nu are Web Bluetooth [V], deci trebuie o aplicație mică (sau extensia iOSWebBLE [V]). Se deschide cu QR de pe ecranul SOUL. | nu | tastatura telefonului, cu diacritice și dictare | 1–2 săpt. (Android/web) + app iOS | cea mai bună experiență de scris; SOUL rămâne mic |
| **Dictare** | cele 2 microfoane de pe placa 1,75″ [V] → STT în cloud (Whisper / Google / Azure, ~$0,006/min [K]) sau prin AI-ul ales de utilizator | nu | da (cloud) | 1 săpt. | ESP-SR offline face doar comenzi, nu dictare în română [K]; tastatura are deja tasta 🎤 (04) |
| **Tastatură Bluetooth** | ESP32-S3 e **doar BLE**, deci merg doar tastaturile BLE (multe au BLE: Logitech K380/Keys-To-Go [K]). Exemplul ESP-IDF `esp_hid_host` suportă S3 și primește rapoarte de tastatură [V]. | nu | layout RO din firmware | 1–2 săpt. (sub Arduino trebuie adaptat din IDF) | „modul birou"; SOUL stă pe picior ca un mic monitor |
| **Taste mari (T9)** | deja proiectat: 3×4, 10,3 × 7,7 mm (04 §12) | nu | da | în plan | lent, dar confortabil |
| **Continuare pe telefon / desktop** | text lung → „continuă pe telefon" (link) sau Claude Desktop prin Hardware Buddy | nu | — | mic | SOUL nu e unealta pentru eseuri |

**Concluzie §4:** problema „nu pot scrie" se rezolvă pe **S** cu telefon + voce + tastatură BLE, fără să schimbăm ecranul. Ecranul mare ajută **tastarea directă pe SOUL**, dar nu e singura cale.

---

## 5. Cele 3 variante, cu corpul
Metodă [E]:
- Corpul v6 se scalează în lățime și înălțime cu k.
- Inelul negru din jurul zonei active se subțiază de la 4,1 mm (v6) la ~1,8 mm la scara locală, pentru că panourile IPS goale au bordură de ~1,5 mm (2,8″: contur 73 față de 70,1 activ [V]). Asta dă activ/lățime = 0,77 față de 0,70 azi.
- Adâncimea crește mai puțin decât k, pentru că bateria crește în plan și stiva doar cu câțiva mm.

| | **S** (azi) | **M** ★ | **L** |
|---|---|---|---|
| Panou | 1,75″ AMOLED 466², CO5300 QSPI | 2,8″ IPS 480², ST7701 RGB, GT911 | 3,4″ IPS 800², JD9365 DSI, GT9271 |
| D activ | 43,8 | 70,1–71,1 | 86,4–87,6 |
| **Corp l × h × a** | **63 × 72 × 27 mm** | **≈ 93 × 106 × 31 mm** | **≈ 113 × 129 × 34 mm** |
| Taste (pas) | 4,1 mm | **6,7 mm** | 8,2 mm |
| MCU / placă de pornire | ESP32-S3 (Waveshare 1.75, $30–40) | ESP32-S3 (Waveshare 2.8C $40 sau LilyGO T-RGB 2.8; apoi PCB propriu + panou $11,5) | ESP32-P4 + C6 (Waveshare 3.4C, $65–75) |
| Audio (2 mic + difuzor) | pe placă [V] | **nu e pe 2.8C**, trebuie adăugat (ES7210/ES8311 sau mic I2S) [V/E] | 2 mic pe placă, conector difuzor [V] |
| Baterie care încape [E] | 800–1000 mAh | **~2500–3000 mAh** | ~3500–4500 mAh |
| Autonomie cu ecranul aprins [E] | ~20 h | ~20–25 h (lumina de fundal consumă cât câștigăm din baterie) | ~15–20 h (P4 + C6 + lumină de fundal) |
| Masă [E] | ~80–110 g | ~180–230 g (≈ un telefon) | ~260–330 g |
| Buzunar | da (blugi, sacou) | **nu**: geantă, rucsac, buzunar de geacă | nu: obiect de birou / noptieră |
| Carcasa CNC [E, față de 10] | $110–220/set la 10 buc. | ×1,6–2 (volum, timp de frezare) | ×2–2,5 |
| Negru / noapte | adevărat, „ochi în întuneric" | gri, cu halou | gri, cu halou |
| Firmware | azi | +1–2 săpt. | +3–6 săpt. |

**Opțiunea „S+" (nerandată):** 2,1″ IPS rotund (Ø53,3) dă un corp de **≈ 70 × 80 × 28 mm** și taste de **5,0 mm**. E un pas de 20 %: pierde negrul AMOLED și nu ajunge la pragul de 6 mm. **Nu o recomand**: ia dezavantajele lui M fără avantajul principal.

**Opțiunea „pătrat AMOLED 2,16″":** aceeași suprafață ca 1,75″, taste mai înguste și o față pătrată. **Nu.**

### Recomandare
1. **S rămâne produsul-erou** pentru primele 10–25 de bucăți. Scrisul îl rezolvăm prin **telefon (BLE) + dictare + tastatură BLE** (§4). Îi arătăm fondatorului că SOUL „nu e un telefon mic", ci un companion la care scrii de pe telefon și pe care îl ții pe birou.
2. **Construim M ca prototip A/B în 2–3 săptămâni** (Waveshare 2.8C, $40, + carcasă SLA la scara din v7). Fondatorul le ține pe amândouă în mână, tastează pe amândouă și decide din mână, nu din randări.
3. Dacă M câștigă: **„SOUL Desk" = M** (sau L pentru birou), ca al doilea produs, iar S rămâne „SOUL Pocket". Două mărimi, același OS. Layout-ul tastaturii scalează deja.
4. **L doar dacă** vrem explicit un dispozitiv de birou cu scris mult. Cere P4, deci alt firmware de bază.

---

## 6. Ce cere M concret (lista de cumpărături pentru prototip)
- Waveshare ESP32-S3-Touch-LCD-2.8C (cu touch) $39,99 [V] sau LilyGO T-RGB 2.8 [V].
- Mic I2S (ICS-43434) + amplificator MAX98357 + difuzor, pentru că 2.8C nu are microfoane [E/K].
- LiPo 2000–3000 mAh; placa 2.8C încarcă pe MX1.25 [V]. **Verifică curentul de încărcare** (lecția de la 1.43, §02).
- Carcasă SLA la **93 × 106 × 31** din `renders/v7` (scalată din STEP-ul v6), apoi CNC dacă trece testul.
- Firmware: env `lcd28` în `platformio.ini`, `Arduino_ESP32RGBPanel` + `Arduino_RGB_Display` (ST7701), touch GT911 prin SensorLib, Canvas pe framebuffer PSRAM, layout tastatură scalat la 480.

## 7. Riscuri / de verificat
- Diametrul activ exact al 2.8C (≈ 70,1 conform panoului gol Twoyas [V]; Waveshare nu îl dă în text).
- Tabelul de init ST7701 potrivit plăcii (Waveshare dă cod IDF/Arduino) și fps cu Wi-Fi activ.
- Cât se vede glow-ul IPS prin sticla noastră neagră. **Se poate testa în 10 minute cu o placă 2.8C lângă S, noaptea.**
- 3.4C: fără încărcător Li-ion, deci are nevoie de PCB de alimentare propriu. BLE prin C6, deci trebuie portată legătura Hardware Buddy.

## 8. Randări (CGI)
`renders/v7/`: `soul_v7_hands.png` (S/M/L în aceeași palmă, aceeași cameră), `soul_v7_lineup.png` (S/M/L pe birou, cu un telefon generic și o cană), `soul_v7_typing.png` (M cu tastatura SoulOS la scară, cu degetul mare deasupra tastelor). Toate sunt randări / concept (CGI).

## 9. Surse
- [V] Waveshare ESP32-S3-Touch-AMOLED-1.75: https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm
- [V] Waveshare ESP32-S3-Touch-AMOLED-2.16 (pătrat, CO5300, CST9220, $29,99–31,99): https://www.waveshare.com/esp32-s3-touch-amoled-2.16.htm · https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-2.16
- [V] Waveshare ESP32-S3-Touch-LCD-2.1 (ST7701 RGB, CST820, $32,99): https://www.waveshare.com/esp32-s3-touch-lcd-2.1.htm · wiki (contur Ø75): https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-2.1
- [V] Waveshare ESP32-S3-Touch-LCD-2.8C (ST7701 RGB, GT911, $39,99 / $32,99): https://www.waveshare.com/esp32-s3-touch-lcd-2.8c.htm · wiki (contur Ø95,86): https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-2.8C
- [V] Waveshare ESP32-P4-WIFI6-Touch-LCD-3.4C / 4C (800² / 720², zonă 87,6 / 101,52 mm, GT9271, $64,99–74,99): https://www.waveshare.com/esp32-p4-wifi6-touch-lcd-3.4c.htm · https://www.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-3.4C
- [V] Waveshare 3.4/4-DSI-TOUCH-C (JD9365, $59,99–69,99): https://www.waveshare.com/4-dsi-touch-c.htm
- [V] CNX Software despre P4 3.4″/4″ (prețuri, ESP-IDF/LVGL): https://www.cnx-software.com/2025/06/01/esp32-p4-development-board-features-3-4-inch-or-4-inch-round-ips-touchscreen-display/
- [V] Panou 2,8″ rotund ST7701S gol (activ 70,13, contur 73 × 77,59 × 2,3, $11,50): https://www.twoyas.com/collections/lcd-display/products/2-8-inch-round-tft-lcd-module-screen-480-480-rgb-ic-st7701s
- [V] LilyGO T-RGB (2,1″ / 2,8″, ST7701S, touch CST820 / FT3267 / GT911): https://lilygo.cc/products/t-rgb
- [V] Makerfabs MaTouch 2.1 Rotary ($38,80, ST7701S, CST8266): https://www.makerfabs.com/matouch-esp32-s3-rotary-ips-display-with-touch-2-1-st7701.html
- [V] Elecrow, displayuri rotunde (toate IPS, maxim 2,8″): https://www.elecrow.com/display/esp-hmi-display/round-rotary-display.html
- [V-s] Viewe 1,75″ AMOLED rotund 466²: https://viewedisplay.com/product/1-75-inch-466x466-round-amoled-display-with-touch-screen/ · Viewe 2,1″ TFT rotund: https://viewedisplay.com/product/2-1-inch-480x480-round-tft-hdmi-touch-display/
- [V] YOURITECH, displayuri rotunde 1,28–2,1″ (AMOLED doar ≤ 1,4″, 2,1″ = TFT): https://www.youritech.com/products/1-28-2-1-inch-circular-round-displays/
- [V-s] AMOLED 1,96/2,06/2,13″ 410×502 (dreptunghiulare), căutare generală „round AMOLED 1.96–2.06″
- [V-s] LilyGO T4-S3 2,41″ AMOLED 450×600 RM690B0: https://www.cnx-software.com/2023/12/27/lilygo-t4-s3-board-2-41-inch-amoled-touchscreen-display-esp32-s3r8/
- [V] Web Bluetooth (fără iOS Safari; Chrome Android da; extensia iOSWebBLE): https://caniuse.com/web-bluetooth
- [V] ESP-IDF `esp_hid_host` (BLE HID host, include ESP32-S3): https://github.com/espressif/esp-idf/tree/master/examples/bluetooth/esp_hid_host
- [V local] `firmware/platformio.ini`, `firmware/README.md`, Arduino_GFX 1.6.8 în `firmware/.pio/libdeps/amoled143/GFX Library for Arduino/src/display/` (`Arduino_RGB_Display.h`: st7701_type1–9; `Arduino_DSI_Display.h`: jd9365; `Arduino_CO5300`); `os/research/04-keyboard-design-familiar.md` §1, §12.
