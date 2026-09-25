# SoulOS — specificație v0.1

*SOUL · ecran rotund AMOLED 1,75" 466×466 · ESP32-S3 · 24 sept. 2026*
Prototip interactiv: `os/index.html` · capturi: `os/screenshots/soulos-*.png`

---

## 0. Ideea într-o frază

**Acasă e fața.** Doi ochi vii care stau mereu pe ecran. Orice altceva (un răspuns, un memento, o cerere Claude) e un **cartonaș** care alunecă peste față. Cât timp cartonașul e deschis, ochii se micșorează într-un „antet” sus și se uită la el. Când termini, cartonașul pleacă și fața revine la dimensiunea întreagă. SOUL nu are meniuri și nici icoane de aplicații. Are o față, un cerc de cartonașe și o singură regulă de voce: **ții apăsat = vorbești**.

Principii:
1. **Întâi caracterul.** Fiecare eveniment are și o reacție a ochilor (privire, clipit, bucurie, „nu”), nu doar un text.
2. **Puține elemente pe ecran.** Maximum un titlu, 1–3 rânduri și 1–2 butoane-chip. Textul are cel puțin 22 px, iar textul principal 27–34 px.
3. **Negru e gol.** Fundalul e mereu #000 (pixelii AMOLED sunt stinși), deci consumul scade și ochii „plutesc”.
4. **Culoarea are sens.** Cremă `#FFF0C8` = informație · chihlimbar `#FFB347` = are nevoie de tine · mentă `#C9F2E4` = gata · gheață `#9FC6FF` = ascultă (microfon pornit).
5. **Totul se întoarce acasă.** Butonul lateral, glisarea în jos sau 7 s fără atingere pe un răspuns te readuc la față.

---

## 1. Corpul și intrările

Referință: `research/06-product-design-v2-2026-09-24.md` §3, forma A.

| Intrare | Hardware | Ce face în SoulOS |
|---|---|---|
| Atingere | touch capacitiv pe ecran | acțiunea principală a ecranului; pe față = „bup” (inimioare) |
| Atingere dublă | touch | refuză o cerere Claude; pe față = râde |
| Ține apăsat (≥380 ms) | touch | **vorbești** (inel gheață). Excepții: pe o cerere Claude = aprobi (1,2 s); pe Memorie = ștergi tot |
| Glisare ← → | touch | treci la aplicația următoare/anterioară (cerc închis) |
| Glisare ↑ | touch | de pe față: stiva **Azi** |
| Glisare ↓ | touch | înapoi (pe față: nimic) |
| Buton lateral (sus-dreapta) | buton fizic cu cursă | apăsare = acasă · **ținut = vorbești** (microful e pornit din hardware de buton) · apăsare dublă = anulează |
| Ridicare | IMU | trezire + ceasul apare 1,5 s |
| Scuturare | IMU | amețit (spirală); închide notificarea curentă |
| Cu fața în jos | IMU | nu deranja + somn (ochi închiși, zzz, luminozitate 55%) |
| Înclinare | IMU | derulează listele lungi (Mementouri, Memorie) |
| Mângâiere pe spate | electrozi capacitivi | reacții de personaj (tors); nu fac nicio acțiune în OS |

Prototipul folosește aceleași reguli cu tastatura: ← → = aplicații, ↑ = Azi, ↓ = înapoi, Space ținut = vorbești, Enter = atingere, D = atingere dublă, Esc = buton.

---

## 2. Modelul de navigare

```
                 ┌──────────── Azi (↑) ────────────┐
                 │ memento · vreme · Claude · baterie│
                 └───────────────▲──────────────────┘
                                 │ ↑ / ↓
 Setări ◀─▶ … ◀─▶ Vorbește ◀─▶ [ ACASĂ = FAȚA ] ◀─▶ … (cerc închis)
                                 │
          suprapuneri: Voce (ține) · Mesaj · Memorie · „Sunt un AI”
```

- **Cercul de aplicații** (ordinea glisării la stânga): Acasă → Vorbește → Mementouri → Notițe → Focus → Claude → Jurnal → Traduce → Muzică → Setări → Acasă. Punctele de jos arată poziția: pătratul e Acasă, punctul aprins e ecranul curent. Pe față punctele nu apar.
- **Suprapunerile** nu fac parte din cerc. Se deschid peste ecranul curent și se închid cu ↓, cu butonul sau singure, după ce au terminat.
- **Vocea e globală.** Ții apăsat pe orice ecran și se deschide suprapunerea Voce. Pe Notițe, vocea dictează o notiță. Pe Traduce, vocea traduce.
- **Fața în timpul navigării:** pentru cartonașe, fața se micșorează la k = 0,30 și urcă la y = −0,33 (antet). Pe Vorbește rămâne mare (k = 0,62). Pe răspuns e la k = 0,42. Când intră un cartonaș, ochii se uită spre direcția din care vine, apoi se așază pe conținut.

---

## 3. Ecrane

| # | Ecran | Scop (un rând) | Detalii |
|---|---|---|---|
| — | **Acasă** | Fața vie. | Ceas discret sus (50% opacitate). Jos apare cel mult o etichetă: „Claude te așteaptă” (chihlimbar) sau „Focus · 18:21”. Ochii urmăresc degetul. |
| ↑ | **Azi** | Totul dintr-o privire. | Patru rânduri: următorul memento, vremea, starea Claude (lucrează / te așteaptă), bateria. Nu are acțiuni; e doar de citit. |
| 01 | **Vorbește** | Întrebi ceva, primești un răspuns scurt. | Fața mare. Sub ea: „Ține apăsat și întreabă” sau ultima întrebare și numele AI-ului (Claude/ChatGPT). |
| 02 | **Mementouri** | Ce urmează azi. | Maximum 3 rânduri (ora + text + bifă). Atingerea bifează, iar ochii se bucură. Un memento nou e evidențiat. |
| 03 | **Notițe** | Notițe vocale care ajung pe telefon. | Ține apăsat = dictezi. Ultimele 2 notițe, cu starea „se trimite…” / „pe telefon ✓”. |
| 04 | **Focus** | Timer de concentrare de 25 min. | Inel cremă pe marginea ecranului, cifre de 104 px. Ochii se uită în jos la timp, cu pleoapele pe jumătate. Atingerea pornește sau pune pauză. La final: ochi-stea, pastila „Focus gata ✓”, haptic. |
| 05 | **Claude** | Aprobi ce vrea Claude (Claude Code / Cowork). | Fără cerere: „Claude lucrează”, iar ochii scanează ca la citit. Cu cerere: eticheta „Claude cere voie” în chihlimbar, proiect + unealtă, comanda (mono) și indiciul „Ține = da · 2× = nu”. Ține 1,2 s (arc mentă) = aprobi; atingere dublă = refuzi (ochii fac „nu”). |
| 06 | **Jurnal** | Ziua voastră, scrisă de el. | Ultimele 3 rânduri cu oră („Am râs de două ori.”). Acțiunile făcute prin voce adaugă singure câte un rând. |
| 07 | **Traduce** | Conversație în două limbi. | Chip RO ⇄ EN (atingerea inversează). Ține apăsat = vorbești. Apare textul sursă mic și traducerea mare (mentă); telefonul o și rostește. |
| 08 | **Muzică** | Telecomandă pentru telefon. | Titlu, artist, butoanele ⏮ ⏯ ⏭ (72/92 px) și o bară de progres. Atingerea pe centru = pauză. |
| 09 | **Setări** | Puține reglaje, pe device. | Luminozitate (40/70/100%), AI (Claude ⇄ ChatGPT), Memorie › (vezi / ține = șterge tot), „Sunt un AI” › (notificare de transparență). Restul setărilor sunt în aplicația de telefon. |
| ov | **Voce** | Ascult → mă gândesc → răspund. | Vezi §5. |
| ov | **Mesaj** | Răspuns rapid la un mesaj. | Textul mesajului și 2 răspunsuri sugerate (chips). Ține apăsat = dictezi alt răspuns. |

---

## 4. Reguli de interacțiune

1. **O singură acțiune principală pe ecran**, activată prin atingere oriunde. Butoanele secundare sunt chips de cel puțin 52 px înălțime.
2. **Ținutul apăsat înseamnă mereu „voce”**, cu două excepții care se văd pe ecran: aprobarea Claude (arc mentă) și ștergerea memoriei (arc chihlimbar). Ambele cer 1,2 s de ținut continuu. Dacă ridici degetul mai devreme, nu se întâmplă nimic.
3. **Atingerea dublă nu întârzie atingerea simplă.** Prima atingere acționează imediat, iar a doua o „modifică” (bup → râs). Singura excepție e ecranul unei cereri Claude, unde atingerea simplă nu face nimic.
4. **Zona sigură:** conținutul stă în pătratul înscris de ~330 px (68 px margine laterală). Nimic interactiv nu stă sub y = 410 (acolo sunt punctele de poziție). Pastila stă la y = 18–72.
5. **Animații:** cartonașele intră în 420 ms (ease-out), iar fața își schimbă mărimea cu un arc de 9/s. Cu „reduce motion” activ, trecerile devin instantanee.
6. **Timeout:** un răspuns se închide singur după 6,5 s. Un cartonaș de aplicație rămâne deschis până la ecranul stins (15 s, apoi fața se estompează și adoarme după 20 s de liniște).
7. **Haptic:** clic scurt la atingere, dublu la aprobare, „bzz-bzz” la o cerere care are nevoie de tine, lung la final de Focus.

---

## 5. Voce și AI: pipeline

### 5.1 Pe ecran (ritmul vizibil)
| Fază | Față | Ecran | Durată tipică |
|---|---|---|---|
| **Ascult** | ochi mari, privire în sus, inel **gheață** pe margine care pulsează cu nivelul vocii | „ASCULT…” și transcrierea live, cu cursor | cât ții apăsat |
| **Mă gândesc** | trei puncte sub ochi, privire sus-dreapta | „Claude se gândește…”, întrebarea și unealta apelată (`→ reminders.create`) | 0,8–2 s |
| **Răspund** | ochii „vorbesc” (scalare după nivelul audio), apoi fericiți | 1–2 rânduri (≤ 60 de caractere) și chips; **mentă ✓** dacă acțiunea s-a făcut | 6,5 s sau o atingere |

Exemple scriptate în prototip: „Amintește-mi la 5 să sun la bancă” → `reminders.create` → „Gata. Te anunț la 17:00.” [17:00 · Sună la bancă ✓] · „Ce vreme e mâine?” → `weather.forecast` · „Notează: idee de breloc” → `notes.append` · „Pornește focus 25 min” → `timer.focus` (local) · „Scrie-i Anei…” → `messages.send` · „Stinge lumina în sufragerie” → `mcp · home.lights`.

### 5.2 Arhitectura
```
SOUL (ESP32-S3)                 Telefon (aplicația SOUL)             Cloud
────────────────                ─────────────────────────            ─────
ține apăsat ─► mic I2S 16 kHz
  ─► Opus 16 kb/s ──BLE (GATT)──► releu audio ─────────WebSocket──► STT streaming
                                                                      │
                                   unelte locale ◄── tool calls ◄── LLM: Claude / ChatGPT
                                   (mementouri iOS/Android,          (system prompt SOUL,
                                    notițe, mesaje, muzică,           memorie per utilizator,
                                    calendar)                         unelte + MCP)
                                                                      │
                                                        MCP servers ◄─┘ (Home Assistant,
                                                                        Notion, calendar…)
◄── card JSON + audio TTS ──BLE──◄ răspuns {say, card, face, chips} ◄── TTS
Face/Card/Notifier redau
```

- **Răspunsul LLM e structurat**, nu text liber: `{ "say": "…", "card": { "text": "…", "chips": [{"t":"17:00 · Sună la bancă","kind":"ok"}] }, "face": "happy", "tool": "reminders.create" }`. Device-ul nu interpretează limbaj; afișează doar ce primește.
- **Uneltele** sunt definite o singură dată și expuse identic ambelor modele (Claude tool use / OpenAI function calling): `reminders.create|list|done`, `notes.append`, `messages.draft|send`, `music.control`, `timer.focus`, `weather.forecast`, `translate`, `memory.get|forget`, `home.*` (prin MCP).
- **Acțiunile către alți oameni** (mesaje, e-mail) se trimit după 3 s de „Trimit… atinge ca să anulezi”. În setările de pe telefon utilizatorul poate cere confirmare explicită.
- **Claude Code / Cowork** merge pe canalul existent `ClaudeLink` (protocolul Hardware Buddy, BLE direct cu desktopul): cereri de permisiune, busy/idle, level-up.

### 5.3 Ce rulează unde
| Pe device (ESP32-S3) | Pe telefon | În cloud |
|---|---|---|
| fața, Brain, gesturi, IMU, randare | releu BLE ↔ internet | STT, LLM (Claude/ChatGPT), TTS |
| cartonașe, notificări, haptic | unelte native (mementouri, notițe, mesaje, muzică) | memoria pe termen lung (criptată, per cont) |
| Focus, ceas, mementouri deja sincronizate (se declanșează și offline) | cache Azi (vreme, calendar) | MCP pentru serviciile externe |
| Opus encode, VAD simplu pentru nivelul vocii | setări, notificări permise, jurnal complet | jurnal: rezumatul zilei (opțional) |
| aprobare/refuz Claude (BLE direct cu desktopul) | | |

Fără telefon sau fără net: fața, Focus, mementourile sincronizate și Claude (desktop) merg în continuare. La „ține = vorbești”, ochii fac „?” cu un nor, iar pe ecran apare: „Nu am net acum.”

---

## 6. Notificări

1. **O singură pastilă** odată, sus (y = 18–72, max. 320 px). Ochii se uită la ea 1,4 s, iar cât stă ea pe ecran fața din antet se micșorează ca să nu se suprapună.
2. **Prioritate:** cerere Claude > memento scadent > mesaj de la un contact favorit > restul. Restul nu apar ca pastilă; se strâng într-un număr în Azi.
3. **Durată:** pastilele informative stau 4–6 s. O **cerere care are nevoie de tine** (chihlimbar) stă 5 s ca pastilă și apoi rămâne ca **inel chihlimbar** pe marginea ecranului, plus eticheta de pe față, până o rezolvi. Nu acoperă conținutul la nesfârșit.
4. **Pe ecranul la care duce notificarea, pastila nu mai apare.** Exemplu: pe ecranul Claude nu apare pastila „Claude cere voie”, se aprinde doar inelul.
5. **Atingi pastila** și se deschide cartonașul ei. **Glisezi pastila în sus** și dispare. **Scuturi** și dispare tot ce nu e chihlimbar.
6. **Fără sunet implicit.** Notificările folosesc haptic și privirea ochilor. Pe telefon, utilizatorul alege sursele permise.
7. **Nu deranja:** cu fața în jos, în orele de liniște sau în Focus apar doar cererile chihlimbar, și doar ca inel, fără haptic.
8. **Culori:** cremă = informație, chihlimbar = are nevoie de tine, mentă = gata ✓.

---

## 7. Confidențialitate

1. **Microfonul pornește doar cât ții apăsat** (degetul pe ecran sau butonul lateral). Nu există cuvânt de trezire și nici ascultare continuă. Pe butonul lateral, alimentarea microfonului trece prin buton (poartă hardware).
2. **Inelul gheață se aprinde întotdeauna când microfonul e pornit.** Regula e în firmware, sub nivelul aplicației: dacă ajunge audio la I2S, inelul e desenat.
3. **Audio-ul nu se păstrează.** Se transmite, se transcrie, apoi se șterge. Rămâne doar textul întrebării, în istoricul de pe telefon (ștergere automată după 30 de zile, configurabil).
4. **Memoria se vede și se șterge de pe device:** Setări › Memorie arată ce ține minte („Ana e sora ta”), iar ținutul apăsat 1,2 s șterge tot. Pe telefon se poate șterge și câte un element.
5. **„Sunt un AI.”** Mesajul apare la prima pornire, în Setări și ori de câte ori cineva întreabă „ești om?”. SOUL nu pretinde niciodată că e om, că are sentimente reale sau că e prieten în locul oamenilor.
6. **Cheile AI** (abonament Claude/ChatGPT sau cheie API) stau pe telefon sau în contul SOUL, niciodată pe device. Device-ul primește doar tokenuri de sesiune.
7. **Acțiunile ireversibile sau către alți oameni** au fereastră de anulare sau confirmare (§5.2). Cererile Claude cer ținut deliberat de 1,2 s: fără aprobări din greșeală.
8. **Datele de pe device** (jurnal, cache Azi) stau criptate în flash (NVS encryption + flash encryption). La reset, se șterg.

---

## 8. Implementare pe ESP32-S3

### 8.1 Randare: renderer propriu, nu LVGL
**Recomandare:** extindem `Canvas` (SDF RGB565, deja folosit pentru față) cu un strat mic de UI, în loc să adăugăm LVGL.

| | Canvas propriu + widgeturi mici | LVGL 9 |
|---|---|---|
| Fața (glow, SDF, pleoape) | există deja, ~9 KB de cod | ar trebui portată ca widget custom sau desenată separat |
| Text | font bitmap 4bpp (Fredoka + diacritice RO, 3 mărimi) | excelent, gata făcut |
| Liste, derulare | câteva widgeturi scrise de noi (≤ 3 rânduri pe ecran) | gata făcut |
| Flash / RAM | ~60 KB cod + ~180 KB fonturi | ~250–350 KB cod + fonturi |
| Un singur pipeline de desen | da | două (LVGL + fața) |

Ecranele SoulOS au puține elemente, așa că un set mic de widgeturi (Text, Chip, ListRow, Ring/Arc, Icon) acoperă tot. LVGL rămâne varianta de rezervă dacă apar Setări complexe pe device.

Fonturi: Fredoka + un font de rezervă pentru ș/ț/ă/î/â (Nunito), rasterizate cu `lv_font_conv` sau un script propriu în atlase 4bpp. Mărimi: 22, 27, 34, plus cifrele Focus la 104 px (doar 0–9 și „:”).

### 8.2 Bugetul de memorie
| Resursă | Mărime | Unde |
|---|---|---|
| Framebuffer 466×466 RGB565 | 434 KB | PSRAM (există: `Arduino_Canvas`) |
| Buffer de push/rotire (`pushBuf`) | 434 KB | PSRAM (există) |
| Al doilea strat pentru tranziții (cartonașul vechi, cache) | 434 KB | PSRAM, opțional: tranzițiile pot fi redesenate |
| Atlase fonturi | ~180 KB | flash (mmap) |
| Audio: buffer mic 2×20 ms + Opus encoder | ~40 KB | SRAM intern |
| TTS jitter buffer (1 s @ 16 kHz PCM) | 32 KB | PSRAM |
| Stiva BLE (NimBLE) | ~60 KB | SRAM intern |
| **Total PSRAM** | **~1,4 MB din 8 MB** | |

Randarea pe cadru: fața merge cu dirty-rect (deja implementat, 30 fps treaz). Tranzițiile de cartonaș sunt full-frame: 434 KB pe QSPI la 80 MHz înseamnă ~11–14 ms de transfer, deci 30 fps țintă cu DMA și dublu buffer. În somn, randarea scade la 5–10 fps (`frameRateHint()`), iar cu fața în jos se oprește complet.

### 8.3 Arhitectura cartonașelor, legată de `lib/Suflet`
Clasele existente rămân. Adăugăm trei clase și extindem două:

```
Sensors ──► TouchGestures ─┐          ┌─► Brain (personaj: Face + Mood + reacții)   [există]
            MotionDetector ├─► Ev ───►│
            ClaudeLink ────┤  queue   └─► Shell (nou: navigare + cartonașe + voce)
            PhoneLink (nou)┘                 │
                                             ├─ Card* stack / RING[10] / overlay
                                             ├─ Notifier (nou: pastilă + inel, priorități)
                                             └─ VoicePipeline (nou: Listen→Think→Answer)
Frame: Brain.update() → Shell.update() → renderFace(canvas, face, shell.faceLayout())
                                       → shell.render(canvas) → push dirty rect
```

- **`Events.h`**: adăugăm `SwipeLeft/Right/Up/Down`, `ButtonPress/ButtonHold/ButtonRelease/ButtonDouble`, `PhoneUp/Down`, `AiCard` (a sosit un JSON de răspuns), `ReminderDue`, `Notify`.
- **`Gestures.cpp`** (`TouchGestures`): astăzi emite `Stroke*` pentru mângâiere. Mișcarea rapidă (> 25% din diametru în < 350 ms) devine `Swipe*`. Mișcarea lentă rămâne `Stroke`, adică mângâiere, doar pe Acasă.
- **`Face.h`**: `renderFace()` primește `FaceLayout { float k, cy; }`. `Face` are deja `ov::Listen/Think/Alert/Progress`; inelele se desenează la scară completă, iar ochii la scara k. Același lucru face prototipul în `drawFace(ctx, S, f, lay)`.
- **`Brain`**: primește în plus `setGazeHint(x, y, dur)` (Shell îi spune „uită-te la pastilă”) și `setState(Listen/Think/Speak/Focus/Busy)`. Reacțiile noi (`Happy`, `Nope`, `Star`) există deja ca `Reaction` (`Celebrate`, `Nope`, `Birthday`).
- **`Shell`** (nou): ține `view`, `ret`, indexul din RING și overlay-ul curent. Decide cine consumă un `Ev`: overlay → card → Shell (swipe/buton) → Brain (bup/râs pe Acasă). Gestionează tranzițiile (offset animat, 420 ms).
- **`Card`** (interfață nouă): `enter(dir)`, `exit(dir)`, `bool onEvent(Ev)`, `void render(Canvas&, Rect)`, `FaceLayout layout()`, `bool wantsHold()`. Implementări: `HomeCard`, `TodayCard`, `TalkCard`, `RemindersCard`, `NotesCard`, `FocusCard`, `ClaudeCard` (citește `ClaudeLink::hasPrompt()` și apelează `decide()`), `DiaryCard`, `TranslateCard`, `MusicCard`, `SettingsCard`, `VoiceOverlay`, `MessageOverlay`, `MemoryOverlay`.
- **`Notifier`** (nou): coadă cu priorități. Desenează pastila și îi spune lui `Brain` să se uite la ea. Pentru chihlimbar setează `ov::Alert` persistent.
- **`VoicePipeline`** (nou): stări `Idle → Listen → Think → Answer`. Pornește și oprește I2S prin `Cue::ListenOn/ListenOff` (există deja în `Brain`). Împachetează Opus pe `PhoneLink`, primește `AiCard` și PCM TTS.
- **`PhoneLink`** (nou, după modelul `ClaudeLink`): transport-free, JSON pe linii și cadre binare pentru audio, pe același BLE (serviciu separat).

### 8.4 Plan pe etape
| Etapă | Livrabil | Estimare |
|---|---|---|
| 1 | `FaceLayout` + `Shell` + `Card` + swipe în `TouchGestures`; Acasă, Azi (date statice), puncte de poziție; testat în `sim` | 1,5 săpt. |
| 2 | Text: atlase Fredoka RO (22/27/34/104), widgeturi Text/Chip/ListRow/Arc; ecranele Focus, Mementouri, Jurnal, Setări (local) | 2 săpt. |
| 3 | `Notifier` + `ClaudeCard` peste `ClaudeLink` existent (pastilă, inel, ține-aprobă, dublu-refuză) | 1 săpt. |
| 4 | `PhoneLink` + aplicație telefon minimă (releu); `VoicePipeline` cu Opus; răspuns structurat; Talk + Notițe + Mementouri reale | 3 săpt. |
| 5 | Unelte telefon (mesaje, muzică, calendar), MCP (Home Assistant), Traduce, Memorie (vezi/șterge) | 3 săpt. |
| 6 | Performanță (DMA dublu buffer, tranziții 30 fps), baterie (somn agresiv, AMOLED negru), teste `pio test -e native` pentru Shell/Notifier | 1,5 săpt. |

Criterii de gata: nicio acțiune nu cere mai mult de 2 gesturi de pe față; de la eliberarea degetului la primul cuvânt < 1,8 s (p50); inelul gheață e prezent în 100% din cadrele cu microfon activ; 18 ore de folosire tipică pe 1000 mAh.

---

## 9. Tastatura, modurile AI și Alarmele (prototip v0.2, 25 sept. 2026)

Implementat în `os/index.html` (copie în `site/os.html`). Designul complet: `research/04-keyboard-design-familiar.md`. Capturi: `screenshots/soulos-keyboard-*`, `soulos-claude-type-*`, `soulos-ai-mode-*`, `soulos-notes-type-*`, `soulos-alarm-*` (390 și 1440 px). Corpul desenat e forma finală v5: piatră verticală 63×74 mm, mai lată sus, bază plată, aluminiu sablat, sticla neagră Ø52 ocupă fața; pe față nu mai e nimic altceva.

**Tastatura (QWERTY rotund).** E un serviciu de sistem: aplicația cere text (`text.request`) și primește doar textul final.
- Ochii urcă într-un antet mic (y 40) și se uită după deget. Câmpul are 2 rânduri, cursorul e gheață. Sub el e bara de sugestii: stânga = ce ai scris, mijloc (îngroșat) = cea mai bună variantă, dreapta = următoarea. Cu câmpul gol apar 3 chipuri de context, date de aplicație.
- Taste de 44–47 px (≈4,1–4,4 mm), 3 rânduri + rândul de acțiuni: `?123` · microfon · spațiu `RO · EN` · Gata. Gata e chihlimbar cu ↑ când trimiți (Claude) și mentă cu ✓ când salvezi (notiță, memento, alarmă). Litera intră când ridici degetul și poți aluneca pe tasta corectă. Straturi: `?123` și `#+=`.
- Predicție locală dintr-un lexic mic EN+RO (index fără diacritice). **Auto-diacritice** la spațiu sau punctuație, doar pentru formele sigure: `sa`→`să`, `si`→`și`, `maine`→`mâine`, `tara`→`țară`. Cuvântul schimbat e subliniat cu mentă. **⌫ imediat după** readuce exact ce ai scris, iar cuvântul nu mai e schimbat în sesiunea aceea. Într-o propoziție în engleză nu se aplică.
- **Apăsare lungă** (380 ms) pe a/i/s/t: tava are litera românească deja aleasă (ă, î, ș, ț). Aluneci pentru â, à…
- ⌫ ținut repetă, apoi șterge cuvinte întregi și oferă `↶ Anulează` 5 s. Scuturarea oferă și ea anularea (doar ca pastilă, nu aplică singură). Două spații = „. ”.
- O gramatică locală de timp („la 5”, „mâine la 9:30”, „at 7pm”, „în 10 min”) oferă chipul mentă `⏰ 17:00`. Merge fără AI.
- Microfonul dictează (demo scriptat) doar cu AI. În modul „Fără AI” e tăiat și spune că dictarea cere AI și net.
- **Butonul lateral = înapoi**: tastatura se închide și ciorna rămâne. Ținut = dictezi în câmp.
- Tastatura fizică a desktopului scrie în câmpul deschis (Enter = Gata, Esc = înapoi). Scurtăturile globale (Space, Enter, D, Backspace, săgeți) merg doar când nu e deschis niciun câmp. Atingerile pe taste nu mai trec prin detectorul de dublă atingere, iar butoanele (`data-act`) reacționează la fiecare atingere, oricât de rapidă.

**Modurile AI** (Setări › AI și panoul prototipului): **Fără AI** · **Claude-ul tău** (conectorul SOUL) · **ChatGPT-ul tău** (aplicația SOUL) · **Cheia ta API** (direct, cheia stă pe telefon).
- Antetul din Vorbește, butonul „Scrie lui …”, eticheta „… se gândește” și eticheta răspunsului arată modul ales.
- Fluxul „Scrie lui Claude”: scrii → trimiți (↑) → ochii se gândesc → cartonaș scurt, marcat **„demo scriptat”**, care și face ceva prin intenții: `reminder.create` („✓ Memento pus pentru 17:00”), `note.create`, `alarm.set`.
- **Fără AI:** scrisul merge în continuare. Mementourile și alarmele cu oră se fac local, prin gramatică. Restul mesajelor ajunge în Notițe (outbox), iar aplicația spune că e offline. Vocea ținută explică că fără AI nu poate asculta.

**Notițe și Mementouri.**
- Notițe: `+` = notiță nouă scrisă. Atingi o notiță = o editezi. ↑ răsfoiește notițele mai vechi.
- Mementouri: `+` = text. Dacă textul are oră, mementoul se pune direct. Dacă nu, se deschide cadranul, cu chipul Azi/Mâine. O oră trecută trece singură pe mâine.

**Alarme** (aplicație nouă în cerc, după Mementouri).
- Lista are comutatoare. `+` deschide **Rim-Dial**:
  - Orele sunt pe un inel de 24 h ca un cadran solar: 0 jos, 12 sus, jumătatea de zi cremă, noaptea gheață.
  - Când ridici degetul, după 400 ms trece la minute.
  - Minutele sunt pe un cadran obișnuit (00 sus). Mișcarea rapidă sare din 5 în 5.
  - Rândul „sună în X h Y min” te ferește de confuzia între jumătățile zilei. Tastatura fizică acceptă cifre (`0730`).
- ✓ duce la rezumat: ora, eticheta (✎ deschide tastatura), cele 7 zile pe marginea de jos, `✓ Setează`.
- La ora alarmei se deschide ecranul de sunat: ochii dorm (zzz), apoi se trezesc. Inelul e chihlimbar și dispozitivul vibrează. Alegi `Amână 5` sau `Oprește`. Butonul lateral oprește alarma, iar cu fața în jos o amâni.
- Panoul are „Sună alarma acum” pentru demo.
