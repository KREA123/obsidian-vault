# SOUL: the dock and the charging capsule as design objects and rituals (2026-09-24)

Tags: **[V]** page fetched today (URL in §9) · **[V-s]** web-search summary today, page not opened (secondary) · **[V-0x]/[V-r]** verified earlier today in note 0x / sibling r-note · **[K]** background knowledge, verify before quoting · **[E]** estimate / engineering judgement.
Builds on 06 (Cuib dock idea, battery model), 07 (press-the-eye, mic gating), 08 (porcelain egg-cradle, CMF), r-icons (L6 "the dock is a home and a stage", capsule "thock", unboxing), r-creatures (R8 tipping limit + Daruma base, R10 "the capsule carries the brand mark"), renders/v4 (PEBBLE 64×72×18, CLOUD 84×66×18, DROP 64×80×18, AMULET Ø64×18; speaker = 7 × Ø0.6 holes on the right edge; 2 gold contacts on a flat base; no visible USB). Not repeated.
**Founder rules applied:** front = body + glass only (so every light, mark, grille and control lives on the DOCK, never on SOUL's face) · speaker on the side/back · charging at the bottom · a SOUL dock / "charging capsule" is part of the product · no loop on the body (the capsule may have one) · stands upright · premium, cheap to make.

---

## 0. What this note concludes
1. **The charging object is half the product and most of the retention.** People pay **$99 for a ring's charging case** (Oura, Jan 2026 [V]). AirPods went 14–16M → 60M/yr with the case as the daily ritual [V]. Docks turn devices into something else: Switch → TV console, Pixel Stand/Tablet → smart display, iPhone → StandBy clock [V].
2. **Bottom contacts are the only charging tech that fits the brief.** Qi needs a Ø20–30 mm flat coil ≤ ~5 mm from the pad [V typical gap], and SOUL's base land is only 24–28 × 14–18 mm (r-creatures R8). A USB-C port means a hole and a plug (a lever) under an 85 g standing object.
3. **EU trap.** Directive 2022/2380 forces a USB-C receptacle on listed categories (incl. **portable speakers, headsets, handheld videogame consoles**) that charge by wire. A charging station doesn't exempt you (only earbuds count together with their case), and "proprietary + USB-C adapter" is explicitly not allowed [V EU guidance Q3, Q22]. Category = *primary intended use* [V Q11]. SOUL must be positioned and documented as an AI companion / assistant, not as a speaker or game. Keep a **hidden USB-C in the sole** in the DVT tooling as insurance.
4. **Freeze the "sole" as a platform**: 5 flush gold targets + 2 polarity-keyed magnets, identical on all four shapes. One dock fits the whole family; the 30-pin → Lightning switch orphaned every iPod dock [V-s].
5. **The dock should do 5 things beyond charging**: stand/tilt (makes SOUL *tappable*), night light, sleep/sunrise ritual, a *physical* privacy state (lid/dome closed → mic hardware-off), and a USB tether to the laptop for the Claude buddy. A speaker dock is optional. No Bluetooth in any dock: Panic paused the Playdate Stereo Dock over BT crashes, pairing and cost [V].

---

## 1. Reference docks, cases and capsules

| Object | Charging tech & facts | The ritual / signature | Lesson for SOUL |
|---|---|---|---|
| **AirPods case** | 44.3×21.3×53.5 mm, 38 g; case cells 398 → 519 → 345 mAh; Qi from gen 2, MagSafe on later cases, the gen 4 case dropped the magnets to shrink; gen 4–5 cases have a Find-My speaker [V]. Pro 2 USB-C case: 45.2×60.6×21.7 mm, 50.8 g, speaker + **lanyard loop**, IP54 [V-s Apple spec] | flip-lid magnetic snap ("the millennial's fidget spinner" [V-r]); lid-open pairing | the container is the daily touchpoint. **The loop lives on the case**, which is exactly founder rule 3. |
| **Apple Watch puck** | inductive, magnetic; 0–80 % in 45 min on S7–S9 / Ultra 3 / SE 3 [V] | **Nightstand mode**: on its side while charging it becomes a bedside clock (portrait from watchOS 4.3) [V] | orientation + charging = a new identity, free in firmware |
| **Pixel Watch 1 → 2** | PW1 wireless → PW2 **4 pins in a 3×3 grid + magnets**; 0–80 % 75 → **43 min**, 0–100 % 110 → 75 min; "pins are faster and generate less heat" [V 9to5google]; PW1 heat forced an update that throttled a full charge to ~2 h [V-s] | same white puck, new contacts | for a small sealed device, **pins beat Qi on speed, heat and space** |
| **Oura Ring 4 charging case** | $99, **5 full charges**, case + ring full in 90 min, recycled **anodised aluminium**, splash-resistant, USB-C, **size-specific (4–15)**, launched 7 Jan 2026 [V] | a jewellery box that charges | a charging case sells at ~25 % of the product price. Size-specific cases are accepted → **shape-specific capsules are OK**. |
| **Galaxy Ring case** | ring $399.99, 18–23.5 mAh (10 Jul 2024) [V wiki]; case 361 mAh, USB-C + **Qi** + reverse wireless, full again in 80 min [V androidpolice, V-s]; translucent lid, white LED ring around a button shows charge [V-s] | "glows delicately" when opened; solid hinge, heft in the base [V] | criticised for one generic colour that doesn't match the ring finishes [V] → **the capsule must match SOUL's colourway** |
| **Nothing Ear (1) case** | square, transparent; lid "opens like a compact", strong magnets; 570 mAh; Qi + USB-C [V-s] | the compact-mirror gesture; the internals on show | transparency or frosting on the *capsule*, not the body |
| **Pixel Stand 1 / 2** | 2018: 5 W Qi + 10 W proprietary; turns the phone into a Home-Hub-like smart display. 2021: 23 W [V] | ambient display on the stand | the dock tells the device *where it is* → auto-mode |
| **Pixel Tablet Charging Speaker Dock** | **magnets + pogo pins**, **43.5 mm full-range driver**, 15 W, 402 g, 169×94×70 mm, Porcelain / Hazel [V]; docked = "hub mode" [V-s] | drop on, it becomes a home display | the closest precedent for SOUL's desk dock: pogo carries power **and audio**, and the colours match the device |
| **iOS StandBy** | charging + landscape → clock, widgets, photos; "dimmer and less flashy colors" at night [V] | the bedside clock is a charging state | night dimming pattern for SOUL's eyes |
| **Nintendo Switch dock** | **USB-C male plug** on top; 173×104×54 mm, 327 g; the OLED dock adds LAN [V] | slide in, it goes to the TV; the Joy-Con "click" became the sound logo [V-r] | a plug-dock works for a 400 g slab with side guides; for a 85 g pebble it becomes a lever on the port |
| **Tamagotchi Uni** | USB-C at the base [V-s]; full charge ~90 min, ~72 h use [V official]; $59.99, bands/lanyards $10 [V-s] | a creature with accessory carry | handheld virtual pets already live under the USB-C rule in the EU (see §3) |
| **Playdate Stereo Dock** | dock + Bluetooth speaker + pen holder; **paused**: BT crashes on fast volume changes, poor pairing, costs above projected revenue [V] | "look incredible on our desks" [V] | **no radio in the dock**; send audio over the pins (Pixel Tablet) |
| **Nomad Base One Max** | metal + glass, **755 g**, 15 W MagSafe, $150 [V-s] | "won't slide around when removing a phone" [V-s] | **weight = premium + one-hand undocking** |
| **Grovemade stand** | walnut/maple + steel base + veg-tan leather, 2.9 lb, **$190 plus the $39 charger**, made in Portland [V-s] | a craft object | people pay furniture prices for honest materials |
| **B&O Beosound A1 2nd Gen** | Cecilie Manz; **pearl-blasted aluminium + polymer + waterproof leather strap**, IP67, USB-C (2.75 h at 5 V 3 A), 18 h [V-s] | the strap is the carry; no dock | a strap/leather accessory makes a sealed object premium |
| **Echo Spot** | 2017: hemisphere, 2.5" round screen, "looks like an alarm clock", $129.99, killed 2019 · 2024: 2.83" half-circle, $79.99, no camera [V] | bedside AI clock | the bedside AI-clock slot is real, but Amazon went cheap. **Premium is open.** |
| **Hatch Restore 3** | $170; sunrise/sunset light, sounds, "Big Button", wind-down; $4.99/mo tier [V-s] | light-first wake-up | **sunrise light before sound** |
| **Zafferano Poldina Pro** | cordless lamp on a **contact charging base**; top glows **red while charging, green when full**; ~6 h charge [V-s]; list $175 [V] | lift the lamp off its base and carry it | a contact base is normal in €150+ design goods. State shown as light, not as a %. |
| **Ray-Ban Meta charging case** | Red Dot 2024 (Fabio Verdelli + Meta): "a modern interpretation of the classic Ray-Ban eyewear case"; magnetic fastener, LED, USB-C [V] | the familiar glasses case, now alive | **reuse a known archetype** (egg, cloche, jewellery box) for the capsule |
| Inductive toothbrush | commercial since the 1970s [V] | a wet, sealed object on a post | a sealed device plus a dumb base is a 50-year-old, trusted pattern |
| **iPod 30-pin docks** | 30-pin 2003 → Lightning 2012; Bose SoundDock 2004–2013 [V-s] | a whole speaker-dock industry | **never change the sole**; publish it and keep it for 10 years (the Leica M mount lesson, [V-r icons]) |
| **LOVOT Nest / Moflin bed / Poké Ball** | [V-r creatures] | the creature goes home to sleep | "going to bed" is a creature behaviour, not a charging chore |
| **Pop Mart / Gashapon / perfume flacon** | blind box 59–69 RMB; China capped the price at 200 RMB (2022) and banned sales to under-8s (2023) [V] · gashapon ¥100–500, 3.711 bn sold since 1977; the **name is the sound**: *gasha* (crank) + *pon* (capsule lands) [V] · Chanel No. 5: 1924 faceted redesign because thin glass broke in shipping; octagonal stopper; "an invisible bottle"; Warhol [V] | the container *is* the reveal and the keepsake | the capsule should have **its own sound and its own silhouette**. Blind-box the *capsule colour* at most, **never the personality** (05). |

---

## 2. The grammar of a great dock or capsule (patterns from §1) [E]
1. **The container is a second product.** It sells ($99 Oura case), protects, carries (the loop), and is the ritual.
2. **Pins inside, Qi outside.** The device gets contacts (Pixel Watch 2). The *case* gets Qi + USB-C (AirPods, Galaxy Ring, Nothing).
3. **Docked = a different being.** Switch, Pixel Stand, StandBy, Nightstand, Pixel Tablet hub mode. For SOUL: bedside mode vs desk mode, chosen by *which* dock it sits in (an ID on the AUX pin).
4. **Weight and material are the premium signal** (Nomad 755 g, Grovemade 1.3 kg, Pixel dock 402 g). A light dock also lifts off with the device.
5. **The docking sound is brand** (Switch click, AirPods snap, gashapon's "pon").
6. **State is shown by light, not numbers** (Poldina red→green, Galaxy Ring LED ring, Hatch sunrise).
7. **Match the colourway** (Galaxy Ring criticism; Pixel dock Porcelain/Hazel).
8. **No radio in accessories** (Playdate). **Freeze the interface** (30-pin).
9. **Borrow an archetype** (glasses case, compact mirror, egg, cloche, jewellery box).

---

## 3. Pogo vs Qi vs USB-C for SOUL

| | **Flush contacts on SOUL + spring pins in the dock** | **Qi (BPP 5 W) in SOUL** | **USB-C receptacle in SOUL** |
|---|---|---|---|
| SOUL-side BOM @1k | 5 gold targets $0.15–0.4 + 2 magnets $0.1–0.25 + TVS/reverse FET $0.1–0.2 = **$0.35–0.85** [E/K] | Rx+charger IC (e.g. TI BQ51050B: Qi v1.2, 1.5 A, 4.5×3.5 mm [V]; price not listed, ~$1–2 [K]) + coil/ferrite $0.5–1 + passives = **$1.7–3.2**, plus WPC logo certification [K] | receptacle $0.1–0.3, sealed IPX7 type $0.4–1.2 [K] + CC resistors/ESD $0.05 |
| Dock-side BOM | 3–5 spring pins $0.3–1.0; a ready 2-pin magnetic module is $2.1–2.2 @5–10k (350 g force, 20k cycles) [V-s] | Tx module $2–4 [K] | a USB-C male in a cradle $0.5–1.5 [K] |
| Efficiency / heat | resistive only, ~95 %+ [K]; cool | Pixel 4 study: wireless used **+39 % energy**, misaligned **+80 %** [V]; Pixel Watch 1 heat throttling [V-s] | ~95 %+ [K] |
| 1000 mAh charge time | 0.5C (500 mA) ≈ 2–2.5 h; 1C ≈ 0–80 % in ~50 min (AXP2101 up to ~1 A [K]) [E] | 5 W at ~50–65 % → ~2–3 h, warm [E] | same as pins |
| Waterproofing | easy: nothing moves on SOUL, targets insert-moulded/glued; IP67 is realistic [E] | perfect (no openings) | a hole; sealed receptacles reach IPX7, but lint and corrosion get into the port [K] |
| Alignment | shape + magnets self-centre; polarity keying fixes the 180° ambiguity [E] | coils ≤ ~5 mm apart typical; > 3 cm misalignment "severely lowers" transfer [V]; Qi2 uses a magnet ring [V] | must be aimed; a knock levers the port [E] |
| Geometry on SOUL | fits the 24–28 × 14–18 mm base land | **doesn't fit the base**; only the domed back (breaks rule 2; a dome rocks on a pad); a metal or zirconia back changes the coupling [E] | fits the base, but the standing object then sits on its plug |
| Corrosion / reliability | sweat + DC ≥ ~100 mV corrodes plated contacts in seconds [V-s patent] → **the dock energises VBUS only after detecting SOUL**; hard gold 0.75–1.25 µm over Ni [V-s jiatel]; target ≥ 10k cycles [V cfe]; **magnet force must exceed the summed spring force** [V cfe] | none | port wear, lint [K] |
| EU 2022/2380 | **not compliant if** SOUL is classified in a listed category (see below) | **exempt** (wireless-only) [V Q15] | compliant |
| Look | invisible when standing (v4 already draws 2 gold contacts) | invisible | a port = "gadget" (08 rule 4) |

**EU common-charger box** [V: EU guidance C/2024/2997]. Listed categories since 28 Dec 2024: phones, tablets, cameras, headphones, headsets, handheld videogame consoles, **portable speakers**, e-readers, keyboards, mice, navigators, earbuds; laptops since 28 Apr 2026. The rules apply to devices that are rechargeable *and* "can be recharged via wired charging". Battery size is irrelevant (Q7). A charging case or station does **not** exempt you: only earbuds are assessed together with their case (Q3). Proprietary connectors are allowed **only in addition to** USB-C, and proprietary + adapter is **not** allowed (Q20, Q22). Category = **primary intended use** (Q11). Smartwatches, fitness trackers and smart glasses are only candidates for future inclusion [V EC page].
→ SOUL (primary use: AI companion / voice assistant / notes) is most likely out of scope, but the speaker and the virtual-pet side make "portable speaker" or "handheld game" arguable [E].
**Action:** write the intended use into the DoC and the manual; ask the Romanian RED market-surveillance authority (ANCOM [K]) for a written view before tooling; and **tool a hidden, sealed USB-C receptacle in the centre of the sole** (invisible when standing; also the dev/recovery port). If the answer is "out of scope", the hole is filled with a blind insert in the same tool. Cost: +$0.4–1.2 [E].

**The SOUL SOLE v1 spec (freeze it; publish it for third-party docks)** [E]
- **5 flush targets**, 3.0 mm pitch, domed Ø1.6, hard gold: **VBUS · GND · USB D+ · USB D− · AUX**. AUX carries the dock ID resistor, the dock-light PWM and the line-out to a speaker dock. The ESP32-S3 has native USB, so D+/D− make any dock a USB port (flashing, recovery, Claude-buddy tether) without a hole in SOUL.
- **2 N48–N52 magnets Ø6×2**, opposite polarities, 16 mm apart: seated backwards, SOUL is *repelled*, so "it refuses to sit with its back to you". SOUL's IMU has no magnetometer (QMI8658 = 6-axis accel + gyro [K]), so the magnets can't upset it.
- Springs **only in the dock** (SOUL has no moving parts). Each dock populates only the pins it needs (CUIB: VBUS/GND/AUX = 3 springs).
- **Force balance** (PEBBLE ~85 g ≈ 0.83 N): springs 3 × 0.3–0.4 N ≈ 1.0–1.2 N up; magnets 2.0–2.5 N down + weight → seated net ≈ 1.8–2.1 N. Lift-out force ≈ 1.6–2.2 N, so the dock must weigh **≥ 300 g (2.9 N)** or it comes up with SOUL (the Nomad lesson). Stronger magnets are *worse*.
- **Taps**: r-creatures R8 shows a free-standing SOUL tips under a 1 N tap. So the dock gets a **backrest at 8° (bedside) to 12–15° (desk)** that takes the tap and the 2.5–3.5 N press-the-eye (07). **The dock is where SOUL becomes touchable hands-free.**
- Dock energises VBUS only when its Hall sensor sees SOUL's magnets **and** the AUX ID reads right. Otherwise the pins are dead (corrosion, coins, keys).

---

## 4. What the dock does beyond charging

| Function | How | Extra BOM @1k [E] | Value |
|---|---|---|---|
| **Pedestal + viewing angle** | backrest 8–15°; eyes at 47–52 % height (r-creatures R5); seated gaze is 30–40° up (R8) → desk docks lift SOUL +30–40 mm | $0 (geometry) | ★★★★★ makes touch possible |
| **Night light** | 6–12 LEDs at 2200 K under a frosted lip wash the *table and SOUL's back*, never its face (rule 1); ≤ 5 lm at night; "candle" fade | $0.5–1.4 | ★★★★ |
| **Sleep + sunrise ritual** | §5; light first, sound second (Hatch) | firmware | ★★★★★ daily reason |
| **Physical privacy state** | capsule lid or cloche closed → Hall in SOUL cuts the mic LDO in hardware: "when it sleeps it cannot hear" (07 made physical) | $0.1–0.3 | ★★★★ trust |
| **Auto-mode by dock ID** | the AUX resistor says bedside, desk or travel → bedside = sleepy clock, desk = Claude-approvals buddy (Pixel Stand / StandBy pattern) | $0.01 | ★★★ |
| **USB tether** | the dock's USB-C → laptop; SOUL enumerates over D+/D−, so the Claude Desktop buddy works without BLE pairing [V-05 buddy API] | $0–0.3 | ★★★ beachhead users |
| **Voice horn (passive)** | a channel in the dock picks up the side speaker and turns it forward. Measured passive boosters: **+1 dB @250 Hz, +3 dB @1 kHz, −5 dB @5 kHz**, "cardboard-like" [V tnt]; phone-specific horns claim +6–13 dB [V-s] → +2–4 dB in the voice band, dull highs [E] | $0 | ★★ only for alarm loudness |
| **Active speaker** | 40–45 mm driver + passive radiator, 3 W class-D fed by AUX line-out (Pixel dock 43.5 mm [V]); **no Bluetooth** (Playdate [V]) | $2.5–4.5 | ★★★ music/voice at the desk |
| **Presence wake** | a hand approaches → eyes open (B&O [V-r icons]); reuses SOUL's proximity sensor | $0–0.5 | ★★★★ the "alive" moment |
| **Travel battery** | the capsule carries 1200 mAh ≈ 1 full SOUL charge after losses | $3–5 | ★★★ |
| **Brand stage** | the brand mark goes on the dock/capsule, never on SOUL (r-creatures R10); the hero shot is "SOUL at home" | $0 | ★★★★ |
Skip: Qi pad on top for the phone (commodity, heat, adds €10 and says "accessory"), clock digits on the dock, any screen or app on the dock.

---

## 5. "SOUL goes to bed" — the scripted ritual [E; timings to tune on hardware]
1. **Seat** (t = 0): shape and magnets pull SOUL the last 3 mm → a damped felt/silicone **"thock"** (r-icons). 150 ms later a two-note low chime from the side speaker. The eyes glance down ("checking the bed"), then up at you, then one slow blink.
2. **Mode** (t + 1.5 s): outside the bedtime window → desk mode (eyes at 60 %, glance card). Inside it → a yawn (eye squash). The dock light rises to 2200 K at 8 %, and the eyelids close over 4 s. The AMOLED goes black (≈ 0 mA for black pixels [K]).
3. **Candle** (t + 60–90 s): the dock light fades out like a candle, or holds a 1–3 % amber night light (user setting). Charging is shown only as a slow 6 s "breath" of the dock light while filling, steady when full (Poldina logic); no % unless asked.
4. **Night**: touch or lift → the eyes half-open and show the time in dim amber for 2 s (StandBy night-dim [V]), then close. No static clock all night (AMOLED burn-in [K]). The mic is gated in sleep unless a wake-phrase feature is explicitly on (off by default, 06).
5. **Sunrise** (alarm − 20 min): the dock light ramps 0 → 100 % warm white (Hatch). At the alarm time the eyes open slowly, and a soft sound follows only if needed.
6. **Lift = awake**: picking SOUL out of the dock (dock-detect + IMU) stops the alarm and shows the **Azi** card. You have to physically take it in your hand to start the day.
7. **Travel variant**: closing the capsule lid = sleep + mic off. Opening it = its eyes open and look up at you (the unboxing "birth" moment, r-icons, repeated daily).

---

## 6. Four dock / capsule concepts (PEBBLE dims; CUIB fits all shapes via the sole)

| | **1 · CUIB** ("nest", in every box) | **2 · CAPSULĂ** (travel egg, the founder's capsule) | **3 · CLOPOT** (glass cloche lantern) | **4 · ALTAR** (sound + sunrise plinth) |
|---|---|---|---|---|
| Archetype | egg cup / river-stone pedestal | egg, compact mirror, Poké Ball, AirPods case | museum bell jar, lantern, reliquary (07) | icon shelf, radio, Pixel Tablet dock |
| Form | Ø80 × 24 mm stone with a sole socket 30×20×5 mm and a backrest rising 28 mm behind SOUL; **300–350 g** | vertical egg clamshell **~76 × 94 × 32 mm, 120–150 g**, rear hinge, magnetic lid; **loop at the hinge** (rule 3) | Ø96 × 22 mm base + borosilicate dome **Ø86 × 118 mm** with an acid-etched crown; 450–600 g total | low plinth **120 × 70 × 42 mm, 450–550 g**; SOUL raised +35 mm at 12°; driver fires up/back |
| Material | slip-cast **porcelain, pearl glaze** (matches Pearl) or matte bisque; cork/felt sole; Onyx = black glaze | **lid: frosted translucent PC** (the sleeping eyes glow through: "a soul in the egg"); base: pearl PC, or **anodised Al** (Oura precedent [V]) on Founders | glass dome + turned **oak/walnut** or porcelain base | bead-blasted Al extrusion or zinc die-cast, perforated back, felt top |
| Electronics | USB-C in, 3 spring pins, Hall, load switch, ESD, LED wash + PMMA ring | **1200 mAh** cell, boost/charger SoC (IP5306-class [K]), 5 pins, USB-C, Hall lid-detect, 3-dot charge light *inside the rim*; option **Qi Rx** (pins inside, Qi outside) | CUIB guts + a 12-LED up-light that fills the frosted crown; ring magnet in the dome rim → lift = wake | 5 pins (USB + AUX audio), 3 W class-D, 45 mm driver + passive radiator, USB-C upstream to the laptop, warm LED bar casting a **halo on the wall behind SOUL** |
| Beyond charging | pedestal/tappable, night light, bedside ID, voice-horn channel toward the side speaker | carry + protect + 1 recharge + lid = sleep/mic-off; ships SOUL (packaging-as-product) | the ritual as theatre: dome on = asleep and deaf, dome lifted = "unveiling" → eyes open; lantern night light | desk buddy (USB tether, Claude approvals), music/voice, sunrise alarm, "shrine" light |
| Signature sound | "thock" + 2-note chime | lid "clack" (tuned magnet + damper), the gashapon lesson | glass "ting" of the dome seating on felt | "thock" + a warmer chime through the 45 mm driver |
| **BOM @1k** [E] | porcelain $3–6 · PCB/pins/Hall/switch/ESD/USB-C $1.4–2.4 · LEDs + light guide $0.5–0.9 · magnets + steel ballast $0.4–0.7 · liner/foot $0.2–0.4 · cable $0.6–1 · assembly/test incl. ~10–15 % porcelain rejects $0.9–1.6 → **$7–13** | PC shells $1.2–2.5 · cell $1.5–2.5 · SoC/PCB $0.8–1.5 · pins/USB-C/Hall/LEDs $0.9–1.6 · magnets/hinge $0.5–0.9 · strap + ring $1–3 · assembly $1.5–2.5 → **PC $8–15**; Al base **$14–24**; +Qi **+$2–3.5** | dome $3–7 (hand-blown $6–12) · base wood/porcelain $4–8 · CUIB electronics $2.2–3.8 · brighter LEDs $0.8–1.4 · dome magnet + Hall $0.3–0.5 · glass-safe pack $1–2 · assembly $1.5–2.5 → **$13–25** | enclosure $5–10 · driver + PR $2–3.5 · amp/PCB/pins/USB/ESD $2.5–4 · LED bar + diffuser $1–1.8 · ballast $0.5–1 · grille/felt $0.4–0.8 · cable $0.6–1 · assembly $2–3 → **$14–25** |
| **BOM @10k** [E] | **$4.5–8** | PC **$6–10**, Al **$9–15** | **$9–16** | **$9–15** |
| Tooling [E] | plaster moulds $1–3k + PCB | PC tools **$12–25k per shape** (start with PEBBLE); UN38.3 for the cell $1.5–3k [K] | dome mould $3–8k (or hand-blown, no tool) + base fixtures | extrusion die $2–5k + CNC fixtures, or die-cast $15–30k |
| Retail | in the box; spare €35–45 | **€49 PC / €69 Al**; Founders ship *inside* it | **€99–119**, or included in the Founders Edition (€299–349, 08) | **€79–99** (adapter not included, EU unbundling [V]) |
| Risks | porcelain chips (glaze the underside, felt sole); must hit ≥ 300 g | shape-specific (4 tools eventually); 1 recharge only; a battery product to certify and ship | glass breakage in transit, dust, "Beauty-and-the-Beast" cliché; sound through glass is muffled (≈ −10 dB [E]) → light-first alarm | scope creep (the Playdate trap); keep it wired-only and ship it in year 2 |

**Why each earns its place** [E]: **CUIB** gives every buyer the ritual for ~$10, and it is the one-dock-for-all-shapes proof of the sole standard. **CAPSULĂ** is the founder's capsule, the legal home of the loop/strap, and the unboxing object (the capsule replaces a moulded insert, so packaging drops from $3–6 to a ~$1.5–2.5 paper sleeve and recovers ~$2–3). **CLOPOT** is the "want it on sight" photo: an heirloom under glass, and the most premium read per euro, because the dome costs less than a titanium bezel. **ALTAR** turns SOUL into a desk companion for the Claude-Code crowd and earns accessory margin later.

---

## 7. Recommendation
- **Launch set:** SOUL + **CUIB** (pearl porcelain) in every box. **CAPSULĂ-PEBBLE** is the launch accessory, and the Founders Edition #001–#1000 ships *inside* an aluminium CAPSULĂ plus a **CLOPOT**. ALTAR comes in year 2, after usage data shows desk demand.
- **Engineering:** freeze SOLE v1 (5 targets + 2 keyed magnets + hidden USB-C in the tool) at EVT. It is identical on PEBBLE, CLOUD, DROP and AMULET. Build a SOLE test fixture (10k seat cycles, salt-fog on the targets, sweat-simulant + bias test).
- **Firmware:** dock-ID modes, the §5 ritual, lift-to-stop alarm, hardware mic gate on lid/dome, no clock without a touch.
- **Brand:** the mark lives on the dock/capsule (debossed underside or back); the capsule matches SOUL's colourway (the Galaxy Ring lesson); the "thock" is the sound logo.
- **Don'ts:** Qi in SOUL; Bluetooth in any dock; a phone-charging pad on the dock; blind-boxing personalities; lights on SOUL's face; a light dock (< 300 g).

## 8. Open questions / next steps
1. Written view from ANCOM / a notified body on SOUL's Annex Ia category (before the DVT tool is cut).
2. Print CUIB in 3 backrest angles (6°, 10°, 14°) and 3 weights (200, 300, 400 g); measure lift-out force and tap stability with the real magnets and pins.
3. Get porcelain quotes: Romanian manufacturers (Alba Iulia region [K, unverified]) vs Jingdezhen/Chaozhou slip-casting; ask for underside glaze and ±0.3 mm socket tolerance after firing (≈ 13–15 % shrink [K]).
4. Borosilicate dome quotes (pressed vs hand-blown) plus a drop test in packaging.
5. Measure the dock voice-horn gain on the v4 side speaker; drop it if < 3 dB at 1–3 kHz.
6. Verify the [K] prices (Qi Rx IC, sealed USB-C, spring pins, IP5306) with 2–3 LCSC/Digi-Key quotes.

## 9. Sources (fetched 2026-09-24 unless marked)
- [V] https://en.wikipedia.org/wiki/AirPods · [V-s] https://support.apple.com/en-us/111834 (Pro 2 USB-C case speaker, loop, IP54, 50.8 g)
- [V] https://en.wikipedia.org/wiki/Apple_Watch · [V] https://en.wikipedia.org/wiki/Pixel_Watch · [V] https://en.wikipedia.org/wiki/Pixel_Watch_2 · [V] https://9to5google.com/2023/10/04/pixel-watch-2-charging-cable/ · [V-s] androidpolice.com / chromeunboxed.com PW2 articles (PW1 throttling)
- [V] https://ouraring.com/blog/oura-ring-4-charging-case/ · [V-s] androidauthority.com, techcrunch.com (2025-10-01) Oura case coverage
- [V] https://en.wikipedia.org/wiki/Galaxy_Ring · [V] https://www.androidpolice.com/samsung-galaxy-ring-charging-case/ · [V-s] hothardware.com Galaxy Ring review (361 mAh, LEDs)
- [V-s] pocket-lint.com / counterpointresearch.com Nothing Ear (1) case (570 mAh, Qi, magnetic lid)
- [V] https://en.wikipedia.org/wiki/Pixel_Stand · [V] https://support.google.com/googlepixeltablet/answer/14718509 · [V-s] https://store.google.com/product/pixel_tablet_charging_speaker_dock (hub mode) · [V] https://en.wikipedia.org/wiki/Pixel_Tablet
- [V] https://en.wikipedia.org/wiki/IOS_17 (StandBy) · [V] https://en.wikipedia.org/wiki/Nintendo_Switch · [V] https://en.wikipedia.org/wiki/Amazon_Echo_Spot
- [V] https://tamagotchi-official.com/us/series/uni/faq/ · [V-s] t3.com, gamespot.com Tamagotchi Uni (USB-C, $59.99, bands)
- [V] https://play.date/stereo-dock/ (paused)
- [V-s] howtogeek.com / macrumors.com Nomad Base One Max (755 g, $150) · [V-s] 9to5mac.com 2021-01-11 Grovemade MagSafe Stand ($190, 2.9 lb)
- [V-s] ceciliemanz.com/content/beosound-a1, bang-olufsen-cee.com A1 2nd Gen (materials, IP67, USB-C, 18 h)
- [V-s] howtogeek.com / tomsguide.com Hatch Restore 3 ($170, sunrise, sub) · [V] https://zafferanoamerica.com/products/poldina-pro ($175) · [V-s] Poldina contact base, red/green glow, ~6 h
- [V] https://www.red-dot.org/project/ray-ban-meta-charging-case-70858 · [V-s] meta.com Ray-Ban Meta case (48 h Gen 2)
- [V] https://en.wikipedia.org/wiki/Pop_Mart · [V] https://en.wikipedia.org/wiki/Gashapon · [V] https://en.wikipedia.org/wiki/Chanel_No._5
- [V] https://en.wikipedia.org/wiki/Qi_(standard) · [V] https://en.wikipedia.org/wiki/Inductive_charging · [V] https://www.ti.com/product/BQ51050B
- [V] https://cfeconn.com/pogo-pin-connectors-tws-earbuds-wearables/ · [V] https://www.jiatelcn.com/tws-pogo-pin-corrosion-solutions/ · [V-s] USPTO 10944271 (electrolytic corrosion at ~100 mV with sweat) · [V-s] alibaba.com 2-pin magnetic pogo ($2.10–2.20, 350 g, 20k cycles)
- [V] https://www.tnt-audio.com/accessories/smartphone_booster_e.html (+1/+3/−5 dB) · [V-s] vat19.com horn stand, USPTO passive-amplifier patents (6–16 dB claims)
- [V] EU guidance on the Common Charger Directive, OJ C/2024/2997: https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:C_202402997 (Q3, Q7, Q11, Q15, Q20, Q22) · [V] https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/radio-equipment-directive-red/one-common-charging-solution-all_en
- [V-s] en.wikipedia.org/wiki/Dock_connector, whathifi.com (30-pin 2003–2012, SoundDock 2004–2013)
- Project: research/05–08, design-max/r-icons.md, design-max/r-creatures.md, renders/v4/README.md, images listed in the brief [V].
- [K], unverified today: Qi Rx/Tx and IP5306 prices, spring-pin forces, AXP2101 max charge current, AMOLED black-pixel current, porcelain shrink and reject rates, UN38.3 cost, ANCOM's role, Alba Iulia porcelain.
