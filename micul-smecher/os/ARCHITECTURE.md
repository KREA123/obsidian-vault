# SoulOS: arhitectura sistemului de operare

*v0.1 · 24 sept. 2026 · pentru fondator și pentru viitoarea echipă de ingineri. Surse: `os/research/01-text-input.md`, `02-os-architecture.md`, `03-code-map.md`, `os/SPEC.md`, `research/06`. Marcaje: **[V]** = verificat (cod local, documentație oficială), **[E]** = estimare. Căile de fișiere sunt relative la rădăcina proiectului.*

---

## 1. Ce e SoulOS

SoulOS e sistemul de operare al lui SOUL. E construit după aceeași idee ca iOS: **straturi** care se sprijină unul pe altul (hardware → kernel → drivere → servicii de sistem → framework de aplicații → aplicații), iar lucrurile importante le face **sistemul, nu aplicația**. Tastatura, notificările, alarmele, stocarea, energia, legătura cu AI-ul și permisiunile sunt **servicii de sistem**. O aplicație doar cere („dă-mi un text”, „pune o alarmă la 7”, „arată cartonașul ăsta”) și primește rezultatul. Aplicațiile de sistem (Notițe, Alarme, Claude…) sunt scrise cu același framework (**SoulKit**) pe care îl vor folosi mai târziu și aplicațiile altor dezvoltatori, care vor rula izolat într-o mașină virtuală. Diferența față de iOS e de scară: SOUL are un microcontroler cu 512 KB RAM, nu un procesor cu gigaocteți. De aceea SoulOS e **o singură imagine semnată**, cu o singură aplicație în prim-plan, fața pe post de ecran de pornire și un API mic, stabil și versionat.

| iOS / watchOS | SoulOS |
|---|---|
| XNU + launchd | FreeRTOS SMP în ESP-IDF 5.5 |
| IOKit (drivere) | BSP: display, touch, IMU, RTC, PMU, audio, radio |
| SpringBoard + Core Animation | Shell + Compositor (Window/Card manager) |
| UIKit / SwiftUI | SoulKit |
| App Intents + Siri | Intents + AI Service |
| tastatura sistemului (proces separat) | Text Input / IME: aplicația primește doar textul final |
| App Store | catalog în aplicația de telefon (faza 2) |

---

## 2. Straturile

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ 7 APLICAȚII TERȚE (faza 2)  mods JavaScript în Moddable XS · sandbox SES           │
│   doar API SoulKit + capabilitățile declarate · 32–64 KB PSRAM per aplicație       │
├────────────────────────────────────────────────────────────────────────────────────┤
│ 6 APLICAȚII DE SISTEM  Acasă/Față · Azi · Vorbește · Tastatură · Claude · Notițe · │
│   Mementouri · Alarme · Focus · Jurnal · Traduce · Muzică · Setări (C++ nativ)     │
├────────────────────────────────────────────────────────────────────────────────────┤
│ 5 SOULKIT (framework)  Card · List · TextField · Keyboard · TimePicker · Face ·    │
│   Chip · Ring · manifest{caps, intents, triggers} · ciclu enter/exit/suspend       │
├────────────────────────────────────────────────────────────────────────────────────┤
│ 4 SERVICII DE SISTEM (fiecare are un singur proprietar; vorbesc prin magistrala)   │
│   Window/Card manager (Shell + Compositor, straturi, tranziții)                    │
│   Input (touch, buton, IMU, gesturi) · Text Input/IME (tastatură, predicție EN/RO, │
│     dictare, tastatura telefonului, TimePicker)                                    │
│   Notificări (niveluri, nu deranja, pastilă/inel) · Timp & Alarme (RTC, TZ/DST)    │
│   Stocare (documente CBOR, sync, outbox) · Energie (stări, somn, baterie)          │
│   Conectivitate (SoulOS Link, Claude Buddy, ANCS/AMS/CTS, Wi-Fi)                   │
│   AI Service: fără AI │ conector Claude │ app ChatGPT │ cheie API │ voce SOUL      │
│   Permisiuni (capabilități + consimțământ) · Update OTA (A/B) · Personaj (Brain)   │
├────────────────────────────────────────────────────────────────────────────────────┤
│ 3 DRIVERE (BSP)  display CO5300 QSPI · touch CST9217 / FT3168 · IMU QMI8658 ·      │
│   RTC PCF85063 · PMU AXP2101 · audio ES8311 + ES7210 (I2S) · haptic · BLE · Wi-Fi  │
├────────────────────────────────────────────────────────────────────────────────────┤
│ 2 KERNEL  FreeRTOS SMP (2 nuclee) în ESP-IDF 5.5 · esp_pm · heap_caps · LittleFS · │
│   NVS · mbedTLS · esp_ota · bootloader (Secure Boot v2, flash encryption, A/B)     │
├────────────────────────────────────────────────────────────────────────────────────┤
│ 1 HARDWARE  ESP32-S3 (2×240 MHz, 512 KB SRAM, 8 MB PSRAM, 16 MB flash) ·           │
│   AMOLED 1,75" 466×466 · touch · IMU · RTC · PMU · 2 microfoane + difuzor · buton  │
└────────────────────────────────────────────────────────────────────────────────────┘
  Telefon (aplicația SOUL): pairing, tastatură lungă, backup, conturi AI, releu, OTA
  Cloud SOUL: serviciul de voce (STT → LLM → TTS), server MCP (conector Claude + app ChatGPT)
  Desktop: Claude Code / Cowork prin Hardware Buddy (BLE direct, deja în firmware)
```

**Reguli:**
- Un strat folosește doar stratul de sub el. Aplicațiile nu ating drivere. Serviciile nu desenează pe panou; desenează doar Compositorul.
- Inelul gheață (microfon pornit) și inelul chihlimbar se desenează **peste** orice aplicație. Nicio aplicație nu le poate ascunde.
- Butonul lateral e al sistemului: apăsare = acasă, ținut = vorbești (într-un câmp text: dictezi), dublu = înapoi.
- **Rutarea unei atingeri:** cerere de permisiune → tastatură (dacă e deschisă) → suprapunere → cartonaș → Shell (glisări) → Brain (reacțiile feței).

**API de sistem** (schiță; aceleași nume în C++ pentru aplicațiile de sistem și în JS pentru mods):
```
text.request({kind:text|number|time|date, prompt, initial, lang:auto|ro|en, suggestions[], maxLen})
                                                      → TextCommit{utf8} | TextCancel
alarm.set({hhmm, days, label}) · reminder.create({when, text}) · note.create({text})
notify.post({level:passive|active|timeSensitive|critical, title, body, actions[]})
store.put / get / query(collection, record)            // doar colecțiile din manifest
ai.ask({text | audio, target:auto|claude|chatgpt})     → {say, card, face, chips, tool}
card.present(Card) · timeline.push(entries[]) · face.express(reaction) · haptic.play(pattern)
```

**Buget de memorie** [E, de măsurat pe placă]:

| Resursă | Consum | Unde |
|---|---|---|
| 2 framebuffere 466×466 RGB565 (desen + push/rotire) | 2 × 434 KB | PSRAM (există) [V] |
| Strat cache pentru cartonaș / tastatură | 434 KB | PSRAM |
| Fonturi 4bpp (22/27/34 px + cifre de 104 px), EN+RO | ~180 KB | flash (mmap) |
| Dicționare EN+RO (20k cuvinte fiecare) + bigrame | < 1 MB | flash; set de lucru < 100 KB |
| NimBLE · audio (buffer microfon + Opus) | ~60 KB · ~40 KB | SRAM intern |
| Mașină XS per aplicație terță | 32–64 KB | PSRAM |
| **Total PSRAM** | **~1,5–2 MB din 8 MB** | resursa rară e SRAM-ul intern (512 KB) |

---

## 3. Deciziile de arhitectură

**D1 · Kernel: ESP-IDF 5.5 + FreeRTOS SMP, o singură imagine semnată, UI pe nucleul 1.**
- *Decizie:* trecem de pe Arduino (azi un singur `loop()`) pe ESP-IDF cu `sdkconfig` propriu. Pasul intermediar e pioarduino `framework = arduino, espidf`. Nucleul 0 rulează radio (NimBLE, Wi-Fi), audio, Link și Store. Nucleul 1 rulează UI-ul (Shell, Brain, Compositor), singurul task care atinge Canvas și panoul.
- *Motiv:* bibliotecile Arduino precompilate au dezactivate `PM_ENABLE` (somn automat), `SPIRAM_XIP_FROM_PSRAM`, `NVS_ENCRYPTION` și `APP_ANTI_ROLLBACK` [V]. Fără ele nu avem baterie, date criptate și update sigur. Izolarea hardware între procese (ESP Privilege Separation) e încă beta pe S3 [V], deci nu o folosim în v1.
- *Alternative:* Zephyr (folosit de ZSWatch; ar trebui refăcute driverele și integrarea S3); rămânem pe Arduino (imposibil, din motivul de mai sus); Linux (nu rulează pe ESP32).
- *Cost:* 3–5 săptămâni de migrare [E]. Tot codul nativ din imagine e „de încredere”: un bug de sistem poate bloca tot, deci review, teste și watchdog.

**D2 · Renderer propriu (Canvas SDF + TextEngine + Compositor), nu LVGL.**
- *Motiv:* fața, care e produsul, e deja scrisă pe Canvas SDF, anti-aliased, cu dirty-rect [V]. Ecranele SoulOS au cel mult 3 rânduri, deci ajunge un set mic de widgeturi. Avem un singur pipeline de desen pentru față și UI. Costul e ~60 KB cod + ~180 KB fonturi [E]. LVGL cere ≥ 64 KB flash (180 KB recomandat) și ≥ 48 KB heap recomandat [V], plus fața portată ca widget.
- *Alternative:* LVGL 9 (are text, textarea și tastatură gata făcute; rămâne plan B dacă Setările de pe device devin complexe); Slint/TouchGFX (nu aduc nimic pentru un ecran rotund cu 3 rânduri).
- *Cost:* construim TextEngine (UTF-8, atlase 4bpp, fallback Fredoka → Nunito pe fiecare glifă pentru ă ș ț, rânduri încadrate în cerc cu lățimea = coarda 2·√(r²−y²)), Compositorul cu straturi (față, cartonaș, suprapunere, tastatură, pastilă, inele de sistem), DMA și dublu buffer. 4–6 săptămâni [E].

**D3 · IPC: magistrală de mesaje tipizate (pub/sub), nu apeluri directe.**
- *Decizie:* `Msg{topic:u16, src, corr_id, payload ≤ 48 B inline | referință în PSRAM}` pe cozi FreeRTOS, câte o coadă per serviciu. Cererile au răspuns legat prin `corr_id` și timeout. Topicurile se generează dintr-un singur fișier de schemă, care produce headerul C++, schema CBOR pentru telefon și stub-urile JS pentru mods. Magistrala crește din `Ev`/`EvQueue` de azi (26 de evenimente fără payload [V]).
- *Motiv:* servicii decuplate, testabile pe PC, și un singur loc unde se verifică permisiunile (cine are voie să publice sau să asculte un topic). Același model îl folosesc ZSWatch (zbus) și Flipper (records) [V].
- *Alternative:* `esp_event` din IDF (îl folosim doar la margine, pentru Wi-Fi/IP, pentru că e netipizat și alocă dinamic); apeluri directe între module (ca azi; nu scalează și nu se pot filtra pe permisiuni).
- *Cost:* o copie per mesaj, ~1–2 KB RAM per coadă [E] și disciplină la schemă.

**D4 · Text Input e serviciu de sistem: tastatura e a sistemului, nu a aplicației.**
- *Decizie:* aplicația cheamă `text.request()` și primește doar textul final; nu vede tastele. Toate metodele stau în aceeași foaie de compunere: tastatura de pe ecran (EN/RO), dictarea (ții butonul; STT în cloud, doar cu AI), tastatura telefonului prin BLE, răspunsuri rapide (3 chipuri) și, mai târziu, tastatură Bluetooth (HID). Pentru ore și date există un selector rotund (TimePicker), fără litere. IME-ul nu are acces la rețea, iar predicția rulează pe device.
- *Tastatura:* un motor cu layouturi încărcabile. Implicit e **QWERTY rotund**: 3 rânduri în banda cea mai lată, taste de 4,3–4,5 mm (46–48 px, ~40% mai late decât pe un Apple Watch de 45 mm) [E], decodor probabilistic (model de atingere gaussian × model de limbă, confirmare la ridicarea degetului). Varianta „Halo” (inel pe margine, ochii rămân vizibili; SwipeRing a măsurat 16,7 WPM [V]) se testează în prototip cu 5–8 oameni înainte de firmware. **T9 cu taste mari** (10,3×7,7 mm) rămâne opțiunea de accesibilitate.
- *Diacritice:* auto-diacritice (scrii „sa”, primești „să” când bigrama e sigură; alegerea celei mai frecvente forme dă ~94% cuvinte corecte, iar modelele mici publicate ajung la 97–98,6% [E/V]). Apăsarea lungă pe a/i/s/t oferă ă â / î / ș / ț, iar atingerea pe un cuvânt ciclează variantele. Stocăm ș ț cu virgulă (U+0219/U+021B), normalizăm sedila și păstrăm textul în UTF-8 NFC.
- *Motiv:* fără AI și fără net, tastatura e singura cale de a scrie. ESP-SR recunoaște offline doar ≤ 200 de comenzi în engleză și chineză, fără dictare și fără română [V]. E modelul watchOS [V] și protejează intimitatea.
- *Alternative:* fiecare aplicație cu tastatura ei (inconsecvent, risc de scurgeri de text); doar voce (nu merge offline și nu merge în română pe device).
- *Cost:* dicționare EN+RO < 1 MB flash, decodor < 1 ms per tastă [E]. Listele de cuvinte trebuie să aibă licență potrivită (FrequencyWords e CC-BY-SA [V]), deci construim un corpus propriu. Tastatura, decodorul și testele cer 6–8 săptămâni [E].

**D5 · Intents + AI Service: un singur API de acțiuni, cinci moduri AI.**
- *Decizie:* fiecare aplicație declară în manifest acțiuni tipizate (`alarm.set{hhmm,days,label}`, `note.create{text}`, `reminder.create{when,text}`, `timer.focus{min}`, `today.set{items}`…). UI-ul, tastatura, vocea și orice AI cheamă aceleași intents. Schemele de unelte pentru LLM se generează din manifeste. AI Service (broker-ul) alege ruta după mod:

| Mod | Sens | „Scriu lui Claude” de pe SOUL | Unde stă cheia |
|---|---|---|---|
| Fără AI (implicit) | — | textul ajunge în Notițe / outbox; o gramatică locală RO/EN înțelege „mâine la 7” | — |
| Conector Claude (serverul MCP SOUL, adăugat în Claude-ul tău) | AI → SOUL | mesajul intră în inbox-ul SOUL; Claude îl citește cu o unealtă când îi ceri, iar răspunsul vine ca un cartonaș | contul tău Claude + OAuth la contul SOUL |
| Aplicație în ChatGPT (același server MCP) | AI → SOUL | la fel | contul tău ChatGPT |
| Cheie API proprie (Anthropic / OpenAI) | SOUL → AI | conversație directă, text și voce | Keychain/Keystore pe telefon, niciodată pe SOUL |
| Serviciul de voce SOUL | SOUL → AI | conversație directă, text și voce (Claude implicit) | cloud SOUL; device-ul are doar tokenuri de sesiune |
| În paralel: Claude Code / Cowork (Hardware Buddy) | desktop → SOUL | doar aprobi sau refuzi; protocolul nu transportă text [V] | — |

- *Motiv:* abonamentele de consum Claude/ChatGPT nu pot fi folosite direct de un dispozitiv terț, așa că modurile 2 și 3 merg invers: AI-ul tău cheamă SOUL. Toate modurile produc același răspuns structurat `{say, card, face, chips, tool}`, deci aceleași ecrane și aceleași teste, cu un LLM simulat.
- *Alternative:* câte o integrare separată pentru fiecare AI (de 5 ori mai mult cod și comportament diferit); cheia API pe device (se poate extrage dintr-un device pierdut).
- *Cost:* server MCP, OAuth și inbox în cloud; review la OpenAI pentru aplicația ChatGPT [E]. Latența „AI → SOUL” depinde de telefon (BLE) sau de Wi-Fi.

**D6 · Runtime pentru aplicații terțe: Moddable XS (JavaScript) în SES Compartments; WAMR e planul B. v1 nu rulează cod terț.**

| Runtime | Flash (motor) | RAM minim per aplicație | Limbaj | Sandbox | Licență |
|---|---|---|---|---|---|
| **Moddable XS (mods)** | câteva sute de KB [E]; bytecode `.xsa` rulat direct din flash [V] | **32 KB** mașină per aplicație (precedent pe ceas) [V] | JavaScript modern | SES Compartments: doar modulele permise, primordiale înghețate [V] | core Apache-2.0; runtime Moddable LGPLv3; licență comercială disponibilă [V] |
| WAMR (WebAssembly) | ~56–59 KB interpretor, ~29 KB runtime AOT [V] | 64 KB (o pagină de memorie Wasm) + stivă [E] | C, Rust, Zig, AssemblyScript | limitele memoriei liniare; importuri controlate | Apache-2.0 |
| Berry / Lua 5.4 | ~40 KB / 100–200 KB [E] | ~10 KB [V] / ~20 KB [E] | Berry / Lua | mediu restrâns, alocator limitat; slab | MIT |
| JerryScript | ~160 KB [V] | < 64 KB [V] | JS din era ES5.1 | doar realm; slab | Apache-2.0 |

- *Motiv:* memoria nu decide, pentru că toate încap: cu o aplicație în prim-plan și un worker, XS folosește ≤ 128 KB din 8 MB PSRAM, iar codul nu ocupă RAM, fiindcă rulează din flash. Decid trei lucruri. (1) Sandbox real: `soul/store` e limitat la colecția aplicației, `soul/net` doar la hosturile declarate, `soul/ui` înseamnă doar SoulKit. (2) JavaScript e limbajul pe care Claude îl scrie cel mai bine și limbajul prototipului web, deci „Claude îți face o aplicație pentru SOUL” devine realist. (3) Precedent: ceasurile Core Devices (Time 2 / Round 2, clasa 512 KB RAM) au trecut în 2025–26 de la JerryScript la XS, cu o mașină de 32 KB per aplicație [V].
- *Alternative:* WAMR (licență curată și orice limbaj, dar pagina de 64 KB și un toolchain greu pentru ne-programatori); Berry/Lua (cele mai mici, dar sandbox slab și ecosistem mic); JerryScript (vechi, abandonat de precedentul de mai sus); MicroPython (~1,6 MB flash, fără izolare între aplicații [V]).
- *Cost:* fișierele modificate de Moddable sunt LGPLv3, iar obligația de re-link intră în conflict cu secure boot blocat. Soluția e o **licență comercială Moddable**, negociată înainte de faza 2; altfel trecem pe WAMR [E]. Mai trebuie watchdog CPU pe fiecare felie de timp.

**D7 · Formatul aplicațiilor și versiunea API.**
- *v1:* fără cod. Telefonul sau cloud-ul trimit cartonașe și rânduri de timeline declarative (CBOR/JSON), ca Wear OS Tiles / WidgetKit.
- *Faza 2:* pachetul `.soul` = manifest CBOR + bytecode `.xsa` + resurse (texte RO/EN, pictograme vectoriale). E semnat ECDSA P-256 de dezvoltator și contrasemnat de catalogul SOUL. Se instalează în partiția `mods` (1 MB) și rulează din flash.
```
id "ro.exemplu.plante"   version "1.0.2"   api "1.0"    // major diferit = refuzat la instalare
name {ro "Plante", en "Plants"}
caps [store:plants, notify:active, net:api.exemplu.ro, ai:optional]
intents [plant.water{name:string}]   triggers [time "daily 09:00"]
```
- *Motiv:* un tabel de API versionat major.minor, ca la Flipper, face ca aplicațiile vechi să supraviețuiască update-urilor [V]. O aplicație declarativă nu consumă nimic cât nu rulează.
- *Alternative:* ELF nativ relocat (ca Flipper `.fap`), rapid, dar fără sandbox pe S3.
- *Cost:* compatibilitatea API trebuie întreținută, plus infrastructura de semnare și catalogul.

**D8 · Stocare & criptare.**
- *Decizie:* documentele stau pe **LittleFS** în partiția `store`, ca înregistrări CBOR `{id ULID, rev, updated_at, deleted, body}`. Colecții: `notes/ reminders/ alarms/ diary/ outbox/ dict/ settings`. Sincronizarea cu telefonul e last-writer-wins după `rev`, iar outbox-ul păstrează ce așteaptă conexiune. Secretele mici (setări, legături BLE, tokenuri) stau în **NVS criptat**. **Flash encryption** XTS-AES-256 acoperă și traficul PSRAM prin cache [V]. Alarmele se salvează ca oră locală + recurență + regulă TZ POSIX (EET/EEST), iar următoarea declanșare se calculează în UTC. Scrierile se grupează și se fac când ecranul e liniștit, fiindcă scrierea în flash oprește cache-ul și UI-ul sacadează.
- *Harta de partiții propusă (16 MB) [E]:* `nvs 64K · nvs_keys 4K · otadata 8K · ota_0 4M · ota_1 4M · mods 1M · store ~6,8M · coredump 64K`. Azi e `default_16MB.csv`: 2 × 6,25 MB app + 3,4 MB SPIFFS nefolosit [V].
- *Motiv:* LittleFS rezistă la căderi de curent și are wear levelling; CBOR e compact și identic pe telefon.
- *Alternative:* FAT + wear levelling (metadatele nu rezistă la căderi de curent); SPIFFS (învechit); SQLite (prea mult RAM pentru ecrane cu 3 rânduri); doar NVS (numai chei mici).
- *Cost:* LittleFS pe partiție criptată trebuie verificat (aliniere la 16 B, viteză) [E]. Last-writer-wins poate pierde o editare simultană, ceea ce e acceptabil în v1.

**D9 · Update OTA A/B cu rollback.**
- *Decizie:* sloturile `ota_0`/`ota_1` + `otadata`. Imaginea nouă pornește „în verificare” și rulează un self-test: citește ID-ul panoului, verifică touch-ul, montează Store, pornește advertising BLE și rulează 30 s fără panic. Abia apoi cheamă `esp_ota_mark_app_valid_cancel_rollback()`; altfel bootloader-ul revine la imaginea veche [V]. Fonturile, dicționarele și sunetele sunt în aceeași imagine, deci se actualizează atomic. Telefonul descarcă imaginea semnată și o trimite prin BLE (L2CAP CoC, bucăți de 4 KB, reluabil), iar acasă se poate folosi Wi-Fi. Anti-rollback prin eFuse doar pentru reparații de securitate, pentru că biții sunt limitați [V].
- *Alternative:* un singur slot + recovery (risc de device mort); resurse într-o partiție separată (update neatomic).
- *Cost:* 8 MB din 16 MB sunt rezervați celor două sloturi. Transferul unei imagini de ~3 MB prin BLE durează 1–2 min [E].

**D10 · Secure boot și lanțul de încredere.**
- *Decizie:* Secure Boot v2 (pe S3: RSA-3072 / RSA-PSS, până la 3 chei revocabile, verificare la fiecare pornire și la fiecare OTA) [V] + flash encryption în modul release + NVS criptat + JTAG oprit + secure download mode. Cheia de semnare stă într-un HSM. Plăcile de dezvoltare rămân deschise; unitățile de producție primesc cheile în fabrică. Cheile AI nu ajung niciodată pe device.
- *Alternative:* fără secure boot (oricine poate instala un firmware care copiază notițele și jurnalul, deci promisiunea de intimitate nu mai stă în picioare); doar secure boot, fără flash encryption (notițele se citesc direct din cip, iar imaginea poate fi înlocuită între verificare și rulare) [V].
- *Cost:* eFuse-urile sunt ireversibile, deci o greșeală strică unități. Mai costă un pas de provizionare în fabrică, depanare și service (RMA) mai grele, plus conformitatea LGPL (D6).

**D11 · Modelul de permisiuni.**
- *Decizie:* capabilitățile se declară în manifest, iar pentru cele sensibile se cere consimțământ la prima folosire: `mic`, `net:<host>`, `ai` (conținutul pleacă la un furnizor AI), `notify:<nivel>`, plus `store:<colecție>`, `alarm`, `sensors`. Verificarea se face la granița serviciului: magistrala verifică capabilitățile expeditorului. Pe device, consimțământul e un chip „Permiți? Da / Nu”; detaliile și revocarea sunt în Setări și în aplicația de telefon. Aplicațiile de sistem primesc și ele doar ce le trebuie: Tastatura nu are rețea, Notițele nu au microfon fără cerere. Inelul gheață apare de fiecare dată când ajunge audio la I2S, iar microfonul e oprit din hardware prin buton (SPEC §7). În aplicația de telefon există un **jurnal de ieșire**: ce a plecat de pe SOUL, când și către ce AI.
- *Alternative:* totul sau nimic, la instalare (vechiul model Android); aplicațiile de sistem fără permisiuni (inconsecvent și greu de auditat).
- *Cost:* în v1 codul nativ nu e izolat (nu există MMU), deci permisiunile protejează doar de aplicațiile din VM și de bug-uri. Ca să nu enerveze, cererea apare la prima folosire, nu la instalare.

**D12 · Energie: patru stări, deținute de serviciul Energie.**

| Stare | Ecran | CPU | Radio | Intră când | Trezire |
|---|---|---|---|---|---|
| Activ | 30 fps | 240 MHz | BLE 15–30 ms | atingere, buton, ridicare | — |
| Liniște | fața adormită, 2–10 fps, luminozitate 110/255 [V] | DFS 80–160 MHz | BLE 50–100 ms | 15 s fără atingere pe cartonaș; fața adoarme după 20 s (SPEC) | atingere, buton, notificare |
| Ecran stins | panou în SLPIN | light sleep automat | BLE păstrat, ≥ 200 ms | cu fața în jos, nemișcat câteva minute [E], noaptea, baterie < 10% | touch INT (1.75), buton (IRQ PMU), ridicare (dacă IMU INT e cablat), alarmă RTC, mesaj BLE |
| Oprit | stins | deep sleep / PMU oprit | oprit | buton ținut 4 s (deja setat în PMU [V]) | buton, alarmă RTC |

- **Alarmele sună din orice stare:** următoarea alarmă stă în memoria RTC, în alarma PCF85063 și într-un timer ESP. Nivelul „critical” trece peste nu deranja, cu difuzor și haptic.
- *Buget pe 1000 mAh [E]:* ambient 12–18 mA × 10 h, activ 70–100 mA × 1 h, voce 200–300 mA × 20 min, în buzunar 3–6 mA × 5 h, noaptea 1–3 mA × 8 h. Totalul e ~360 mAh/zi, deci ~2,5 zile tipic și 1–1,5 zile la folosire intensă. Criteriul minim din SPEC e 18 h.
- *Motiv:* AMOLED-ul e cel mai mare consumator, iar pixelii negri consumă aproape zero. Light sleep păstrează BLE [V].
- *Alternative:* fața mereu aprinsă (mai drăguț, dar ~1,5× consum [E]); deep sleep între interacțiuni (pierde BLE și se trezește greu).
- *Cost:* depinde de D1. Pe schema plăcii 1.75 trebuie verificate: rutarea IMU_INT și RTC_INT (ambele −1 în `board.h` [V]), cristalul de 32 kHz (necesar pentru BLE în light sleep) și driverul haptic. Consumul se măsoară cu un analizor de curent.

---

## 4. Aplicațiile de sistem v1

| Aplicație | Ce face | Servicii / API | Fără AI |
|---|---|---|---|
| **Acasă / Față** | ochii vii, ceasul, o etichetă de stare | Face, Brain, Input (bup, râs, privire), Notify (eticheta), Time | da |
| **Azi** | următorul memento, vremea, Claude, bateria | `timeline` (Store), Time, Energie, Link (vreme și calendar de la telefon), ClaudeLink | parțial (fără vreme) |
| **Vorbește** | ții apăsat și întrebi, sau scrii | Voice (I2S, Opus), `ai.ask`, `text.request`, Face (ascult / mă gândesc / răspund) | nu: „Nu am AI acum” și propune Notițe |
| **Tastatură** | foaia de compunere a sistemului | Text Input: layouturi EN/RO, decodor, dicționar personal (`store:dict`), `text.push` de la telefon, dictare (cu AI), TimePicker; **fără rețea** | da |
| **Claude** | aprobi / refuzi cererile Claude Code și Cowork; îi scrii lui Claude | ClaudeLink (Buddy BLE), Notify chihlimbar, `text.request` → `ai.ask{target:claude}` (ruta după mod, D5) | aprobarea da; scrisul doar cu AI |
| **Notițe** | scrii sau dictezi; notițele ajung pe telefon | `text.request`, Voice, `store:notes`, sync; `note.create/append/list` | da |
| **Mementouri** | ce urmează azi; atingerea bifează | `store:reminders`, Time (planificator), Notify time-sensitive, TimePicker + etichetă, gramatică RO/EN locală; `reminder.create/list/done` | da |
| **Alarme** | trezire, repetare pe zile, amânare | Timp & Alarme (RTC + timer, din orice stare), difuzor + haptic, Notify critical (trece de nu deranja), TimePicker; `alarm.set/list/cancel` | da |
| **Focus** | timer de 25 min cu inel | Time, Notify (filtru nu deranja), Face (progres), haptic; `timer.focus` | da |
| **Jurnal** | ziua ta, în rânduri scurte | `store:diary`, evenimentele din Brain, rezumat AI opțional; `diary.read` | da (rânduri din șabloane) |
| **Traduce** | RO ⇄ EN, vorbit sau scris | Voice, `text.request`, `ai.ask{task:translate}`, TTS | nu |
| **Muzică** | telecomandă pentru telefon | AMS (iOS) / Link (Android); `media.control` | nu are nevoie de AI, dar are nevoie de telefon |
| **Setări** | luminozitate, limbă, AI, tastatură, memorie, permisiuni, update | Settings (NVS criptat), Permisiuni, Energie, AI Service, Update OTA, Brain (Memorie: vezi / șterge) | da |

---

## 5. Aplicația de telefon (companion) și protocolul BLE

**Ce face (iOS și Android):**
1. **Pairing.** SOUL arată 6 cifre. LE Secure Connections cu *numeric comparison*: aceleași cifre apar pe ambele ecrane și confirmi pe amândouă. Legătura (bond) se salvează criptat în NVS. Urmează `hello` (versiune de protocol, API, placă, id). Contul SOUL e opțional.
2. **Tastatura lungă.** Pe SOUL alegi „Scrie pe telefon”. Telefonul deschide un câmp text, fiecare modificare pleacă drept `text.push{partial}` și apare live pe SOUL, iar „Gata” trimite `commit`. Merge în orice `text.request`.
3. **Backup și sync.** Colecțiile Store (notițe, mementouri, alarme, jurnal, dicționar personal) se sincronizează după `rev`. Backup-ul e criptat pe telefon și, opțional, în contul SOUL, criptat cu o cheie a utilizatorului.
4. **Conturi AI.** Alegi modul (D5). Pentru Claude sau ChatGPT: te conectezi la contul SOUL (OAuth), apoi aplicația te ghidează să adaugi conectorul sau aplicația. Pentru cheie API: cheia stă în Keychain/Keystore, iar apelurile pleacă de pe telefon. Pentru serviciul de voce: abonamentul.
5. **În plus:** ora și fusul orar, vremea și calendarul pentru Azi, notificările (pe Android le trimite aplicația; pe iOS le ia SOUL direct prin ANCS), Muzică, update OTA, Wi-Fi pentru voce acasă, setările lungi, permisiunile, jurnalul de ieșire și releul audio când SOUL nu are Wi-Fi.
- *Tehnologie [E]:* Flutter pentru interfață, cu un strat nativ (Swift/Kotlin) pentru BLE în fundal, audio și Keychain.

| Serviciu GATT | Rolul SOUL | Caracteristici | Pentru |
|---|---|---|---|
| **SoulOS Link** (UUID propriu, 128 biți) | periferic | `info` (read: versiuni, placă, id) · `ctrl_rx` (write fără răspuns) · `ctrl_tx` (notify) · `audio_up` (notify, Opus 16 kb/s) · `audio_down` (write, TTS) · `bulk` = canal L2CAP CoC (fallback GATT) | tot ce face aplicația |
| **Claude Buddy** (UUID-uri NUS, linii JSON, passkey) | periferic | RX write / TX notify | Claude Desktop (Code, Cowork); **neschimbat** |
| Battery 0x180F · Device Information 0x180A | periferic | standard | baterie, versiuni |
| ANCS · AMS · Current Time (iOS) | client GATT | — | notificări, muzică și oră **fără aplicația noastră** |
| HID (mai târziu) | central | — | tastatură Bluetooth fizică |

Legătura folosește MTU 247–512, PHY 2M și DLE pentru audio și OTA. Toate mesajele de pe SoulOS Link au același format de cadru:
```
Cadru CBOR: {v:1, t:"<tip>", id:u32, re:<id cerere>?, b:{…}}      // câmpurile necunoscute se ignoră
hello / caps                 versiuni protocol + API, placă, baterie, limbă
time.sync                    epoch UTC + TZ POSIX (ex. "EET-2EEST,M3.5.0/3,M10.5.0/4")
text.push                    {partial | commit | cancel, utf8}             // tastatura telefonului
intent.call / intent.result  {name:"alarm.set", args:{…}} → {ok, card}
store.sync                   {coll, since_rev} → înregistrări CBOR (last-writer-wins)
card.push / timeline.push    cartonașe și rânduri Azi, declarative
notify.post                  notificări filtrate de telefon (Android)
ai.ask / ai.reply            text → {say, card, face, chips, tool}
audio.start / audio.stop     Opus pe audio_up; TTS pe audio_down
ota.begin / chunk / end      imagine semnată, bucăți de 4 KB, reluabil
```

---

## 6. Ce există deja vs ce trebuie construit

**Pe scurt:** din SoulOS 1.0 există azi cam **10%** [E]: personajul (fața, Brain, 24 de reacții), gesturile de bază, protocolul Claude Buddy, simulatorul, testele și prototipul web al experienței. Restul se construiește.

| Componentă | Există azi (cod) [V] | De construit |
|---|---|---|
| Fața + personajul | `Face` (parametric, SDF), `Brain` (1085 de linii: dispoziție, 24 de reacții, somn), `Personality` | `FaceLayout{k,cy}` (fața mică în antet); cues → haptic și audio |
| Renderer | `Canvas` SDF RGB565 cu dirty-rect. Fără text, imagini și dreptunghiuri rotunjite; `fillRect` nu marchează dirty, `blend` nu verifică limitele | TextEngine, Compositor cu straturi, DMA + dublu buffer |
| Text pe ecran | doar fontul 5×7 ASCII din Arduino_GFX: pixelat, măsoară greșit UTF-8, nu apare în sim | tot: `make_font.py`, UTF-8, fallback, încadrare în cerc |
| Input | `TouchGestures` (tap, dublu, ținut, mângâiere; citit o dată pe cadru), `MotionDetector` (ridicare, scuturare, cu fața în jos…) | glisări direcționale, coordonate în eveniment, butonul lateral, timpi unificați (ținut 380 ms, dublu 330 ms; azi 0,5 s / 0,4 s), dublu-tap care nu înghite tastarea |
| Evenimente / IPC | `Ev` (26 de valori fără payload), `EvQueue<8>`; totul ajunge la Brain | magistrala `Msg` tipizată, rutare prin Shell |
| Window/Card manager | nu există (doar în prototipul web) | Shell, Card, suprapuneri, pastilă, inele |
| Text Input / tastatură | nimic | serviciul, 2–3 layouturi, decodor, dicționare, TimePicker, `text.push` |
| Timp & alarme | RTC citit și setat; o singură sincronizare de la Claude Desktop sau prin serial | fus orar + DST, sync de la telefon, planificator, alarme din orice stare |
| Stocare | NVS (Preferences) pentru memoria personajului; partiția SPIFFS de 3,4 MB nefolosită | Store pe LittleFS, sync, outbox, NVS criptat |
| Notificări | nimic | serviciul Notify, ANCS |
| Audio / haptic | nimic (ES8311/ES7210 nefolosite) | I2S, Opus, VAD, TTS, AEC; driver haptic |
| BLE | NUS + passkey LESC (`ble_link`), `ClaudeLink` (aprobă/refuză, oră, stare); numele BLE conține încă vechiul nume | SoulOS Link, ANCS/AMS/CTS, L2CAP pentru OTA; redenumire la SOUL |
| Wi-Fi | nimic | provizionare, WebSocket pentru voce |
| Energie | inițializare PMU (1.75), citire baterie, fps după starea personajului | stări, light sleep, ecran stins, treziri |
| OTA / secure boot | 2 sloturi app în harta Arduino; rollback activ în biblioteci; niciun cod OTA | D9, D10, noua hartă de partiții |
| Permisiuni | nimic | D11 |
| AI în cloud | `ai/` (Python): naștere personaj, conversație cu ieșire structurată, memorie, mementouri, jurnal; 9 teste care trec | voce (STT/TTS streaming), broker cu 5 moduri, server MCP + OAuth, conturi |
| Aplicația de telefon | nimic | tot (§5) |
| Prototip web | `os/index.html`: 9 aplicații + Azi + suprapuneri, RO/EN, demo scriptat | tastatură, Alarme, scris către Claude și în Notițe (pentru testele cu oameni) |
| Simulator și teste | `sim` (10 scene), `frames_to_media.py`, 24 de teste native care trec | atingeri cu coordonate, scene UI și tastatură, teste pentru fiecare serviciu nou |
| Aplicații terțe | nimic | faza 2 (D6, D7) |

---

## 7. Roadmap SoulOS 0.1 → 1.0

*Toate duratele sunt **estimări** [E] pentru lucru secvențial, cu hardware disponibil.*

| Versiune | Conținut | Durată [E] | Cine |
|---|---|---|---|
| **0.1 Shell** | FaceLayout, Shell + Card manager, glisări și buton cu coordonate, TextEngine + fonturi RO, widgeturi Text/Chip/List/Ring; Acasă, Azi (static), Focus, Setări locale; scene în sim | 4–5 săpt. | 1 dev + Claude |
| **0.2 Scriu** | test de tastatură în prototip (5–8 oameni), apoi Text Input (QWERTY rotund, decodor EN/RO, auto-diacritice), TextField, TimePicker; Store pe LittleFS; Notițe, Mementouri, **Alarme** offline (RTC, haptic, difuzor) | 6–8 săpt. | 1 dev + Claude, designer part-time pentru test |
| **0.3 Fundația** | migrare pe ESP-IDF, task-uri pe nuclee, magistrala `Msg`, serviciul Energie, harta nouă de partiții, OTA A/B cu self-test (USB/Wi-Fi), coredump | 5–7 săpt. | inginer firmware senior (solo + Claude se poate, cu risc) |
| **0.4 Legătura** | SoulOS Link, aplicația de telefon MVP (pairing, oră, tastatura telefonului, sync și backup, OTA prin BLE), ANCS/AMS/CTS, Muzică | 7–9 săpt. | + dezvoltator mobil |
| **0.5 Voce & AI** | audio I2S + Opus + VAD, inelul gheață, AI Service (fără AI / voce SOUL / cheie API), Vorbește, scris către Claude, Traduce, Jurnal; serviciul `ai/` extins cu voce | 7–9 săpt. | + backend/AI; firmware audio |
| **0.6 Conectori** | server MCP SOUL (OAuth, inbox, livrare spre device) pentru Claude și ChatGPT; permisiuni, consimțământ, jurnal de ieșire | 4–6 săpt. + review OpenAI | backend |
| **0.7 Securitate** | Secure Boot v2, flash + NVS encryption, provizionare în fabrică, politică anti-rollback, audit extern | 3–5 săpt. | firmware + consultant securitate |
| **0.8 Beta** | 50–100 de testeri, consum măsurat și optimizat, telemetrie opt-in, rapoarte de crash, accesibilitate (T9 mare), finisare RO/EN | 6–8 săpt. | toată echipa + QA |
| **1.0** | lansare cu Voice Edition; API-ul SoulKit 1.0 înghețat | 2–4 săpt. | toată echipa |
| 2.0 | aplicații terțe (XS), SDK + simulator pentru dezvoltatori, catalog în aplicația de telefon | 3–4 luni după 1.0 | echipa + relații cu dezvoltatorii |

- **Total [E]:** 0.1 → 1.0 înseamnă 44–61 de săptămâni de lucru. Cu o echipă care lucrează în paralel (mobil în timpul lui 0.3, backend în timpul lui 0.4), calendarul e de **~8–10 luni**. Un singur dezvoltator cu Claude are nevoie de **~14–18 luni** și se blochează la punctele de mai jos. Voice Edition e anunțată pentru toamna 2027 (~12 luni), deci **echipa trebuie să existe de la 0.3–0.4**.
- **Desk Edition (1.43", USB, fără audio, primăvara 2027)** are nevoie doar de 0.1, o parte din 0.3 (OTA, fără Energie) și 0.7. Asta e fezabil cu 1 dev + Claude + un consultant de securitate în ~5–6 luni [E].
- **Ce poate construi singur un dezvoltator + Claude:** tot codul portabil din `lib/` cu teste și sim (TextEngine, Shell, tastatura și decodorul, Store, Alarme, codecurile de protocol, registrul de intents), prototipul web, serviciul AI din cloud, un server MCP simplu și documentația.
- **Ce cere echipă sau specialiști:** optimizarea consumului cu măsurători pe hardware; BLE în fundal pe iOS/Android și publicarea în magazine; audio (AEC, latență); secure boot și provizionarea în fabrică (ireversibile); certificări; teste cu mulți oameni; operarea cloud-ului 24/7.
- **Echipa pentru 1.0:** lead firmware/arhitect SoulOS (ESP-IDF, energie, securitate), 1 normă din 0.3 · dezvoltator UI și input (TextEngine, Compositor, tastatură; poate fi dezvoltatorul actual + Claude) · dezvoltator mobil (iOS + Android, BLE, audio), 1 normă din 0.4 · backend/AI (voce, MCP, OAuth, găzduire în UE), 1 normă din 0.5 · designer de produs (mișcare, tastatură, teste), ½ normă · QA + măsurători, ½ normă din 0.8 · consultant de securitate, contract pentru 0.7. Adică **~4 oameni cu normă întreagă + 2–3 part-time**.

---

## 8. Riscuri tehnice principale

| # | Risc | Cum îl reducem |
|---|---|---|
| 1 | Tastatura pe Ø44 mm e prea greu de folosit | test A/B în prototipul web (WPM, erori) cu 5–8 oameni înainte de firmware; decodor + auto-diacritice; voce și tastatura telefonului ca alternative; T9 mare pentru accesibilitate |
| 2 | Nu ajunge SRAM-ul intern (BLE + Wi-Fi + TLS + audio + DMA) | buget per componentă, măsurat automat pe placă (`heap_caps`); bufferele TLS și Wi-Fi în PSRAM; NimBLE, nu Bluedroid; Wi-Fi pornit doar pentru voce |
| 3 | Autonomia iese sub țintă | serviciul Energie din 0.3; analizor de curent din prima zi; fața ambientală la 2–5 fps; ecran stins agresiv; baterie de 1000 mAh |
| 4 | Necunoscute pe placa 1.75 (IMU_INT, RTC_INT, cristal 32 kHz, haptic) | verificăm schema acum; plan B: trezire prin timer ESP și citirea IMU în light sleep; PCB propriu pentru producție |
| 5 | Migrarea Arduino → ESP-IDF strică ce merge | biblioteca rămâne fără dependențe hardware, cu cele 24 de teste și simulatorul; migrăm o singură dată (0.3), în doi pași |
| 6 | Scrierea în flash sacadează UI-ul | scrieri grupate când ecranul e liniștit; `SPIRAM_XIP_FROM_PSRAM`; task Store cu prioritate mică |
| 7 | Ecranul e lent (QSPI la 40 MHz [V], fără DMA: un cadru complet ia ~22 ms [E]) | DMA + dublu buffer, dirty-rect, strat cache pentru tastatură; testăm 80 MHz pe panou |
| 8 | Dependența de platforme (Hardware Buddy, conectori Claude, aplicații ChatGPT, politicile lor) | stratul Intents izolează furnizorul; modul fără AI e promisiunea de bază; MCP e un standard deschis |
| 9 | Limitele iOS în fundal (releu BLE, notificări push) | BLE background mode + state restoration; Wi-Fi direct acasă; pentru conectori acceptăm livrarea „la următoarea sincronizare” |
| 10 | Device blocat după OTA sau eFuse ars greșit | A/B + self-test + rollback; teste cu tăierea curentului în timpul update-ului; provizionare scriptată, încercată pe 20 de unități înainte de fabrică |
| 11 | Licența Moddable XS (LGPLv3 vs secure boot) | licență comercială înainte de faza 2, altfel WAMR; v1 nu depinde de niciun runtime |
| 12 | „Un OS ca Apple” cu o echipă mică (scope) | API mic, înghețat per versiune; fără cod terț în v1; 13 aplicații de sistem, nu mai multe; fiecare fază livrează ceva care merge |
| 13 | Diacritice și fonturi (Fredoka nu are ă ș ț) | fallback pe glifă către Nunito; teste de randare RO în sim; normalizare sedilă → virgulă |
