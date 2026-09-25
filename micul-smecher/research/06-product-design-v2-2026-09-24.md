# Product design v2 — "SUFLET Pebble" (raw, 2026-09-24)

Tags: **[V]** verified today (fetched page or project CAD/STEP data) · **[K]** from knowledge (spec sheets/reviews as remembered, verify before quoting publicly) · **[E]** estimate / engineering judgement.
WebSearch budget was exhausted in this session; only direct WebFetch of known URLs was possible.

## 0. Constraints inherited from v1 (project data)
- Waveshare ESP32-S3-Touch-AMOLED-1.75: round 466×466 AMOLED, CO5300, CST9217 touch, ES8311 + ES7210 (2 mics, AEC), speaker on MX1.25 header (8 Ω 2 W "2030" speaker in kit), QMI8658 IMU, PCF85063 RTC, AXP2101 PMU, PWR + BOOT keys, 16 MB flash / 8 MB PSRAM, $29.99–39.99; case and GPS variants exist [V, waveshare.com product page].
- Mechanicals from STEP (in `cad/micul_smecher.scad`) [V]: cover glass Ø48.96, flat front Ø44.16, active/touch Ø43.76, module+PCB Ø46.0, deepest part at the board edge 12.7 mm (8-pin header), 8.9 mm under the battery footprint, USB-C face r = 23.8.
- v1 coin shell on 1.75 with 400 mAh + kit speaker stacked = **Ø60.8 × 23.5 mm**; without speaker 17.7 mm [V, cad/README]. The Ø is set by the insert bosses outside the glass; the board alone allows ~Ø51.
- ppi: 466 px / 43.76 mm ≈ 10.6 px/mm ≈ 270 ppi [E from V].
- Firmware sets AXP2101 charge current to 200 mA for 400–500 mAh; must raise to ~500 mA (0.5C) for a 1000 mAh cell [V, firmware/src/main.cpp].
- Waveshare 2.06" AMOLED board: **rectangular** 410×502, watch form factor, same audio/IMU/PMU, $29.99–31.99 [V]. The 1.8" is also rectangular [K]. → no bigger *round* AMOLED ESP32 dev board; 1.75" is the round ceiling at maker level [E].

## 1. Reference objects
| Object | Size / weight | Materials | Carry & input | Worked | Failed | Lesson for SUFLET |
|---|---|---|---|---|---|---|
| Rabbit r1 (Teenage Engineering, 2024, $199) | 2.88" touchscreen [V]; ~78×78×13 mm, ~115 g, 1000 mAh [K] | orange plastic | pocket; PTT button, scroll wheel, rotating camera, IMU [V] | object design, colour, the wheel, $199 no sub | 130k sold → ~5k daily users by Sep 2024; MKBHD "barely reviewable" [V]; battery at launch, "an app" | great object ≠ daily reason. Ship jobs that work every day. |
| Humane AI Pin (2023, $699→$499 + $24/mo) | ~34 g pin + ~20 g magnetic battery booster [K] | aluminium, glass | magnet through clothing; touchpad, gestures, voice, laser projector [V] | the magnetic-through-fabric mount | overheating (ice packs; projector 9-min cap), battery, "can only rely on it to tell the time" (Verge); bricked 28 Feb 2025 [V] | never replace the phone; no projector; no forced sub; thermal budget; survive the server. |
| Playdate (Panic + TE, 2022) | **76×74×9 mm, 86 g**, 2.7" 400×240 1-bit [V] | yellow plastic | pocket; D-pad, A/B, **crank**, IMU, mic [V] | a single signature input, seasons of content; $179→$229 [V] | battery recall 2022 [V, prior research] | one unmistakable physical gesture; content cadence. |
| Tamagotchi (1996→Paradise 2025) | keychain egg ~40×45×15 mm, ~20 g [K]; 3 buttons [V] | plastic | chain; 3 buttons | 98M+ units [V]; care loop; egg shape = "creature" | fades after weeks without new content | shape says "creature"; daily ritual; minimal buttons. |
| Nothing Ear (1) / Phone (1) | Ear (1) case ~58.6×58.6×23.7 mm, ~57 g [K] | transparent PC showing internals; Glyph LEDs | pocket; pinch | transparency as brand; Glyph = light as language [V earlier research] | Glyph use-cases thin | show the "soul" through translucent/frosted material; light as the language. |
| Oura ring | ~4–6 g, ~2.5–2.9 mm thick [K] | titanium, PVD | worn 24/7; no input | 5.5M rings, ~$1B revenue [V earlier] — invisible, no screen, value in the app | subscription friction | passive value, zero ceremony. |
| Apple Watch / AirTag | Watch 41–49 mm cases, ~30–62 g, 1.7–1.9" displays [K]; AirTag Ø31.9×8 mm, 11 g [K] | aluminium/ceramic/Ti, glass | wrist / keyring; Digital Crown, side button, raise-to-wake | Digital Crown = precise scrolling on a small round-ish UI; raise-to-wake | — | raise/pick-up to wake; a crown/rim is the best scroll input for round UIs. |
| Plaud NotePin | **~17 g** (0.59 oz on product page) [V]; ~50×20×10 mm [K]; 20 h recording, 40 days standby, 64 GB [V] | aluminium | **magnetic pin, clip, lanyard, wristband** [V]; one press | one clear job (record → transcript/summary); >2M devices, ~50% pay [V earlier] | — | voice notes are a paid-for job; offer many carry accessories. |
| Meta Muse Charm (announced Sep 2026) | keychain with small screen + animated avatar [V earlier] | — | keyring; **fingerprint to talk** [V earlier] | validates "charm + avatar + voice" | no price/specs yet | privacy gesture must be ours and visible; speed. |
| Casio Moflin ($429) | ~180 mm body, ~280 g [K]; no screen | fur | hold in lap; touch/stroke sensors, sound | >20k units [V earlier]; being stroked and responding | no "useful" function | petting/holding as input (capacitive back = cheap version). |
| Pebble watch | original 52×36×11.5 mm, 38 g, 7-day battery [K; 38 g/7 days V]; Time Round 38.5 mm, ~7.5 mm, 2-day battery [K] | plastic / steel | 4 buttons; 2025 Core Devices revival: Pebble 2 Duo $149, Time 2 $225, Round 2 $199 [V/Wikipedia] | long battery, buttons, open community (Rebble) | Round's 2-day battery hurt; company died 2016 [V] | battery life is a feature; open ecosystem outlives the company; buttons > touch for eyes-free. |
| TE OP-1 / Pocket Operators | OP-1 ~282×102×14 mm, ~590 g aluminium [K]; PO bare PCB, 2×AAA [K] | anodised Al / bare PCB | tactile encoders, colour-coded | fixed visual language, playful graphics on tiny screens, honest materials | — | strict graphic language for SufletOS; tactile physical controls. |
| Dieter Rams | 10 principles: innovative, useful, aesthetic, understandable, unobtrusive, honest, long-lasting, thorough, environmentally friendly, as little design as possible [V Wikipedia]; Braun T3 pocket radio (1958) [K] | — | — | — | — | "less but better": one button, one screen, one gesture. |
| Jony Ive / LoveFrom + OpenAI device | pocket-size, screen-free, contextually aware; not before end Feb 2027 [V earlier research]; Ive's stated aim: products that make people less anxious [K/R] | obsessive materials | — | — | — | calm technology; care in materials and "feel in the hand". |
| River pebbles / palm & worry stones | palm stones ~40–65 mm long, 30–45 wide, 15–25 thick; worry stones ~35–45 × 30–35 × 8–10 mm with ~20 mm thumb dimple [K/E] | stone, polished | held, rubbed, pocketed | universally comforting, no instructions needed | — | the organic ellipse with a soft domed back is the most "hold-able" form there is. |

## 2. Ergonomics (palm / pocket / one hand) [K/E]
- Adult hand breadth (metacarpal) ≈ 70 mm (5th pct women) to ≈ 97 mm (95th pct men); palm length ~95–115 mm. An object ≤ 70 mm long sits inside the palm of ~all adults; 55–70 mm is the "palm stone" range.
- One-hand use with the thumb on the face: the thumb covers comfortably ~Ø40–50 mm when the object rests in the fingers → a 44 mm active area is thumb-reachable edge to edge.
- Thickness: 15–22 mm feels like a stone; >25 mm reads as a "puck/brick"; <12 mm needs a lanyard or it slips. Taper edges so the *perceived* thickness is lower than the centre thickness.
- Pocket: women's front jeans pockets are much shallower than men's (The Pudding 2018: ~48% shorter on average) [K] → keep the longest dimension ≤ ~70 mm and thickness ≤ ~22 mm; no protrusions (crowns snag).
- Weight: charms < 40 g; pocket objects comfortable at 60–120 g (Playdate 86 g, r1 ~115 g). **Sweet spot 70–95 g**: feels solid/premium without dragging a pocket or a lanyard. Target density ~1.3–1.8 g/cm³ (pure plastic ~1.1 feels "toy").
- Edge radii: nothing < 1 mm anywhere the hand goes; outer silhouette radii ≥ 3 mm, section radii 6–15 mm for a pebble; bezel lip ≤ 0.5 mm proud of the glass.
- Legibility: minimum comfortable cap height ≈ 0.4–0.5° visual angle → at 35 cm (hand) ≈ 2.5–3 mm ≈ 28–32 px; at 65 cm (desk, on stand) ≈ 5–6 mm ≈ 55–60 px. Usable inscribed square on Ø43.8 = 31 mm → ~5 short lines in hand, ~3 at desk. **Glanceable cards, not documents.**
- Round screen sizing: 1.75" (Ø44 active) is at the Apple-Watch-45 mm level — the largest that keeps a < 70 mm object; bigger round needs a > 75 mm body.

## 3. Form options [E]
| | A. Pebble (recommended) | B. Coin with rotating rim | C. Capsule / egg |
|---|---|---|---|
| Plan | oval 68 × 60 mm (prod) / 72 × 64 (proto on Waveshare) | round Ø62–64 | 82 × 44 stadium or egg |
| Thickness | 19 mm centre, ~12 mm at edge (prod); ~24/15 proto | 17–19 flat | 20–22 |
| Weight | 75–90 g | 85–100 g (metal rim) | 90–110 g |
| Battery | 1000 mAh (523450 in the oval) | 800–1000 mAh | 1200–1500 mAh |
| Speaker | sealed 1813/2015 box in the lower lobe | tight → small 1511 | best (dedicated end chamber) |
| Input | touch + 1 button + IMU + capacitive back | touch + rim (hall/magnetic encoder) + button | touch + button + wheel |
| Pros | most holdable, reads "creature", pocket-safe, no moving parts | best navigation for SufletOS, desk-friendly, "watch-like" | best acoustics/battery |
| Cons | no precise scroll | rim = sealing/dust, cost, snags, looks like a watch | loses the round-being, reads remote/Rabbit |

**Choice: A**, with the rim idea kept as a "Pro/desk" variant later. Reasons: palm-stone ergonomics; pocket safety; cheapest tooling (2-part shell); strongest emotional read (stone that opens its eyes); the dimensioned oval leaves exactly the lower lobe for a sealed speaker + LRA and a 1000 mAh cell behind the board.

Proposed spec (A):
- Outline: soft oval 68 × 60 mm, display centred 3–4 mm above centre; section: domed back (R ≈ 60–80), 19 mm at centre, ~12 mm perimeter; front: glass flush with a 0.3–0.5 mm frosted lip.
- Proto on Waveshare 1.75: ~72 × 64 × 24 mm (edge header at 12.7 mm + 523450 cell + foam + wall), ~95–105 g.
- Materials: body frosted translucent PC (RF-transparent, diffuses a faint glow from a ring LED/AMOLED edge — "the soul shows through"); premium edition in matte zirconia ceramic back (RF-transparent, cool, heavy → ~110 g) or bead-blasted anodised aluminium *front ring only* (keep the antenna zone non-metallic). Avoid soft-touch coatings (hydrolyse → sticky in 2–4 years).
- Inputs: capacitive touch screen (tap/swipe/hold); **one physical button** on the upper-right edge, flush, with travel (hold = talk — mic hardware-gated by the button, the privacy promise made physical; double-press = cancel/back); IMU (pick-up wake, face-down = do not disturb / mute, shake, tilt-to-scroll lists); capacitive electrodes inside the back (ESP32-S3 touch pads): "held"/petting detection. No squeeze (needs strain gauges, skip).
- Carry: detachable wrist strap / lanyard through a hidden bar at the top; magnetic clip accessory (steel plate inside shell, magnet clip outside — Humane/Plaud lesson); "Cuib" (nest) dock: weighted stone-shaped stand with magnetic alignment + pogo-pin charging, holds it at 15–20° for desk / Claude-Code mode; USB-C hidden under the strap bar for dev units only.

## 4. Features ranked (value × feasibility on ESP32-S3 + cloud) [E]
| # | Feature | Runs where | Value | Feasibility | Phase |
|---|---|---|---|---|---|
| 1 | Living eyes offline (existing) | device | ★★★★★ | done | v2.0 |
| 2 | Hold-to-talk assistant (Claude / ChatGPT) | device mic → Wi-Fi (or phone BLE relay) → our EU server → LLM + TTS | ★★★★★ | high (xiaozhi-class stack, MIT) | v2.0 |
| 3 | Reminders / alarms / timers by voice | cloud parses → device RTC alarm + speaker + LRA | ★★★★★ | high | v2.0 |
| 4 | Voice notes → Obsidian / email / phone | Opus to PSRAM/flash → upload → transcript + summary → email / Git (Obsidian) / Notion / app | ★★★★★ (Plaud proves willingness to pay) | high | v2.0 |
| 5 | Claude Code / Cowork approvals | BLE Hardware Buddy (existing) | ★★★★ (beachhead) | done | v2.0 |
| 6 | Focus timer / Pomodoro with "concentrated eyes" | device | ★★★★ | high | v2.0 |
| 7 | Morning briefing (calendar, weather, 1 reminder) | cloud composes (calendar connector, weather API), device shows 3 cards + speaks | ★★★★ | medium-high | v2.1 |
| 8 | Notification glance + music control | BLE: iOS ANCS/AMS work without an app; Android needs companion app | ★★★ | medium | v2.1 |
| 9 | Mood check-in + diary of the day | cloud (existing `ai/` journal) | ★★★ | high | v2.1 |
| 10 | MCP actions (smart home, send message) with on-device confirm (hold = approve) | cloud agent + user's connectors | ★★★ | medium; risk of misfire → confirm every write | v2.2 |
| 11 | Find my phone | companion app | ★★ | medium | v2.2 |
| 12 | Translate (phrase mode) | cloud | ★★ | medium; phone does it better | later |
Keep OFF: camera, projector, LTE/SIM, always-on listening/wake word by default, web browsing, typing, long reading, payments, app store, anything replacing the phone, anything that needs > ~2 s before first feedback without "thinking" eyes. Local fallback for everything time-critical (alarms fire offline).

SufletOS principle: the eyes are the home screen and the status bar. Content appears as a card *below shrinking eyes*; max 3 lines; swipe up = card stack (next event, timer, last note), swipe down = quick toggles (DND, volume, Wi-Fi), button hold = talk anywhere. Every screen returns to the eyes after 8–10 s.

## 5. Components & BOM delta (vs v1 voice, prod at ~1k units) [E]
| Item | v2 choice | Δ cost |
|---|---|---|
| Display | 1.75" 466² AMOLED (CO5300) vs 1.2–1.43" | +€3–5 |
| Battery | 1000 mAh LiPo 523450 (5.2×34×50, ~19 g) + PCM vs 500 mAh | +€1.5–2.5 |
| Speaker | sealed box 1813/2015 (~0.7–1 W) + acoustic mesh | +€0.8–1.5 |
| Haptics | LRA (Ø10 Z-axis or X-axis ~12×4) + DRV2605L/AW86224 | +€1.5–2.5 |
| Charging | pogo pins + magnets in shell | +€1–2 |
| Pocket sensor | ALS/proximity (e.g. VEML7700 / LTR-553) | +€0.5–1 |
| Shell | bigger 2-part frosted PC + strap bar + steel plate | +€2–4 |
| Strap/lanyard | included | +€1–2 |
| Cuib dock (weighted, pogo) | included in premium SKU or €19–29 accessory | €4–8 own cost |
| **Total delta** | | **≈ +€11–20 → COGS ~€50–70 @1k; ~€38–50 @10k** |
Retail consequence (≥ 2.5× landed): €149 base / €179–199 with dock / €249+ ceramic edition.
Dev-kit prototype: board $35 + 1000 mAh cell €8 + DRV2605L+LRA €10 + SLA shell €15 + strap €3 ≈ €75–85.

Battery life estimate (1000 mAh, 3.7 V) [E; measure on hardware]:
| Mode | Current | Daily time | mAh/day |
|---|---|---|---|
| Ambient eyes (dim, 2–5 fps, BLE connected) | ~12–18 mA | 10 h | 150 |
| Awake interaction (30 fps, touch) | ~70–100 mA | 1 h | 85 |
| Voice (Wi-Fi streaming + speaker) | ~200–300 mA | 20 min | 85 |
| Pocket/face-down (panel off, BLE) | ~3–6 mA | 5 h | 25 |
| Night sleep (RTC + IMU wake) | ~1–3 mA | 8 h | 15 |
| **Total** | | | **~360 mAh → ~2.5 days typical; ~1–1.5 days heavy; > 10 days standby** |
Rule: 0.5C charge (500 mA) → ~2.5 h to full on the dock. Replaceable-with-tools battery for EU Battery Regulation (Feb 2027).

## 6. Sources
- https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm [V]
- https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-1.75 (3D zip: files.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-1.75/ESP32-S3-Touch-AMOLED-1.75-3D.zip, 4.8 MB, downloaded) [V]
- https://www.waveshare.com/esp32-s3-touch-amoled-2.06.htm [V]
- https://en.wikipedia.org/wiki/Rabbit_r1 [V]
- https://en.wikipedia.org/wiki/Humane_AI_Pin [V]
- https://en.wikipedia.org/wiki/Playdate_(console) [V]
- https://en.wikipedia.org/wiki/Tamagotchi [V]
- https://en.wikipedia.org/wiki/Pebble_(watch) [V]
- https://en.wikipedia.org/wiki/Dieter_Rams [V]
- https://www.plaud.ai/products/notepin [V]
- Project data: micul-smecher/cad/micul_smecher.scad + cad/README.md (STEP-verified 1.75 dimensions), firmware/src/main.cpp, research/01–05 [V]
- Everything tagged [K] is from memory of spec sheets/reviews (r1 78×78×13/115 g, AI Pin weights, Ear (1) case, Oura, AirTag, NotePin size, Moflin, OP-1, ergonomic percentiles, pocket study) — verify before public use.
