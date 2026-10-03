# 09 · SOUL everywhere: connectivity on the go

*SOUL package · 3 Oct 2026 · rev. 1. Goal from the founder: **"connect your AI to this device and take it with you
everywhere."** Scope: how SOUL M (Waveshare ESP32-S3-Touch-LCD-2.8C, LiPo 803450 1500 mAh, aluminium body with a
polymer base) reaches the internet away from home Wi-Fi. Built today: firmware 1.5.0 (§1–2). Studied: the phone app
BLE tether (§4) and built-in LTE (§5). Recommendation and roadmap: §7.*

Markers: **[V]** checked today against the source listed, **[E]** our estimate (method given), **[U]** unknown or
unverified, to measure or confirm, **[R]** read in our own code.

---

## Rezumat (RO)

**Ce merge azi (firmware 1.5.0, construit și testat pe PC):** SOUL ține minte până la **8 rețele Wi-Fi** (acasă,
birou, **hotspotul telefonului**, altele), cu prioritate, și trece singur de la una la alta: când pleci de acasă
caută des (la 4 s, 3 minute), deci se conectează la hotspot în câteva secunde după ce îl pornești; când ajungi acasă
revine pe Wi-Fi-ul de acasă. Hotspotul se adaugă **direct pe SOUL** (Setări › Wi-Fi › „Adaugă hotspotul
telefonului”), cu instrucțiuni pentru iPhone (Hotspot personal › Permite altora + **Maximizează compatibilitatea**,
fiindcă SOUL merge doar pe 2,4 GHz) și Android (nume, parolă, banda 2,4 GHz), sau pe pagina de configurare și pe
`/me/wifi-help`. După fiecare conectare SOUL verifică dacă internetul chiar merge: recunoaște **Wi-Fi-ul de hotel cu
pagină de login** (nu poate apăsa „Accept”, îți spune să folosești hotspotul) și **hotspotul fără date mobile**.
Fără internet, ochii au pleoapele puțin mai grele și se uită din când în când în jur; regulile de pe device (alarme,
memento-uri, minutar) merg imediat, iar celelalte întrebări **așteaptă (maximum 5, maximum 6 ore)** și pleacă singure
când revine internetul.

**Recomandarea:** hibrid, în trei trepte. (1) **Wi-Fi + hotspotul telefonului** pentru pilotul de 10–25 de bucăți
(cost hardware: €0, gata azi). (2) Aplicația de telefon cu „tether” prin Bluetooth **nu** ca drum principal: pe
iPhone aplicația poate fi oprită de sistem sau închisă de utilizator și SOUL rămâne fără internet; o facem mai târziu
doar dacă pilotul cere, întâi pe Android. (3) **LTE Cat-1 bis încorporat în v2** (ex. Quectel EG800Q-EU sau SIMCom
SIM7672E + eSIM MFF2 1NCE: 500 MB pe 10 ani la €12): **≈ €48 în plus pe bucată la 25 de bucăți, ≈ €34 la 1.000**
(cu datele pe 10 ani), plus **≈ €10–25k o singură dată** pentru certificare (RED cu SAR). Bateria: **≈ –10 %
autonomie** dacă reducem ping-ul socket-ului SOUL Cloud pe celular de la 25 s la ~5 min (altfel ≈ –40 %). În CAD:
antenă flexibilă pe peretele bazei din polimer (fereastra RF), la ≥ 10–15 mm de aluminiu și ≥ 20 mm de antena
Wi-Fi. **Microfonul și difuzorul** trebuie să devină standard: pe drum vorbești, nu tastezi; azi calea de voce
(`SUFLET_VOICE`) trimite 8 s de WAV (256 KB) doar la OpenAI cu cheia ta și nu vorbește înapoi; lipsesc Opus (16×
mai puține date), STT prin SOUL Cloud și răspunsul vorbit.

---

## 0 · The options at a glance

| | **a) Phone hotspot** | **b) BLE tether via a phone app** | **c) Built-in LTE Cat-1 bis** |
|---|---|---|---|
| Works today | **Yes, firmware 1.5.0** (§1) | No: needs 2 apps + a relay protocol | No: v2 hardware |
| Needs the phone | Yes, hotspot on | Yes, app running | **No** |
| Hardware cost per unit | €0 | €0 (BLE is on the ESP32-S3) | **≈ €48 @25 / ≈ €34 @1k** incl. 10 years of 500 MB (§5.7) |
| One-off cost | €0 | ≈ €12–25k app development [E] + $99/yr Apple, $25 Google | ≈ €10–25k certification [E] + carrier PCB design |
| Data paid by | The phone's plan | The phone's plan | Us / the owner (≈ €1–2 per year text-only, §5.5) |
| Reliability | Good once saved; iPhone hides an idle hotspot (§1.2) | Android good (CompanionDeviceManager); **iOS fragile** (§4.2) | Good where LTE is; weak in deep indoor on low bands (§5.4) |
| Extra latency per Claude turn | +0.1–0.3 s [E] | +0.3–1.5 s [E] | +0.2–0.5 s (socket open) [E] |
| SOUL battery | ≈ same as home Wi-Fi | Wi-Fi off, BLE on: slightly better [E] | ≈ –10 % with long keepalives, ≈ –40 % with today's 25 s pings [E] (§5.3) |
| Phone battery | Hotspot drain on the phone [U: measure] | Small (BLE) | None |

---

## 1 · a) The phone's hotspot: built today (firmware 1.5.0)

### 1.1 What the owner does

Once, at home or on the go:

- **On SOUL:** *Settings › Wi-Fi › Add my phone's hotspot* shows the steps, then *Type it on SOUL*: the hotspot's
  name, then its password, on the round keyboard. Names and passwords are typed **verbatim** (no auto-capital,
  auto-diacritics or ". "; this also fixed API keys typed on SOUL, whose first letter used to be capitalised [R]).
  Pictures: `firmware/sim/shots/everywhere/03-hotspot-howto.png`, `04-hotspot-password.png`.
- **Or on the setup page** (`http://192.168.4.1/hotspot`, from *Set up from a phone*): the same steps, name and
  password fields; the main page now lists the saved networks with *first / normal / last* and *forget*.
- **Or read it on `/me/wifi-help`** (SOUL Cloud, EN + RO, new section "Take SOUL with you").

The steps shown:

| Phone | Steps |
|---|---|
| **iPhone** | *Settings › Personal Hotspot*: **Allow Others to Join** on; **Maximize Compatibility** on (iPhone 12 and later otherwise use 5 GHz; SOUL's ESP32-S3 is 2.4 GHz only) [V: Apple, PhoneArena]. The name is the iPhone's name (*Settings › General › About › Name*) [V: Apple]. If SOUL does not join within a minute: open *Settings › Personal Hotspot* and keep it on screen, then pick SOUL up. |
| **Android** | *Settings › Network & internet › Hotspot & tethering › Wi-Fi hotspot* (names vary by brand): name, password, **2.4 GHz** band (or "2.4 and 5 GHz"); turn off *Turn off hotspot automatically*. |

### 1.2 What the firmware does

Code: `firmware/lib/Suflet/src/WifiRoam.{h,cpp}` (hardware-free, unit-tested), driven by `firmware/src/net.cpp`.

- **Up to 8 saved networks** (`WifiBook`): Home (priority 8), Work (7), Other (5), Phone hotspot (3); priority 1–9
  editable. Stored in NVS `soulkey/wifis` (versioned blob); 1.4's single network moves in as *Home* on first boot.
- **Roaming** (`WifiRoamer`): join the highest priority network in reach (≥ –86 dBm), then the strongest. Online on a
  second-choice or weak (< –80 dBm) network: look around every 2 min and move to a higher priority one at ≥ –72 dBm
  (back home from the hotspot), or to a ≥ 10 dB stronger one of the same priority.
- **Fast reconnect**: when the link drops, or when a network is added, **scan every 4 s for 3 min**, then every 20 s
  up to 10 min, then once a minute (battery). Picking SOUL up (IMU) or asking a question offline restarts the fast
  phase. Simulated: hotspot switched on → SOUL joined within one fast scan (≤ 4.5 s) + the join [R: test].
  At boot the network that last reached the internet is joined **before any scan** (wake-polls have ~12 s).
- **Failures**: a wrong password (`AUTH_FAIL`, 4-way handshake timeout) is not retried until the network is saved
  again or 30 min pass, and the Wi-Fi page says "Wrong password" + the name; other failures back off 15 s → 8 min.
- **iPhone names**: an iPhone hotspot is called "Ana**’**s iPhone" (typographic apostrophe). A saved name matches the
  air after folding ’ ‘ ʼ ` → ', ASCII case and trailing spaces, and SOUL joins the name **exactly as on the air**.
- **iPhone hides an idle hotspot**: reports agree that devices on an iPhone hotspot are dropped after ~90 s without
  traffic [V: BGR], and that the hotspot is visible to new devices while the Personal Hotspot screen is open [V:
  Apple says "stay on this screen" for Bluetooth joins]. SOUL's fast scans + "pick it up" cover the first; the second is
  why the steps say to open that screen. **[U] measure on real iPhones (BRINGUP §4c).**

### 1.3 Captive portals (hotel, train, café)

After every join SOUL sends **one plain-HTTP request** to `http://connectivitycheck.gstatic.com/generate_204` without
following redirects (`classifyProbe`): **204** (or an empty 200) = online; a **redirect, a page or 511** = a login
page (captive portal); **no answer / 403 / 5xx** = no internet (e.g. a hotspot with mobile data off). Plain HTTP on
purpose: a portal can only intercept an unencrypted request (an HTTPS check would just fail and look like "no
internet"). Then:

- Captive / no internet: the screen says so ("Wi-Fi needs a login: use the hotspot", "The phone has no data"); SOUL
  Cloud waits for real internet (`netOnline()`); SOUL re-checks every 30 s and moves to any other saved network in
  reach (the captive one is skipped for 10 min).
- **SOUL cannot log in** (no browser, and "I agree" pages change per venue). We do not try: the fix is the hotspot.
- Privacy note: the check reveals SOUL's IP to Google (as every Android phone does). Open item: serve a plain-HTTP
  `generate_204` from SOUL Cloud and point `SUFLET_PROBE_URL` there (docs/07 §6.13 uses an HTTPS `/v1/ping`, which
  cannot tell a login page from no internet).

### 1.4 Offline behaviour

- **Eyes**: after 20 s without internet on the home face (and only when the brain needs the internet, not in *No AI*):
  `FaceState::Offline` — lids slightly heavier (0.2) and a left-right glance every ~9 s, "looking for a signal".
  Back online the lids open again. Picture: `sim/shots/everywhere/01-offline-eyes.png`.
- **Offline rules** (alarms, timers, reminders, notes) answer at once, as before.
- **Question queue** (`AskQueue`): anything the rules cannot do is kept — **5 questions at most** (the oldest goes),
  duplicates once, **dropped after 6 h** rather than answered late — and SOUL says "No internet right now. I'll ask as
  soon as I'm back online (N waiting)". Back online (3 s after the internet check passes; SOUL Cloud: once it says
  welcome; Bridge: once the computer is there), the questions go **one at a time** when SOUL is idle, with a "You
  asked earlier" capsule; a turn lost on the way goes back in the queue (twice at most). Kept in RAM: a restart or
  deep sleep loses them [R].

### 1.5 Tests and what is not verified

153 native tests pass (141 before + 12 in `test/test_suflet/test_wifi.cpp`: book, apostrophes, priority, fast
hotspot join, roaming home, wrong password, captive portal, no data, queue, offline eyes, typing the hotspot on SOUL,
every Wi-Fi screen). `lcd28` builds with zero warnings, `pio check -e lcd28` clean. Simulator scene `everywhere`
(9 stills in `firmware/sim/shots/everywhere/`). **Nothing has run on a board yet**: BRINGUP §4c lists the 9 checks
and the 4 numbers to write down (hotspot appears → online, with the iPhone screen closed, home → leave the hotspot,
current while searching).

---

## 2 · Data and latency of a Claude turn (common to every option)

| Item | Size [E] | Method |
|---|---|---|
| Typed turn over the open SOUL Cloud socket | ≈ 10–20 KB up+down | request JSON with context ≈ 2–6 KB (docs/07: ~2–2.5k input tokens per call are made **in the cloud**, the device sends only the text + context), answer 1–3 KB, TCP/TLS record overhead |
| Typed turn, own key, fresh TLS (B1) | ≈ 20–35 KB | + full TLS 1.3 handshake with certificate chain ≈ 5–8 KB, request carries the whole prompt (~8 KB) |
| Socket keepalive | ≈ 100 B per ping | today a ping every 25 s (docs/07 §6: server closes after 70 s silent) [R] |
| 8 s spoken question, today (`SUFLET_VOICE`) | **256 KB** | 16 kHz × 16 bit × 8 s WAV [R: `net.cpp transcribe`] |
| 8 s spoken question in Opus 16 kb/s | **16 KB** | Opus' wideband speech sweet spot is 16–20 kb/s [V: Xiph wiki] |
| 15 s spoken answer in Opus 24 kb/s | ≈ 45 KB | |

Latency of one turn (the model dominates: time to first token ≈ 0.3–0.9 s, then ~150 output tokens) [V: Claude
latency benchmarks, see sources; E for the totals]:

| Path | Network RTT | Network part of a turn | Turn total [E] |
|---|---|---|---|
| Home Wi-Fi | 15–40 ms | 0.05–0.3 s | 2–5 s |
| Phone hotspot | Wi-Fi hop + phone LTE/5G 30–60 ms | 0.1–0.4 s | 2–5 s |
| Built-in LTE Cat-1 bis | 50–100 ms [V: Zipit, Eseye] + idle→connected promotion ≈ 0.1–0.3 s [E] | 0.2–0.5 s (socket open), 0.5–1 s (fresh TLS) | 2.5–6 s |
| BLE tether (phone app) | 2 BLE hops 30–60 ms + app wake 0.1–1 s on iOS [E] + phone LTE | 0.3–1.5 s | 3–7 s |
| LTE-M | 100–300 ms realistic [E] (sources disagree, see §8) | 0.5–1.5 s | 3–7 s |
| NB-IoT | 1–10 s | seconds | **not interactive: rejected** |

Throughput is never the limit for text: Cat-1 bis gives up to 10 Mb/s down / 5 Mb/s up [V: Quectel], LTE-M ~1 Mb/s.

---

## 3 · Battery model (SOUL M, LiPo 803450, 1500 mAh, 3.7 V ≈ 5.6 Wh)

Board currents are the BRINGUP §4 estimates (not measured yet): awake ≈ 180–230 mA, asleep glow 70–100 mA, screen
off 45–70 mA, a Wi-Fi TLS turn +80–120 mA for < 3 s. **A carried day [E]**: 1 h awake, 15 h asleep/screen off at
≈ 60 mA, 8 h night deep sleep ≈ 0, 50 questions.

| Day | Wi-Fi at home | On the phone's hotspot | Built-in Cat-1 bis, pings every 25 s | Cat-1 bis, pings every 5 min, Wi-Fi radio off |
|---|---|---|---|---|
| Board (screen, CPU) | 230 + 900 mAh | same | same | same, minus ≈ 15–25 mA Wi-Fi modem sleep × 16 h ≈ –300 mAh [E] |
| Radio idle | in the board figure | in the board figure + scans when lost ≈ 3 mA × hours offline | module DRX ≈ 2–3 mA × 24 h ≈ 60 mAh [V: A7670 sleep < 2.5 mA] | ≈ 60 mAh |
| Keepalives | — | — | 144/h × 10 s RRC tail at ≈ 50 mA ≈ 20 mAh/h → **≈ 320 mAh** over 16 h [E] | 12/h → ≈ 27 mAh [E] |
| 50 turns | ≈ 4 mAh | ≈ 4 mAh | 50 × (3 s at ≈ 250 mA + 10 s tail at 50 mA) ≈ 17 mAh [E] | ≈ 17 mAh |
| **Total / day** | **≈ 1,130 mAh** | **≈ 1,150 mAh** | **≈ 1,530 mAh** | **≈ 930–1,230 mAh** |
| **Battery life** | **≈ 32 h** | **≈ 31 h** | **≈ 23 h (–30–40 %)** | **≈ 29–39 h (≈ –10 % to +10 %)** |

Take-aways: the screen and the always-on face dominate; the radio only matters through **how often it wakes**.
On cellular the SOUL Cloud ping must go from 25 s to ~5 min (a docs/07 §6 protocol change: the server's 70 s silence
rule moves too; carrier NAT timeouts are often 5–30 min [U: measure on 1NCE/Telekom]), and the Wi-Fi radio is
switched off while on cellular.

---

## 4 · b) BLE tether through a companion phone app

### 4.1 How it would work

SOUL already speaks BLE (the Claude Desktop Hardware Buddy link, `src/ble_link.cpp`) [R]. A tether adds a GATT service
"SOUL relay": SOUL writes a request frame (the same JSON it sends to SOUL Cloud today, ≤ 10 KB), the app sends it to
SOUL Cloud over HTTPS/WebSocket on the phone's data, and notifies the answer back in chunks (MTU 247; ESP32-S3 BLE 5
2M PHY: tens of KB/s in practice [E], plenty for text and Opus). End-to-end encryption device ↔ SOUL Cloud (the device
key, docs/07 §6) so the app only carries opaque bytes and never holds the user's tokens.

### 4.2 iOS

- An app with the `bluetooth-central` background mode is **woken when a connected peripheral sends a notification**
  and gets **~10 s** of execution from the last BLE packet [V: Punch Through; Apple Core Bluetooth background guide];
  **state restoration** relaunches it in the background after the system killed it [V: Apple]. A Claude turn of 2–7 s
  fits; a long streamed answer keeps it awake through its own BLE traffic.
- **What breaks it**: the user **force-quits** the app (iOS does not relaunch it for BLE until it is opened again)
  [V: Apple docs on state restoration], Low Power Mode and memory pressure terminate it [V: Apple: "the system may
  terminate them"], and a phone reboot needs one unlock first. For a device whose promise is "always works", that is
  a support problem we cannot fix from SOUL: SOUL simply goes offline with no way to tell the user why.
- **Setup**: AccessorySetupKit (iOS 18+) gives one-tap pairing and Bluetooth + Wi-Fi access without the usual
  permission prompts [V: Apple WWDC24, Punch Through] — worth using for setup even without a tether.
- **App Store**: a companion app for our hardware with setup, settings and the relay is a normal case; background modes
  must be used for what they declare (BLE accessory) [U: re-read guideline 2.5.4 at submission]; no MFi needed for
  BLE; privacy labels must declare that questions pass through. The app cannot switch the iPhone's hotspot on.

### 4.3 Android

- **CompanionDeviceManager** association + `REQUEST_COMPANION_START_FOREGROUND_SERVICES_FROM_BACKGROUND` exempts the
  app from background-start limits, and a `connectedDevice` foreground service keeps the link [V: Android developers].
  Reliable, with a persistent notification. Android 15+ enforces the permission/type pairing at service start [V].

### 4.4 What it needs to build [E]

| Piece | Effort |
|---|---|
| Firmware: relay GATT service, framing, retries, "phone link" as a transport next to Wi-Fi in `net.cpp`/`cloud.cpp` | 2–3 weeks |
| SOUL Cloud: accept relayed device frames (same `/v1/device` protocol, transport-agnostic) | 1 week |
| Android app (Kotlin): CDM pairing, foreground service, relay, setup screens | 4–6 weeks |
| iOS app (Swift): AccessorySetupKit, Core Bluetooth background + restoration, relay, setup screens | 5–7 weeks |
| QA on 10+ phones, store submissions, privacy policy | 2–3 weeks |
| **Total** | **≈ 3–4 months of one developer, ≈ €12–25k** (Romanian contractor rates [E]) |

**Verdict**: worth it later as a *companion* (setup, settings, notifications, and a fallback relay on Android), **not**
as the way SOUL reaches the internet on iPhone.

---

## 5 · c) Built-in cellular

### 5.1 Which radio

| Tech | Fit for SOUL | Why |
|---|---|---|
| **LTE Cat-1 bis** | **Yes** | 10/5 Mb/s, 50–100 ms RTT [V], one antenna, broad EU coverage on existing LTE, modules ≈ €10–14 |
| LTE-M (Cat-M1) | Maybe (fallback) | ~1 Mb/s, low power (PSM/eDRX), but latency and roaming coverage vary by operator [V: Onomondo, Hologram] |
| NB-IoT | No | seconds of latency; not for conversation |
| 2G fallback | Avoid | GSM bursts draw **≈ 2 A peaks** [V: A7670 hardware design] — too much for a 1500 mAh LiPo and the board's power path; networks are switching 2G/3G off |

### 5.2 Modules (Europe)

| Module | Tech | Size (mm) | Price | Notes |
|---|---|---|---|---|
| **Quectel EG800Q-EU** | Cat-1 bis | 15.8 × 17.7 × 2.4, 2 g [V] | €13.09 @1, **€11.35 @1000+** (distributor list) [V: SOS/MC-Technologies listings] | Small LGA, single antenna, LTE only (no 2G peaks) |
| **SIMCom SIM7672E** | Cat-1 bis (Qualcomm QCX216) | 24 × 24 × 2.4 [V] | $12.93 @100 (distributor) [V: Techship/Ineltek listings] | Pin-compatible family with A7670 |
| SIMCom A7670E | Cat-1 (+GSM) | 24 × 24 × 2.4 [V] | ≈ $8.7–9.6 [V: LCSC] | Cheapest, but the **GSM variant has 2 A peaks** [V]: only with 2G disabled, or skip |
| u-blox LEXI-R10 | Cat-1 bis | **16 × 16 × 2** [V: u-blox] | [U: quote] | Smallest; u-blox support and certifications |
| Nordic nRF93M1 | Cat-1 bis | [U] | [U: quote] | Pre-certified; Nordic tooling |
| Quectel BG95-M3 | LTE-M/NB-IoT/EGPRS | 23.6 × 19.9 × 2.2 [V] | ≈ €18–24 [V: listings] | Lower power, lower speed; for an LTE-M variant |

Pick for v2: **EG800Q-EU** (size, LTE-only) with **SIM7672E** as the second source; get LEXI-R10 and nRF93M1 quotes.

### 5.3 Power and the battery

- Supply 3.4–4.2 V straight from the cell (not the board's 3.3 V regulator); LTE power class 3 (23 dBm) [V: A7670
  design guide]; TX bursts ≈ 0.5–1 A on LTE-only modules [E: typical Cat-1 bis; confirm in the EG800Q hardware guide];
  sleep < 2.5 mA, off-leakage 20 µA [V: A7670].
- The 803450 cell (1500 mAh) at 1C is 1.5 A continuous; its protection board may trip at 2–3 A [U: seller data]. So:
  LTE-only module, **≥ 470 µF low-ESR bulk capacitance** at the module, a load switch so the module is fully off on
  Wi-Fi, and **no cellular below ≈ 3.5 V** (brown-out risk for the ESP32 when the cell sags).
- Battery effect: §3 (≈ –10 % with 5-minute keepalives and the Wi-Fi radio off on cellular; ≈ –30–40 % with today's
  25 s pings).

### 5.4 Antenna in an aluminium body

- The aluminium shell is a Faraday cage; the cellular antenna must sit in the **polymer base** (the RF window that
  research/08 already calls "an antenna window by design"), on its inside wall, with **≥ 10–15 mm clearance from
  aluminium** and the battery [E: typical keep-outs for FPC LTE antennas], fed by U.FL from the module.
- Low bands (B20 800 MHz, B8 900 MHz) need a ground ~ λ/4 ≈ 80–90 mm; SOUL M is ~ 80 mm across, so expect **low-band
  efficiency 10–25 %** (−6 to −10 dB) [E]; mid bands (B3 1800, B1 2100, B7 2600) will be fine. Rural/indoor coverage on
  B20 is the risk: measure with an operator-grade test before committing.
- **Coexistence**: B7 (2.6 GHz) and B40 sit next to Wi-Fi/BLE 2.4 GHz: keep the cellular antenna ≥ 20 mm from the
  ESP32's antenna, orthogonal if possible.
- **SAR**: SOUL is held in the hand and carried in a pocket; with a 23 dBm transmitter the end product needs a SAR
  assessment (EN 50566 / EN IEC 62209-2 class tests) [E: applies to body-worn/handheld < 20 cm].

### 5.5 SIM, eSIM and data plans (EU, today)

| Offer | Price [V] | For SOUL |
|---|---|---|
| **1NCE IoT Lifetime Flat** | **€12 one-off: 500 MB + 250 SMS for 10 years** per SIM; top-up €10 / 500 MB; SIM chip MFF2 **eUICC €2.50**, card €1–2 (price list June 2026) | Best fit: 500 MB ≈ 2+ years of typed use at 30 turns/day (≈ 18 MB/month [E]); voice-heavy use needs a top-up every ~6 months. Speed ≤ 1 Mb/s (fine). [U: confirm terms allow a consumer device] |
| Onomondo | pay as you go, ≈ €0.0025–0.003/MB, no fee for inactive SIMs (+ platform fees on quote) [V: Onomondo] | Cheaper per MB at scale; quote needed |
| Hologram | Europe PAYG $0.10/MB + $1/SIM/month (2023 list; current = quote) [V: Hologram legacy pricing] | Too expensive for voice |
| SGP.32 IoT eSIM (Telenor, Tele2, Soracom, KORE/Kigen) | commercial since spring–summer 2026 [V: IoT Portal, IoT Business News] | Lets us switch operator over the air later; pair with an MFF2 eUICC |

Choose a **soldered MFF2 eUICC** (no slot to seal in the aluminium body, survives drops), 1NCE for the pilot of v2,
SGP.32 capable so the profile can be changed later. iSIM (SIM inside the modem) exists on Nordic's nRF9151
(LTE-M/NB-IoT) [V] but not yet on the Cat-1 bis modules above [U].

### 5.6 Certification

- **RED** (CE): a cellular radio in the end product adds radio tests (EN 301 908-1/-13 for LTE UE), EMC
  (EN 301 489-1/-52), safety (EN 62368-1) and **SAR** (§5.4), even with a pre-certified module [E: the module's
  certificate covers the module, not the product]. **EN 18031** (RED cybersecurity, mandatory since 1 Aug 2025 [V])
  already applies to SOUL's Wi-Fi; the cellular interface joins its scope.
- **GCF**: not legally required in the EU; operators may ask; with a GCF-certified module a product is usually
  accepted on the operator side [V: Techship]; full GCF ≈ $15–50k [V: m2msupport] — avoid by using a certified module
  and not changing its firmware. **PTCRB** only for North America (not in v2).
- Budget: **≈ €10–25k one-off** [E: lab quotes needed], on top of the €5–12k Wi-Fi CE/RED already in docs/01.

### 5.7 BOM delta per unit (v2, Cat-1 bis)

| Item | @25 [E] | @1k [E] | Basis |
|---|---|---|---|
| Module EG800Q-EU (or SIM7672E) | €14 | €11.35 | distributor lists [V] |
| LTE FPC antenna 698–2690 MHz + U.FL cable | €5 | €2.50 | typical Taoglas/Molex FPC pricing [E] |
| MFF2 eUICC + 10-year 500 MB plan (1NCE) | €14.50 | €14.50 | €2.50 + €12 [V] |
| Carrier PCB 25 × 30 mm 4-layer (module, bulk caps, load switch, level shifting, ESD), assembled | €12 | €4 | JLC-class small runs [E] |
| Extra assembly, RF check, SIM activation | €3 | €1.50 | [E] |
| **Total** | **≈ €48** | **≈ €34** | Retail: + €69 at a typical 1.5–2× hardware multiple [E] |

### 5.8 What changes in CAD (not edited here)

1. **Polymer base = RF window**: a conformal FPC antenna on the inside wall of the base, ≥ 10–15 mm from the
   aluminium seam and from the battery; no metal (magnets, steel washers, laser-mark ground spot) within 10 mm.
2. **Module placement**: the carrier PCB (25 × 30 × ~4 mm with the module) in the base, next to the battery, with a
   short U.FL run to the antenna; a thermal pad to the base, not to the aluminium (keep the RF ground short).
3. **Battery bay**: keep the 803450 (1500 mAh); if the base grows by ~3 mm, an 1800–2000 mAh cell becomes possible
   [U: check the 8.6 × 34.5 × 50.5 mm bay in `prototip/README.md`].
4. **No SIM door** (soldered eUICC); a test-point pad for the module's USB (firmware updates, RF tests).
5. Keep ≥ 20 mm between the LTE antenna and the ESP32 module's 2.4 GHz antenna.

---

## 6 · Microphone and speaker: make them standard

On the go people talk, they do not type on a 2.8″ round keyboard. Today both are **optional build flags** on SOUL M
(`-DSUFLET_MIC_INMP441=1`, `-DSUFLET_SPK_MAX98357=1`, voice behind `-DSUFLET_VOICE=1`) [R: `platformio.ini`,
`src/audio.cpp`]. What exists:

- Hold the glass → record up to **8 s of 16 kHz PCM** in PSRAM → a **WAV (256 KB)** to OpenAI's transcription API
  **with the owner's OpenAI key only** → the text goes through the normal ask path (or becomes a dictated note) [R:
  `net.cpp transcribe`, `Os::voiceText`]. The speaker plays the alarm tone [R: `AlarmTone`].

What is missing for an on-the-go AI device:

| Missing | Why it matters on the go | Size |
|---|---|---|
| **Opus encoding on the device** (16 kb/s wideband) | 16× less data than WAV (16 KB vs 256 KB per 8 s): hotspot and LTE friendly, faster upload | ESP-IDF audio codec / libopus fixed-point [U: CPU load on S3, expect a fraction of one core at 16 kHz] |
| **STT through SOUL Cloud** (owner's key kept in the cloud, B2) | today voice needs an OpenAI key on the device; SOUL Cloud and Claude-only owners have no voice | cloud endpoint + protocol frame (docs/07 §6 change) |
| **Spoken answers** (TTS → Opus → speaker) | a glance-free answer while walking | cloud TTS with the owner's key + Opus decode + I2S out |
| **Streaming** while recording; longer than 8 s | latency and longer questions | firmware ring buffer + chunked upload |
| Queue voice offline | today a spoken question offline is transcribed only online | keep the Opus clip (≈ 16 KB) in the offline queue |
| AMOLED 1.75 board's ES7210/ES8311 codec path | the board has 2 mics + a speaker, but the firmware's I2S path is the INMP441/MAX98357 one [R] | driver work |

Parts to make standard (per unit): **MEMS I2S mic** (ICS-43434 class; the INMP441 is old and should be checked for
end-of-life [U]) ≈ €1.5–3, **MAX98357A** class-D amp ≈ €1–2, **15 × 11 mm speaker** €1.2–2 [V: docs/01 P0-03] →
**≈ €4–7 @25, ≈ €2–3.5 @1k** [E]. CAD: a Ø0.8–1 mm acoustic port with mesh and gasket for the mic, a grille for the
speaker in the polymer base. A speaker also gives alarms and "You asked earlier" an audible cue.

---

## 7 · Recommendation and roadmap

**Hybrid, in order of cost and certainty: Wi-Fi first, the phone's hotspot second, built-in LTE Cat-1 bis third.
The BLE tether is not the main path.**

| Phase | When | What | Cost |
|---|---|---|---|
| **v1 · pilot, 10–25 units** | now → Dec 2026 | Firmware 1.5.0: multi-network + hotspot + captive detection + offline queue (built). **Mic + speaker standard.** Measure on the pilots: how often they use the hotspot, hotspot-appears → online time on iPhone/Android, battery per day, data per day (log bytes). BRINGUP §4c on the board first. | €0 radio; mic/speaker ≈ €4–7/unit |
| v1.x firmware | Q1 2027 | Opus voice + STT/TTS via SOUL Cloud; voice in the offline queue; keepalive made adaptive (protocol change, docs/07 §6); queue persisted in NVS; own `generate_204` on SOUL Cloud | firmware + cloud work |
| Companion app (optional) | Q1–Q2 2027, only if the pilot asks | Android first (CDM: setup + relay), iOS for setup (AccessorySetupKit), relay only as best effort | ≈ €12–25k |
| **v2 · 500–1k units** | H2 2027 | **Built-in LTE Cat-1 bis** (EG800Q-EU / SIM7672E), soldered MFF2 eUICC, 1NCE 10-year plan (or SGP.32 provider), FPC antenna in the polymer base, Wi-Fi first / cellular when no saved network is in reach, 5-min keepalives on cellular. Sell as "SOUL Go" (+ €69) or standard. | ≈ €34/unit @1k + ≈ €10–25k certification |

Why not LTE in v1: it needs a carrier PCB that the Waveshare board does not have, a power path from the cell, a new
base, SAR and cellular RED tests — months and €10–25k for 10–25 units — while the hotspot gives the same "works
everywhere" for €0 to people who carry a phone anyway.

---

## 8 · Open risks

1. **Nothing in §1 has run on a board** (BRINGUP §4c). In particular: the ESP32 driver's disconnect reasons on a wrong
   password, async scans while the RGB panel streams from PSRAM, and NVS writes on joins (`wlast` is written only when
   the network changes; flash writes glitch the panel, docs/07 §6.5).
2. **iPhone hotspot visibility** after its idle timeout: SOUL may need the user to open the hotspot screen. Measure.
3. **Fast scans cost battery** (≈ +40–80 mA average for the first 3 min after a drop [E]); tune after measuring.
4. The **offline queue is RAM-only** (a restart or deep sleep loses it) and answers come back on the face, not as a
   notification list: fine for 5 questions, revisit with voice.
5. **Captive check uses Google's endpoint**; move to our own plain-HTTP endpoint.
6. **Cellular keepalive** needs a protocol change (25 s → minutes) agreed by the cloud and firmware sides (docs/07 §6
   is normative).
7. Sources disagree on **LTE-M vs Cat-1 latency** (one says LTE-M 10–15 ms, others say Cat-1 is ~50 ms faster than
   LTE-M) [V: both in the sources]: measure on the operator we pick; it does not change the Cat-1 bis choice.
8. **1NCE terms for consumer devices**, module prices at 1k (quotes, not distributor lists), certification lab
   quotes, low-band antenna efficiency in our base: all [U] until quoted or measured.
9. App Store review of a relay companion app [U].

---

## Sources (checked 3 Oct 2026)

- Apple, *Personal Hotspot* support (Allow Others to Join, Maximize Compatibility, name from Settings › General ›
  About): <https://support.apple.com/en-us/111785>; PhoneArena, iPhone 12 5 GHz hotspot:
  <https://www.phonearena.com/news/iphone-12-5ghz-hotspot_id128072>; BGR, iPhone hotspot behaviour (90 s idle
  disconnect): <https://www.bgr.com/2272041/using-iphone-hotspot-wrong-why/>
- SIMCom A7670E: LCSC <https://www.lcsc.com/product-detail/C7435296.html>, hardware design
  <https://files.waveshare.com/wiki/A7670E-Cat-1-GNSS-HAT/A7672X_A7670X_Series_Hardware_Design_V1.03.pdf>,
  <https://www.espboards.dev/sensors/a7670/>
- SIMCom SIM7672: <https://www.ineltek.com/en/sim7672-lte-cat-1-bis-module-by-simcom-qcx216-based/>,
  <https://techship.com/product/simcom-sim7672e-mngv-lte-cat-1bis-smt/?variant=001>
- Quectel EG800Q: <https://www.quectel.com/product/lte-eg800q-series/>,
  <https://www.soselectronic.com/en-us/articles/quectel/quectel-eg800q-eu-lte-module-for-even-greater-flexibility-of-iot-applications-2871>,
  <https://mc-technologies.com/en/produkt/quectel-eg800q-eu/>
- Quectel BG95: <https://www.quectel.com/product/lpwa-bg95-cat-m1-cat-nb2-egprs-series/>
- u-blox LEXI-R10: <https://www.u-blox.com/en/u-blox-empowers-global-connectivity-new-ultra-compact-lte-cat-1bis-cellular-modules>
- Nordic nRF93M1 / nRF9151: <https://www.nordicsemi.com/Products/nRF93M1/Modules>, <https://www.nordicsemi.com/Products/nRF9151>
- 1NCE price list (June 2026): <https://a.storyblok.com/f/335000/x/23bb62a8c3/1nce_gmbh_price_list_01_2026.pdf>,
  <https://www.1nce.com/en-eu/1nce-connect/pricing>
- Onomondo pricing: <https://onomondo.com/pricing/>; Hologram pricing: <https://www.hologram.io/pricing/legacy/>,
  <https://www.hologram.io/pricing/>
- SGP.32 in 2026: <https://iotportal.co.uk/news/sgp32-uk-europe-iot-esim-2026/>,
  <https://iotbusinessnews.com/2026/07/09/soracom-brings-sgp-32-iot-esim-orchestration-to-commercial-availability/>
- LTE standards / latency: <https://www.zipitwireless.com/blog/lte-cat-1-bis-a-comprehensive-guide-to-its-benefits-and-uses>,
  <https://www.eseye.com/resources/iot-explained/lte-cat-1-bis-for-iot-and-m2m-everything-you-need-to-know/>,
  <https://onomondo.com/blog/lte-standards-for-iot-comparison/>, <https://www.hologram.io/blog/nb-iot-vs-cat-m1-vs-cat-1/>
- iOS Core Bluetooth background: <https://developer.apple.com/library/archive/documentation/NetworkingInternetWeb/Conceptual/CoreBluetooth_concepts/CoreBluetoothBackgroundProcessingForIOSApps/PerformingTasksWhileYourAppIsInTheBackground.html>,
  <https://punchthrough.com/leveraging-background-bluetooth-for-a-great-user-experience/>; AccessorySetupKit:
  <https://developer.apple.com/videos/play/wwdc2024/10203/>, <https://punchthrough.com/ios18-accessorysetupkit-everything-ble-developers-need-to-know/>
- Android background BLE / CDM: <https://developer.android.com/develop/connectivity/bluetooth/ble/background>,
  <https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start>,
  <https://developer.android.com/develop/background-work/services/fgs/service-types>
- RED cybersecurity / EN 18031: <https://developer.espressif.com/blog/2025/04/esp32-red-da-en18031-compliance-guide/>,
  <https://www.nemko.com/blog/cybersecurity-in-europe-en-18031-is-now-a-harmonized-standard>
- GCF and module certification: <https://m2msupport.net/m2msupport/gcf-process-costs-timeframe-and-labs/>,
  <https://techship.com/blog/end-certified-modems-vs-pre-certified-modules-whats-the-right-path-1/>
- Opus: <https://wiki.xiph.org/Opus_Recommended_Settings>, RFC 6716 <https://www.rfc-editor.org/info/rfc6716/>
- Claude latency: <https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency>,
  <https://www.kunalganglani.com/blog/llm-api-latency-benchmarks-2026>
