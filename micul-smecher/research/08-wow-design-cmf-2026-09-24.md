# SOUL — "wow" design, CMF and the three render concepts (raw, 2026-09-24)

Tags: **[V]** fetched today (URL in §7) · **[K]** background knowledge, verify before quoting publicly · **[E]** estimate / engineering judgement.
Builds on 05 (launch/brand), 06 (board mechanicals, BOM, battery, reference objects) and 07 (amulet grammar, press-the-eye, halo, crown, caseback). Not repeated here. **Scope change since 07: SOUL is no longer a necklace** — pocket / bag / desk. So the 50 g weight ceiling from 07 goes away; 70–95 g (pocket-watch class) is now allowed, and that opens up metal and ceramic.

---

## 0. Diagnosis: why v1 felt precious and v2 felt cheap [E, from project numbers]
| | v1 coin Ø52 | v2 pebble 68×60 |
|---|---|---|
| Glass Ø48.96 area / plan area | 1883 / 2124 mm² = **~89 % face** | 1883 / 3204 mm² = **~59 % face** |
| Read | "a jewel that is all eye" | "a plastic housing with a screen set into it" |
| Surface | frosted white = diffuses light, looks like glass/porcelain | uniform matte grey/white = looks like printer plastic, no highlight, no contrast material |
| Section | coin: crisp edge that catches a highlight | soft dome, no edge, so no highlight line and no sense of precision |
Rule that falls out of this: **keep face/plan ≥ 80 %, and put a crisp, light-catching edge around the eye.** Making the object bigger is fine only if the *face* grows with it (see §4, "infinity glass").

---

## 1. What reads as premium/futuristic vs cheap

### 1.1 Perception rules (CMF)
| Lever | Premium | Cheap | Numbers / refs |
|---|---|---|---|
| **Density** (mass ÷ envelope volume) | 1.7–2.5 g/cm³: the object feels "full" | < 1.2 g/cm³ feels hollow; it rattles or rings when tapped | iPhone 2007: 135 g / (115×61×11.6 = 81 cm³) ≈ **1.66** [V dims from 07, E calc]; AirTag 11 g / 6.4 cm³ ≈ **1.7** [E]; Watch Ultra ~61 g / ~31 cm³ ≈ **2.0** [K/E]; pure ABS/PC shell with air inside ≈ **0.8–1.1** [E]. Target SOUL ≥ **2.0** |
| **Stiffness / sound** | no flex under squeeze, dull "tock" when tapped | creaks, oil-can flex, hollow "tick" | ribs + potting/foam, metal frame; a creak is heard as cheap before it is seen [K] |
| **Gaps & flushness** | ≤ 0.10–0.15 mm, even all round, flush ±0.05 | 0.3–0.5 mm uneven, steps between parts | watch/phone industry norm [K]; a unibody or bayonet back (07) removes most seams |
| **Edges & highlights** | one deliberate chamfer or radius that draws a continuous highlight line; G2 (curvature-continuous) surfaces so reflections flow without breaking | blobby G1 blends: the reflection kinks where surfaces meet; soft "melted" edges | iPhone 5 diamond-cut chamfer (2012) [K]; Rams / Ive: "a precise edge = care" [K] |
| **Glass↔metal transition** | glass edge 2.5D-curved and flush with a polished lip, or the metal lip stands 0.1–0.3 mm proud to protect a flat crystal (Watch Ultra) | glass sitting in a plastic pocket with a visible black foam/glue line | Ultra: flat sapphire crystal behind a raised titanium rim [V/K] |
| **Contrast pairing** | one hero material + one precious contrast (Ti + zirconia back; white + black glass) | one material everywhere, one colour | Watch Ultra 2 Black: "custom blasting" + DLC PVD over grade-5 Ti, matching **dark zirconia back** [V apple newsroom] |
| **Light as a material** | diffuse, no visible LED dots, no hotspots; slow eased fades; one colour at a time; the light seems to come from *inside* the material | LED dots visible through a thin diffuser, flickering PWM, rainbow RGB, hard on/off | Apple's "breathing" sleep LED, Nothing Glyph (07) [K/V]; Vision Pro lesson: eyes shown behind reflective glass came out "dim, low-resolution" [V wiki] → an emissive face needs **AR-coated glass and true black** |
| **Surface finish** | bead-blast (hides scratches and fingerprints), fine brushing, selective mirror polish on *one* edge, PVD/DLC, polished zirconia | generic mould texture (VDI/MT spark), glossy-plastic paint that chips, soft-touch paint (goes sticky in 2–4 years, 06) | |
| **Honesty / micro-detail** | laser-engraved type 0.3–0.5 mm cap height, a knurl or detent you can feel, seals that don't show, no visible fasteners | stickers, screws, round-hole speaker grilles, embossed logos, visible USB flap | Rams "as little design as possible" (06); TE: exposed but *designed* internals [V 06] |
| **Brand colour discipline** | ≤ 2 materials + 1 accent (Ultra's orange Action button; TE; Nothing red dot) | many colours, gradients | Watch Ultra orange Action button [V wiki] |

### 1.2 Finish menu (what each costs you) [K/E]
- **Bead/glass-bead blast** (Ti, Al, steel): satin, even, hides scratches and fingerprints; ~$0.3–1 per part. The best "tech-premium" default.
- **Anodising** (aluminium only): colour + hardness in a 10–25 µm oxide; type II decorative, type III hard. Titanium "anodising" only gives interference colours (blue/gold/purple), which read as jewellery or bike parts, not premium tech.
- **PVD / DLC**: 1–3 µm, 1500–2500 HV. Black / graphite / bronze on Ti or steel. Scratch-resistant, but when it chips at an edge the bright metal shows → chamfer the edges before coating. ~$1.5–4 per part at 1k.
- **Mirror polish**: the most expensive-looking finish and the fastest to scratch and fingerprint. Use it only on one line (a chamfer, the bezel top).
- **Polished zirconia**: glassy, cold, heavy, ~1200–1300 HV, practically scratch-proof in a pocket; shows fingerprints; white stays white (no UV yellowing, unlike PC/ABS: the Friend complaint in 07).
- **Frosted glass / acid-etched glass**: the "v1 DNA" look done right. Real glass, cool to the touch, doesn't yellow.
- **NCVM / "ceramic-look" UV lacquer on PC**: a cheap imitation of the finishes above; fine at €149, detected by weight and temperature (PC feels warm and light).

### 1.3 Anatomy of "cheap plastic" (and why) [K]
Parting line and flash on the silhouette (two-plate tool, worn shut-off); **sink marks** opposite bosses/ribs (rib > ~50–60 % of the wall thickness) → wavy reflections; knit/weld lines and flow marks near gates; ejector-pin circles; gate vestiges; low-saturation matte grey PC/ABS ("printer beige/grey"); a single generic texture; thin 1.2–1.5 mm walls → flex and a hollow sound; fasteners visible; uneven light pipes showing LED dots; thick black borders around the display. Most of these come from cost-driven tooling, not from the material; a well-tooled PC part (Nothing Ear case, iPhone 5c) can read premium. v2's problem was mostly *geometry and material monotony* (§0), not the plastic itself.

### 1.4 Reference moves, one line each
- **Apple / Ive**: unibody, a highlight chamfer, the face is the product, obsessive gap control; Watch Ultra = raised Ti lip + orange accent + zirconia back [V/K]. **Vision Pro**: laminated curved glass + aluminium, 600–650 g; the EyeSight "eyes on the outside" was criticised as dim behind reflective glass [V].
- **Nothing**: transparency with designed internal cover plates; the internals are *styled*, never raw PCB [K]. **Teenage Engineering**: flat colour, graphic discipline, exposed but designed mechanics [V 06].
- **B&O**: bead-blasted and diamond-cut aluminium, oak, woven fabric; A1 = aluminium dome + polymer base = an antenna window by design [K]. **Braun/Rams**: grey/white + one colour accent, precise radii [V 06].
- **Leica**: knurled dials, vulcanite, the red dot, audible clicks = the "instrument" feeling [K].
- **Oura**: titanium + PVD, epoxy inner (RF/sensors), 4–6 g [V wiki weight; K materials]. **Pixel Watch**: domed glass flowing into polished steel, no bezel line [K].
- **Humane / Rabbit / Friend** (06/07): Humane = Al + glass but thermal failure; r1 = TE orange plastic, loved object that failed on product; Friend = white plastic that yellows and reads as a medical-alert button.

---

## 2. The three concepts — engineering reality

Common base: the Waveshare 1.75 stack (06/07), 650–1000 mAh cell, ~45 g of internals (module ~20, cell 13–19, speaker+LRA 4, misc 5) [E].

| | **A · LENS** (bead-blasted Ti, knurled rotating bezel, halo) | **B · ORB** (clear/frosted optical glass, glowing inside) | **C · EVE** (glossy white zirconia egg, black glass visor, stands up) |
|---|---|---|---|
| Envelope [E] | Ø58–60 × 15–17 mm (≈ 40–45 cm³) | Ø60 × 22–24 mm dome (≈ 55 cm³) | ~62 W × 72 H × 48 D mm egg (≈ 110 cm³) |
| Process | 5-axis CNC Ti-6Al-4V mid-frame + bezel ring (knurl machined), bead blast, optional DLC; zirconia or glass caseback; bezel with 36–60 detents (spring + ball) and a magnet ring read by a hall encoder (no shaft through the case = sealed) | (i) moulded borosilicate/aluminosilicate glass dome + polish, or (ii) diamond-polished-tool injection PMMA/optical PC + hard coat; inner frosted diffuser; designed "visible" internals (custom PCB art, black mask, light guide, deco plates) | Zirconia CIM (3Y-TZP) front + back shells, sinter (~20 % linear shrink [K]), lap/polish; hot-bent 3D black glass visor with AR; weighted flat base |
| Housing cost @1k [E] | **$55–100** (Ti CNC set $35–70, bezel mechanism $5–10, blast/DLC $3–8, glass $4–8, back $4–10) | **$20–45** (glass/PMMA $8–20, diffuser + deco + light guide $6–12, frame $3–6, hard coat) | **$40–80** (zirconia 2 parts $25–50 at CIM yields of 70–85 %, polish $3–8, visor $6–15) + tooling $40–120k |
| Housing cost @10k [E] | **$30–55** (or Ti MIM at $8–15 per part after $15–40k tooling, weaker finish; aluminium CNC variant $8–14) | **$10–22** | **$20–40** |
| Tooling [E] | fixtures only for CNC ($3–10k) → cheapest to start, most expensive per unit | glass mould $5–15k or high-polish steel injection mould $15–40k | highest: CIM moulds $20–60k per part + visor tool $5–10k |
| RF (ESP32-S3 2.4 GHz) | **Problem.** Ti (resistivity 420 nΩ·m [V]) still shields. Strategy: a **dielectric ring**: the frosted halo ring (PC/PMMA/glass, ≥ 1.0–1.5 mm) under the bezel = a 360° slot; put an LDS or FPC antenna behind it + a **zirconia/glass caseback** (the Watch approach). Alternative: the Ti ring *as* the antenna with an arc slot (the IEEE all-metal smartwatch design: ~97 mm × 1 mm arc slot, 2.4 GHz [V-snippet]). Budget a −3 to −6 dB penalty vs plastic, plus an RF tuning spin [E] | **Perfect** (glass/PMMA transparent). Watch out for conductive NCVM/metallised deco and the AMOLED ground | **Good.** Zirconia is a dielectric [V] but high-κ (εr ~25–30 [K]) → detunes an antenna that touches it; keep 2–3 mm clearance or tune on the shell |
| Thermal (~0.5–1 W peak during Wi-Fi voice) [E] | Ti 21.9 W/m·K [V] spreads the heat; warm but even; OK for ≤ 1 W with ≤ 43 °C at the skin [K] | glass ~1, PMMA ~0.2 W/m·K: hot spot behind the module; fine at the duty cycle, don't seal the cell against the ESP | zirconia ~2–3 W/m·K [K], low (thermal-barrier ceramic [V]); large surface → fine |
| Weight [E] | Ti ~42 g shell (Ti-6Al-4V 4.43 g/cm³) + glass back + 45 g internals = **80–95 g** → ρ ≈ **2.0–2.3** ✔ | glass shell ~50 g (2.2–2.5 g/cm³) + 45 = **~95 g**; PMMA version ~60 g → ρ 1.1 (feels light) | 1.5 mm zirconia (5.68–6.05 g/cm³ [V]) ≈ 80 g + 45 + ballast = **~130–150 g**. Heavy for a pocket, ideal for a desk |
| Drop (1 m onto concrete) | **Best.** Ti dents rather than breaks; the cover glass is the weak point → raised bezel protects it | **Worst.** Glass body = shatter risk, even chemically strengthened; PMMA cracks; PC survives but scratches and yellows | **Medium.** 3Y-TZP is transformation-toughened ([V]; ~5–10 MPa√m [K] vs glass ~0.7), but point impacts on edges chip it; an upright egg knocked off a desk lands on its visor |
| Scratch | Ti grade 5 is soft-ish; bead-blast hides it; DLC helps | glass OK (Mohs ~5.5–7), pocket sand (quartz 7) scratches it; PMMA scratches fast | zirconia ~Mohs 8–8.5: near scratch-proof; black glass visor needs AR + oleophobic coating |
| Wow / risk | "instrument" read: Leica × Watch Ultra × click-wheel. Risk: reads as "a watch without a strap" if the face is too small | the most "futuristic" in renders. Risk: in real life, raw ESP32 internals + PC yellowing = Friend 2.0; the most expensive to make *look* good inside | the most "character" (EVE). Risk: too close to Pixar's EVE (Disney trade-dress/PR risk); 110 cm³ does not go in a pocket; glossy = fingerprints; CIM tooling before product-market fit |
| Who did similar | Apple Watch Ultra (Ti + zirconia back + raised lip) [V]; Omega "Dark Side of the Moon" (full ZrO₂ case, 2015) [V]; Leica/dive bezels [K] | Nothing Ear (1)/Phone (1) transparency + Glyph (07); B&O Beosound Level/A1 dielectric windows [K]; Jibo's single glowing orb eye [V] | EVE (Ive consulted) [V]; Echo Spot 2017 hemisphere + 2.5" round screen $129.99, 2024 redesign 2.83" $79.99 [V]; Emo 94×66×117 mm, 248 g, $279 [V]; Vector (black OLED face, Anki bankrupt 2019, DDL relaunch 2021) [V]; Jibo (Breazeal; shut down, assets to NTT 2020) [V] |

**Takeaways** [E]: A is the only one that is premium *and* pocketable *and* survives drops; its costs are RF and money. B is the cheapest housing, but the most expensive to make look expensive, and the most fragile. C has the strongest character, but it is a desk object with a Disney shadow over it, and it has the highest up-front tooling.

---

## 3. "Futuristic with a soul": icons and the moves they use
| Icon | Facts | The move |
|---|---|---|
| **HAL 9000** | one lens with a red and yellow dot; prop ≈ 3" lens = Fisheye Nikkor 8 mm f/8 [V] | a *real precision optical part* as the face; one eye = presence. (Its downside: cold surveillance. We add blinks and warmth.) |
| **EVE** (WALL-E) | glossy white egg, black visor, blue LED eyes; Ive consulted; eyes deliberately *not* over-expressive, so emotion comes from pose [V] | **eyes floating in deep black glass** + restraint + body pose |
| **BB-8** | sphere + dome, one black lens; asymmetric panels so you can read its motion; Sphero sold 1M+ toys in 2015 [V] | minimal face; personality through *motion and tilt* |
| **Baymax** | Disney 2014, Shigeto Koyama (mecha designer) [V]; face = two dots joined by a line (suzu-bell reference) [K] | the most reduced face possible still reads as caring; soft white volume |
| **TARS** (Interstellar) | brushed-metal monolith slabs, no face; personality through voice ("humor 75 %") and movement [K] | an object can have a soul with *zero* face, if the voice and timing are right |
| **Samantha / Her** (2013) | a small folding device like a vintage cigarette case or compact, warm colours, an earpiece; production design by K.K. Barrett [K] | **anti-gadget**: it looks like a personal keepsake, not tech. Softness through colour and fold |
| **WALL-E** | binocular eyes [K] | eyes borrowed from a real instrument |
| **Vision Pro EyeSight** | eyes rendered behind reflective glass came out dim and uncanny [V] | warning: **eyes must be emissive, high-contrast, and simple**, not photoreal |
| **Emo / Vector** | 1000+ expressions, headphones, skateboard [V]; black OLED face [V] | toy side: accessories and cartoon props read as a *kid's gadget*. Avoid them |

**Design moves: face without toy** [E, synthesised]
1. **Two eyes, no mouth, no brows, no cheeks.** Emotion comes from lids, pupils, timing and tilt (EVE, Baymax, Vector).
2. **The eyes float in true black**: an AMOLED behind black glass with ink matched to the panel's black, so you cannot see where the screen ends (EVE's visor, and Watch's hidden borders [K]).
3. **Precious when asleep**: switched off, it must still be a beautiful lens or stone (HAL's Nikkor). No face shows while it charges unless you look at it.
4. **Motion restraint**: blinks every 3–8 s, saccades, slow-in/slow-out; an idle state 90 % still. Hyperactive = toy.
5. **Gaze is the interaction**: eyes turn to the user (IMU tilt → pupils shift), and look *up* when picked up; body pose on the desk dock (a tilt servo is optional later).
6. **One accent colour with meaning** (HAL red, EVE blue, the Claude orange for approvals); never rainbow.
7. **Adult materials**: metal, glass and ceramic signal a keepsake; decals, rubber ears and accessories signal a toy.
8. **Sound is small**: soft non-verbal chirps before speech (BB-8/R2 class), never a jingle.

---

## 4. Size: is there a bigger round AMOLED for ESP32-S3?
| Board / panel | Shape | Size / res | Tech / driver | Price | Usable round Ø vs 1.75 (Ø43.8) |
|---|---|---|---|---|---|
| Waveshare ESP32-S3-Touch-AMOLED-**1.75** | round | 466×466 | AMOLED CO5300 | $29.99–39.99 [V 06] | **Ø43.8** (baseline) |
| Waveshare ESP32-S3-Touch-AMOLED-**1.8** | **rectangular** | 368×448, 350 nits | AMOLED CO5300, CST820 | $27.99–29.99 [V] | inscribed circle ≈ Ø37 [E] ✗ |
| Waveshare ESP32-S3-Touch-AMOLED-**2.06** | rectangular (watch) | 410×502 | AMOLED CO5300 | $29.99–31.99 [V 06] | ≈ Ø33 [E] ✗ |
| Waveshare ESP32-S3-Touch-AMOLED-**2.16** | **square** | 480×480, 600 nits | AMOLED CO5300, CST9220; codec + 2 mics, QMI8658, AXP2101, RTC | $29.99–31.99 [V] | inscribed circle = 2.16"/√2 ≈ **Ø38.8** ✗ (smaller than the 1.75!) |
| Waveshare ESP32-S3-Touch-LCD-**2.1** | round | 480×480 | **IPS LCD** ST7701 (RGB), CST820 | $32.99 [V] | ≈ Ø53 [E] ✔ size / ✗ blacks |
| Waveshare ESP32-S3-Touch-LCD-**2.8C** | round | 480×480 | **IPS LCD** ST7701 | $32.99–39.99 [V] | ≈ Ø71 [E] (desk only) |
| Industry round AMOLED | round | 1.2–1.43 common, **1.75 466×466 the largest found** (VIEWE catalogue) [V search]; 1.96" exists but 410×502 rectangular [V search] | | | round AMOLED > 1.75" is not available off the shelf at maker MOQ [E] |

**Conclusion** [E]: **1.75" is the round-AMOLED ceiling.** The 2.1" round is LCD: its backlight turns "black" into a grey glow. That kills the floating-eyes-in-black-glass effect, which is *the* wow move (§3.2), and draws ~60–100 mA more for the backlight. Don't trade AMOLED for size.
**How to make it feel bigger anyway: an "infinity glass" face.** Use a custom cover glass **Ø52–54** over the 1.75 panel, with a black ink border matched to the AMOLED's black (L* ≈ 0–2) under an AR coating. Because the eyes never touch the edge, the eye reads the whole black glass as screen → perceived face **Ø53 vs 44 (+46 % area)**. Object **Ø60–62**: face/plan ≈ 75–80 %, pocket-watch size (07: 16s/18s pocket watch cases Ø50–55), fits in a jeans pocket, and fills a palm like v1 did but larger. Cost of the custom 2.5D glass: +$2–5 at 1k [E]; it needs a custom FPC bond or a bezel-seat redesign, and in proto it can be a glass overlay on the stock board. **Portable sweet spot: Ø58–62 × 14–17 mm, 75–90 g.** Above Ø65 or 100 g it becomes a desk puck.

---

## 5. Recommendation: **"LENS" body, EVE's black face, ORB's light (hybrid A+)**, plus an EVE-inspired porcelain **dock**
Why: A is the only concept that is premium, pocketable and durable at once. Concept C's *face* idea (black visor, floating eyes) is the soul, and it goes on the front glass. B's *light* idea goes into the halo ring, which also solves A's antenna problem. C's *standing body* becomes the desk dock, so its size and weight cost nothing in the pocket. The frosted-white v1 DNA survives in the halo and the white zirconia back.

| Item | Spec [E unless tagged] |
|---|---|
| Form | Round lens, **Ø60 × 15.5 mm at the rim / 17 mm at the centre** (domed back); silhouette = a circle with a knurled rim. Proto on stock Waveshare: Ø62 × 19–20 |
| Face | **Infinity black glass Ø53**, 2.5D, aluminosilicate (sapphire on Founders), AR + oleophobic; the 1.75" 466×466 AMOLED (Ø43.8 active) floats inside; no logo. The face stays press-to-talk (07 #1) |
| Bezel | Grade-5 Ti, **knurled, rotating**, 36 detents (spring + ball), magnet ring + hall encoder (TMAG5273/AS5600 class) = the round-native scroll (iPod rule, 07); O-ring under the bezel (dive-watch practice). Top chamfer mirror-polished (the one highlight line); the rest bead-blasted. 0.2 mm proud of the glass |
| Halo | 1.2 mm frosted PMMA/glass ring between the bezel and the case, lit from inside by 8–12 side LEDs = the "soul light" (07 #2). **It is also the 360° antenna window** (LDS/FPC antenna behind it) |
| Case / back | Mid-case Ti-6Al-4V bead-blast (Natural) or DLC (Onyx); **white polished zirconia bayonet caseback** (Bone), engraved (07 #4), RF + tactile contrast; 2 pogo targets + a magnet on the back |
| Colourways | **Bone** (natural Ti + white zirconia + white halo), **Onyx** (DLC black Ti + black zirconia + smoke halo). Accent: one Claude-orange dot on the crown-less 12 o'clock mark (Ultra's orange button logic) |
| Weight / density | **~85 g** (range 78–92), ρ ≈ 2.0 g/cm³ |
| Inputs | press-the-eye (dome), touch, rotating bezel, IMU (lift-to-wake, face-down = sleep), capacitive "held" back |
| Carry | pocket (no protrusions except the bezel knurl, ≤ 0.8 mm high); bag via a thin leather/Ti clip sleeve that grips the bezel; optional short lanyard loop in the sleeve. **Not a necklace** |
| Dock "Cuib" | slip-cast **glossy white porcelain** egg-cradle (the EVE body): the lens clicks in magnetically, upright at ~75°, so the eyes look at you from the desk; pogo charging; weighted (~250–350 g). Slip-casting is cheap ($5–12 at 1k, low tooling [E]) and Romanian porcelain is a local story (e.g. Alba Iulia [K]) |
| Battery / display / radio | as in 06/07 (650–1000 mAh; more room at Ø60 → aim for 800–1000); ESP32-S3 Wi-Fi + BLE |
| Housing BOM | Ti version **$60–95 @1k, $35–55 @10k**; **aluminium 7075 bead-blast/anodised version $25–40 @1k, $12–20 @10k** (ρ drops to ~1.6: add a tungsten or steel ballast plate for $1–2) |
| Retail implication (≥ 2.5× landed, 05) | **Founders Titanium, numbered: €299–349** (COGS ~€100–120 @1k). **Standard aluminium + zirconia back: €199–229** (COGS ~€70–85). Porcelain dock included in Founders, €39 otherwise. €149 is only reachable with a PC/"ceramic-look" shell, and that is the look the founder rejected |

**Honest trade-offs**
- **Titanium doubles the housing cost** and forces an RF tuning spin (the halo window must be designed in from day 1; test the ESP32-S3 antenna in a Ti mock-up at EVT). The aluminium variant keeps ~90 % of the look at ~40 % of the cost. Only the tap sound and the "cold then warm" touch tell them apart.
- **Rotating bezel** = +€5–10, +2 mm Ø, a dust/seal path and a snag risk. 07 recommended software rim-scroll instead. I'm reversing that here because the object is now pocket/desk rather than necklace, and because a crisp detented bezel is the cheapest way to get a "Leica-grade" wow in the hand. Keep rim-scroll in software as the fallback if EVT shows grit or snag problems.
- **Losing the all-white v1 coin**: Bone keeps white in the back and the halo, but the front becomes black glass. That is deliberate: white-framed AMOLED looks like a toy smartwatch, black glass makes the eyes float. **Show the founder renders of both.**
- **ORB transparency** is parked, not killed: it can come back as a limited "Glass" edition once the custom PCB is beautiful enough to be seen.
- **EVE egg as the handheld** is rejected (110 cm³, 130–150 g, CIM tooling, Pixar resemblance). As a porcelain dock it keeps its magic for ~€10.
- Everything here is [E] until three looks-like models (Ti, Al + ballast, PC) are weighed and handed to 10 people blind. **Weight and sound will decide more than the renders.**

**5 design rules for SOUL (CMF)**
1. **The face is at least 80 % of the object, and it is black glass.** The eyes float in true black; you should never see where the screen ends.
2. **Density ≥ 2 g/cm³, zero flex, a dull "tock"**: it must feel fuller than it looks.
3. **Two materials plus one light**: metal body, glass/ceramic contrast, one frosted halo. One accent colour, never RGB.
4. **One highlight line, no visible seams**: a single polished chamfer catches the light; gaps ≤ 0.15 mm; no screws, grilles, ports or logos on the front or sides (engrave the back).
5. **Asleep, it is a lens; awake, it is someone**: beautiful switched off (HAL), restrained switched on (EVE): eyes only, slow, looking at you.

---

## 6. Next steps
1. Order a Ti and an Al bezel ring (CNC, Xometry/PCBWay-class, ~$60–150 each proto [E]). Fit them over the stock 1.75 board with a custom Ø53 black overlay glass, then compare with the v1 coin side by side.
2. RF test at EVT: ESP32-S3 RSSI/throughput in Ti vs Al vs PC mock-ups, with halo-window antenna vs caseback antenna.
3. Get CIM quotes for the zirconia caseback (2–3 Dongguan/Chaozhou suppliers; ceramicstimes etc.) and a slip-cast porcelain dock quote (RO + CN).
4. Test a 10-person blind "which is more expensive" ranking of weighted looks-like models (Ti 85 g / Al 65 g / Al + ballast 80 g / PC 55 g).

## 7. Sources (fetched 2026-09-24)
- https://www.waveshare.com/esp32-s3-touch-amoled-1.8.htm [V] · https://www.waveshare.com/esp32-s3-touch-amoled-2.16.htm [V] · https://www.waveshare.com/esp32-s3-touch-lcd-2.1.htm [V] · https://www.waveshare.com/esp32-s3-touch-lcd-2.8c.htm [V]
- WebSearch "largest round AMOLED…" → viewedisplay.com 1.75" 466×466 round AMOLED; youritech.com round range 1.28–2.1 (2.1 = TFT) [V-snippet / V]
- https://en.wikipedia.org/wiki/Apple_Watch_Ultra [V] · https://en.wikipedia.org/wiki/Apple_Watch [V] · https://www.apple.com/newsroom/2024/09/apple-watch-ultra-2-now-available-in-black-titanium/ [V]
- https://en.wikipedia.org/wiki/Zirconium_dioxide [V] · https://en.wikipedia.org/wiki/Titanium [V]
- https://en.wikipedia.org/wiki/Apple_Vision_Pro [V] · https://en.wikipedia.org/wiki/Amazon_Echo_Spot [V] · https://en.wikipedia.org/wiki/Jibo [V] · https://en.wikipedia.org/wiki/Vector_(robot) (→ Cozmo article) [V]
- https://en.wikipedia.org/wiki/EVE_(WALL-E) [V] · https://en.wikipedia.org/wiki/HAL_9000 [V] · https://en.wikipedia.org/wiki/BB-8 [V] · https://en.wikipedia.org/wiki/Baymax [V] · https://en.wikipedia.org/wiki/Oura_Health [V]
- https://living.ai/product/emo/ via WebSearch snippets (94×66×117 mm, 248 g, $279) [V-snippet]
- WebSearch "slot antenna for all-metal smartwatch" → ResearchGate/IEEE 7481365 (97 mm × 1 mm circular slot, 2.4 GHz) [V-snippet; full text 403]
- CNC/CIM cost pages (rapid-mfg.com, newayprecision.com, le-creator.com) gave no hard numbers → all housing costs are [E]
- Not fetched ([K]): TARS, Her device, B&O, Leica, Pixel Watch, sink-mark rules, zirconia εr/toughness, finish costs, Alba Iulia porcelain
