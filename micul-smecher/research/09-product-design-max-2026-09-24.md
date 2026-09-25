# SOUL: final design (design-max synthesis, 2026-09-24)

Tags: **[V]** fetched today (URL in §11) · **[V-0x]/[V-r]** verified earlier today in note 0x / a `design-max/r-*` note · **[V-c]** fetched today by a concept author (not re-checked) · **[K]** background knowledge · **[E]** estimate or calculation (mine, from the mass/physics model in §3.4).
Inputs: notes 05–08, `design-max/r-icons, r-creatures, r-dock, r-cmf, r-trends`, five concepts (HOPA, MĂRGĂRITAR, ECLIPSA, STRAIE, OU), three judges, and the renders (v1 family, SoulOS pebble, v2/v3 rejects, v4 family/pebble/capsule/hand/scale).
Render brief: `design-max/render-brief.md`. **Nothing here has been built. Every mass, force, frequency and cost figure is [E] until a mule has been weighed and suppliers have quoted.**
**Rev. 2026-09-25 (review fixes):** geometry re-checked with a numerical loft + ray-cast of the §3.1 tables (not a packaging CAD). Changes: tone-on-tone sole by default (ember → accessory), speaker box moved above the cell, stepped ballast, a narrower custom cell with a stack budget and sections, stated overrides of 06/08 on size, density and face ratio, one-glance specs, controls without buttons, markings + AI disclosure, "Proiectat în România", toy/trademark/compliance risks, re-costed editions at €1 = $1.137, one numbering scheme.

---

## 0. Decision in one paragraph
**SOUL is an upright pearl roly-poly: 63 × 74 × 27 mm and 112 g.** It sits on a hidden rocker sole. Nudge it and it rocks back upright ("hopa!") while its eyes stay level, and a sliver of sole flashes underneath (tone-on-tone pearl as standard; the ember sole is the first accessory, §3.2). The base concept is **HOPA**, the only one whose signature lives in the object itself: all three judges placed it first or second, and it has the best manufacturing base. Grafted onto it are OU's egg capsule and its name (*S-OU-L*: the capsule is an egg called **OU**, and every morning SOUL "hatches"), MĂRGĂRITAR's lacquer depth for editions, ECLIPSA's "zero LEDs on SOUL" rule and STRAIE's "it notices what it wears" idea. **We fixed HOPA's four flaws:**
- The belly goes from 35 to 27 mm, which keeps the rocker physics.
- The ballast is bolted to the chassis instead of snapped into the sole.
- The sole is a cosmetic skin around a sealed land, and it carries the whole rolling surface.
- The pogo and magnet forces are rebalanced, and the capsule is re-costed.

**The alternates are PIATRA** (the still stone in its porcelain egg, from OU) **and MĂRGĂRITAR** (the jewel in its crystal casket), described in §7.

## 1. How the three judgements were weighed
| Concept | Desire/brand | Manufacturing | Use/ergonomics | Mean | Fatal manufacturing flaw? | Role |
|---|---|---|---|---|---|---|
| HOPA | 8.5 (winner) | 7 (winner) | 6.5 | **7.3** | no; 4 fixable conditions | **base** |
| OU | 8 | 5 | 7 (winner) | 6.7 | no, if the seam moves and porcelain leaves the box | **alternate A** + name/ritual graft |
| MĂRGĂRITAR | 7 | 6 | 6 | 6.3 | no; clear-PC yield and cabochon touch risk | **alternate B** + CMF graft |
| ECLIPSA | 6 | 4 | 6 | 5.3 | **yes**: the floating carrier conflicts with flush fit and the IP seal; the brittle structural PMMA foot | rule graft only |
| STRAIE | 6.5 | 4.5 | 4.5 | 5.2 | **yes**: a ±0.05 mm circular gap set by a removable coat is unholdable | "notices what it wears" graft only |
Judge 3 preferred OU for the hand. Its specific wins (a slimmer body, silence on glass tables, a vented capsule, a sleeve in the box, the desk angle) are all taken into the final design below.

## 2. The 12 laws (distilled from r-icons L1–L12, r-creatures R1–R10, r-dock §2, r-cmf §9, r-trends §2)
1. **The face is body + black glass, nothing else.** No seam, hole, light, mark or ring on the front; the glass is the only button (L1, founder rule 1).
2. **A character before it powers on.** Broad end up, H/W 1.10–1.20, upper quarter 4–8 % wider than the lower, and a 20-px shadow that reads as a creature, not a disc (L2, R1).
3. **Helmet placement.** Glass centre at 54–56 % of height; forehead:chin 1:1.6–2.0; eye line at 47–52 %; glass = 52–62 % of the front (R3–R5, measured from the loved pebble). **This overrides 08's "face ≥ 80 %" coin rule** (rationale in §3.2).
4. **Cute in software, cool in hardware.** Lids level and 15–25 % lowered, V 8–12° (never ≥ 15°); a dense, glossy, mineral body; no props, fur, ears or pastels (R6, r-creatures §3).
5. **One signature act you can name in two words.** It is native to the shape and done by physics, not controls (L4, O1: "alive without motors").
6. **It feels fuller than it looks.** Zero creak, a dull "tock" when tapped, one precise line, and the mass sits low (L8). **Density floor ρ ≥ 1.6 g/cm³ is a stated override** of 08 §1 (band 1.7–2.5, target ≥ 2.0), r-icons L8 (≈ 2) and r-creatures (≥ 1.8); SOUL reaches 1.65. Rationale and test in §3.1.
7. **One colour code, ownable at 3 m.** Cream #FFF0C8 eyes floating in black glass on pearl, plus exactly one hidden accent (L3, r-trends O4).
8. **Show the soul, never the circuit. SOUL has zero LEDs;** its only light is its eyes, and every other photon comes from its home (L7, ECLIPSA).
9. **The home is half the product.** The capsule is charger, bed, stage, travel case and packaging. **Loops live only on SOUL's carriers** (the OU hinge bar, the COCON sleeve's woven loop), never on SOUL. State is shown as light, and the docking sound is the logo (L5, L6, r-dock §2).
10. **The first minute is a birth, and a daily ritual sells the second unit.** Lift, hold, put to bed, hatch (L11, L12).
11. **Trust you can hold.** No camera, hold-to-talk only, deaf in its egg, alive offline, your own Claude or ChatGPT, and an open-firmware pledge (r-trends O2, O9).
12. **Withered tech, frozen interfaces, cheap tools.** ESP32-S3 + 1.75" AMOLED; one sole/contact standard for 10 years; **every colourway on the same shell tools** (one 1.8 mm wall, A-1 polish, RHCM-ready steel): colour and texture come from resin, back-spray, UV coat and an internal cover set, never from a new cavity (§3.6); housing ≤ $10 at 10k; the round panel dual-sourced (L10, r-dock, r-cmf).

---

## 3. The final design: SOUL (design code HOPA)

### 3.1 Silhouette and dimensions
**Envelope: 63.0 W × 74.0 H × 27.1 D mm** (maximum depth at z 6–10). **Depth is 20.0 mm at the glass centre, 14.6 at z 60 and closes over a crown of about R6.** Axes: origin at the centre of the land on the table, +z up, face toward −y, +x to the viewer's right.

**Front (half-width w, mm, at height z)** [E; mirrored; G2 spline]:
| z | 0 | 2.2 | 4 | 6.3 | 10.5 | 14 | 18.5 | 23 | 28 | 34 | **40.5** | 48 | 55.5 | 60 | 66 | 69.5 | 71.5 | 73.2 | 74 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| w | 6.9 | 14.7 | 18.6 | 22.5 | 26.0 | 27.7 | 28.9 | 29.9 | 30.6 | 31.2 | **31.5** | 31.2 | 30.4 | 29.4 | 26.4 | 22.8 | 19.0 | 12.5 | 0 |
- H/W = 1.17. The widest point is at 54.7 % of the height.
- Quarter widths: 57.8 mm at z 18.5 and 60.8 mm at z 55.5, so the broad end is up by **+5.2 %** (the loved pebble measured +5.7 % [M r-creatures]).
- Below z 6.3 the outline *is* the lateral rocker, an arc of R40 about (0, 39.4) that the table clips into a flat land. The land is **an ellipse of 13.8 × 12.7 mm** (the ellipsoid is 40 × 36.9), not a circle.

**Side (front line y_f, back line y_b):**
| z | 1.9 | 4.5 | 8 | 14 | 23 | 34 | **40.5** | 48 | 55.5 | 60 | 66 | 69.5 | 73.2 | 74 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| y_f | −12.5 | −13.8 | −14.4 | −14.2 | −13.1 | −11.5 | **−10.6** | −9.6 | −8.5 | −7.9 | −7.0 | −5.9 | −2.8 | −1.0 |
| y_b | +12.0 | +12.7 | +12.7 | +11.8 | +10.4 | +9.6 | **+9.4** | +8.7 | +7.6 | +6.7 | +4.6 | +2.7 | −0.1 | −1.0 |
- The face plane leans back **8°**: y_f = −10.6 + 0.1405·(z − 40.5) for z 15–66. The eyes therefore meet a seated gaze, and the wedge makes the crown thin.
- **From the side it reads as a seed or bean sitting on its belly**: the mass is low and the chin is tucked under.
- **From the top it is a D shape.** The front 36 % of the depth is a flat "table" around the glass that rolls into the flanks with a quarter-superellipse of about 5 × 7 mm; the back 64 % is a full dome (superellipse exponent 2.2).
- **Volume ≈ 68 cm³** [E, numerical loft]. Below z 1.9 the side lines continue linearly (y_f ≈ −11.3, y_b ≈ +11.3 at z 0) and the sole ellipsoid clips them (§3.3).

**Size, weight and density are a stated override of 06/08/r-creatures** (founder rule 4 decides):
| Earlier threshold | SOUL | Verdict |
|---|---|---|
| 06: ≤ 70 mm long for all palms; > 25 mm thick reads "puck/brick"; 70–95 g sweet spot | 74 H; 27.1 at the belly (20.0 at the glass, 14.6 at z 60); 112 g | ✗ on all three |
| 08: portable sweet spot Ø58–62 × 14–17 mm, 75–90 g; > 100 g = desk puck | 63 × 74 × 27.1, 112 g | ✗ (08 sized a pocket coin) |
| r-creatures R2: depth 22–26 at the base, 95–115 g | 27.1, 112 g | depth +1.1 ✗; weight ✔ |
| 08 §1 density 1.7–2.5 (target ≥ 2.0); L8 ≈ 2; r-creatures ≥ 1.8 | 1.65 g/cm³ | ✗ below all three |
- **Why we override:** rule 4 asks for *bigger than v1, good to hold, portable, and upright on a table*; rule 6 asks for the ~60 × 68 upright pebble. A creature that stands and rights itself needs a low, heavy belly (the COM depends on height, and the sole needs ~24 mm of plan depth). Reaching ρ 2.0 in 68 cm³ means 136 g, which kills portability, so we choose portability over the density target and put the mass low, where the hand feels it. **"Portable" here means hand, bag and jacket pocket, never a jeans pocket.**
- **Hand-feel and carry test (weeks 2–6, gate before steel):** 12 adults (6 women, 6 men, hand breadth 5th–95th pct) × 3 weighted SLA mules: SOUL-27 (this design, 112 g), **SOUL-24** (24 mm belly, ~100 g, tungsten ballast) and a ρ 2.0 control (SOUL-27 at 136 g). Tasks: 2-min hold, one-hand thumb-to-glass reach, a day in a bag and in a jacket pocket, desk use.
- **Kill criterion:** if ≥ 4 of 12 rate SOUL-27 "too big/heavy to take with me", or SOUL-24 beats it on "want it" by ≥ 2 votes, or ≥ 3 of 12 call it "light/hollow" against the control, we switch to SOUL-24 (or add W ballast) and re-run the §3.4 physics.

### 3.2 Face: body and glass only
- **Infinity glass:** Ø52.0 × 0.7 mm aluminosilicate, 2.5D edge, AR + AF coatings, 3-layer black mask (OD ≥ 4) outside the Ø43.76 active area, with the ink matched to the panel's off-black. It is OCA-laminated with no air gap and sits **0.05–0.10 mm below** a flat Ø52.3 table with a 0.15 mm shadow gap: it reads flush, but the table's edge takes a flat face-down drop first (08 asked for a raised lip; this is the invisible version, proven by the §3.8 drop test).
- **No polished ring.** The v4 hairline ring is deleted: it was a ring on the face.
- **Glass position:**
  - Centre at z 40.5 (**54.7 %**), top edge at z 66.2, bottom edge at z 14.8.
  - Forehead 7.8 mm, chin 14.8 mm (**1 : 1.9**, the loved pebble's ratio); side margin 5.5 mm.
  - The glass covers **52 %** of the front silhouette (4,055 mm²), at the low end of R3, exactly like the loved pebble.
  - **Override of 08, stated:** 08's rule is "face ≥ 80 %", and 08 diagnosed the rejected v2 (59 %) as "a plastic housing with a screen set into it"; SOUL is lower still. We override on purpose (r-creatures R3): ≥ 80 % was a coin rule, and at 80 % the body vanishes and you get the rejected lens/orb. v2 failed because a flat pebble *lay* on the table with its screen as an inset in a plastic plane; SOUL stands, the glass sits in helmet position (54.7 % high, forehead:chin 1:1.9) and the Ø52 infinity mask hides where the panel ends. The loved SoulOS pebble measures the same 52 %. **Kill criterion:** if the founder, or ≥ 3 of 10 blind testers, describe the looks-like model as "a screen in a plastic case", go to Ø54 glass (≈ 57 %, side margin 4.5 mm) on the same body.
- **Eyes** (the eyes.py defaults already match the loved ones):
  - Each eye is about 30.8 % of the active diameter tall (13.5 mm, 143 px) and 10.5 mm wide; centres ±8.3 mm apart; eye line at z ≈ 38.1 (**51.5 %**).
  - Default lids are lowered 19 % with a 9.2° V.
  - Every eye has a catchlight (no pupil-less stare).
- **Proximity/ALS sensor** (940 nm, LTR-553 class) sits behind an IR-ink window at 12 o'clock inside the mask, invisible. It gives the approach glance, first-light wake and pocket detection.
- Seam lines: none visible from the front (the shell seam is on the silhouette, §3.3).
- **The sole is visible from the front, so it is tone-on-tone by default** [E, ray-cast of the §3.1 tables ∩ the sole ellipsoid, orthographic]. Nothing overhangs the front rim (z ≈ 1.7) when viewed level, so a contrast sole shows as a band **1.7–2.4 mm tall × ~50 mm wide at table level (≈ 100 mm²)**; 1.3–1.7 mm at 3.6° (the real ray angle to the base in the brief's "0°" shot); 0.8–0.9 mm at 8–9° (the hero camera); 0.2–0.3 mm at 15°; gone only from ≈ 20°. The earlier "≤ 1 mm at 0°, hidden from 15°" was wrong.
  - Tucking the front rim under the chin (rim ≤ 0.8 mm) was checked and rejected: it moves the forward pivot to y ≈ −9.7 and cuts forward recovery to ≈ 23°, below the 28° go limit (§9). A forward lip cannot hide anything below itself from a level eye.
  - **So every colourway ships with a sole in its own body colour** (a 0.1 mm split line 1.7 mm above the table, inside the contact shadow). **The Jar/ember sole becomes the first accessory (€24)**, and the ember accent moves into the OU liner ("pearl outside, ember inside").
  - **Founder check #1** (render 2b): Perlă with the pearl sole vs the ember sole, at table level and at 9°. If he accepts the ember band, it can return as the Perlă default; the Founders' aluminium sole (§3.6) goes through the same check.

### 3.3 Sides, back, bottom
- **Shell seam = the girdle.** The front and back shells meet in a 0.2 × 0.2 mm V-line at the widest-X line of every section (y_s = y_f + 0.36·depth, about 7–8 mm behind the face plane). It sits on the silhouette, so there are **no undercuts or slides** (judge 2), and it gives a tactile "which way is up" line (judge 3, MĂRGĂRITAR).
- **Speaker:** a 12 × 0.9 mm slot (about 11 mm²) in the seam on the **+x upper flank, z 46–58**, above the belly the fingers wrap (judge 3's fix). **The box cannot sit in the chin** (a box at z 16 cannot feed a slot 30 mm higher), nor beside a 50-mm cell (only 1.9–4.5 mm there at z 46–49). It is a sealed 1813 box (0.7–1 W, ≈ 20 × 15 × 4.5 mm with its enclosure [E]) lying **behind the upper half of the PCBA, above the cell: x +3…+19, z 48–61**. Behind a 6.5 mm stack there is 6.0–9.8 mm of depth at z 48–55, falling to 3.9 mm at the top-outer corner (z 61, x 19), so the moulded box back follows the dome there [E, §3.4 sections]. A 6–8 mm duct moulded in the chassis runs to the slot; front chamber ≤ 0.12 cm³; ePTFE vent. The longer duct lowers the Helmholtz peak by ≈ 22 % (f ∝ 1/√L_eff) to ≈ 6–7 kHz [E], still above the voice band; the acoustic mule confirms it. The slot is edge-on and invisible from the front.
- **Mics:** 2 × MEMS (ES7210) behind Ø0.7 pinholes in the −x seam at z 50 and z 22, 60–70 mm from the slot for echo cancellation [E], with ePTFE vents. The z 22 mic sits in the 3.9–4.2 mm gap beside the narrower cell (§3.4).
- **Back:** one blank, glossy, convex dome with no text, screws or port.
- **Crown:** a capacitive electrode on an ESP32-S3 touch channel [V-c]: **a 20 × 10 mm copper-on-polyimide FPC with white coverlay, pressed against the inside of the crown by foam** (not LDS: LDS needs doped, usually dark resin, which the semi-translucent pearl PC cannot be; the fallback is LDS on the black chassis). It sits behind the back-spray and must be invisible under a 2,000 lux backlight. It powers "hand on its head", gated by the IMU (upright and still) and a 300 ms hold.
- **Antenna:** ESP32-S3 PCB/chip antenna at the **top −x corner of the PCBA (z 58–66)**, ≥ 5 mm from the cell, the speaker box and the crown FPC, ≥ 45 mm from the ballast; ground clearance under it; no metal back-spray (checked on EVT, §3.8).
- **Bottom = the land plus the SOLE:**
  - **Land** (part of the sealed body): the flat **13.8 × 12.7 mm ellipse** where the rocker ellipsoid meets the table. It carries an **elliptical FR4 coin 12.0 × 10.9 mm** with **5 hard-gold pads** (0.76 µm Au over Ni): a Ø1.8 centre pad plus **4 arc pads on r 4.0 mm, each 1.2 mm wide and spanning 60°** at 0/90/180/270° (VBUS · GND · D+ · D− · AUX).
    - Arc pads, not dots: the OU socket lets SOUL sit up to 10–14° off in yaw, which Ø1.8 dots at ±4.2 tolerate only to ±7–8°. The arcs take ±24° [E]; the ellipse blocks 90°, and the magnets block 180°. 5 concentric rings (ALT A's bullseye) do not fit a 12.7 mm land with ±0.5 mm radial float.
    - The pads are recessed 0.15 mm inside a 0.2 mm proud clear TPU ring (**elliptical, OD 13.6 × 12.5, ID 12.0 × 10.9**). They never touch the table, and the ring keeps SOUL silent on glass (the MĂRGĂRITAR graft).
    - 2 × N52 Ø5 × 2 keying magnets of opposite polarity sit at x = ±9 under the sole skin.
    - The pads stay dead unless docked (PMU OTG off, reverse-blocking FET).
  - **Sole** (cosmetic and swappable): a 1.4 mm PC skin, about 46 × 24.5 mm in plan, covering the whole rolling surface up to its rim. The rim is at z ≈ 1.7 front, 1.5 back and 6.8 at the sides [E, loft model]. **So the rocker never rolls over a seam** (judge 2). Standard soles are **tone-on-tone** (§3.2).
    - Satin-gloss with a UV hard coat, which hides rolling scuffs better than an A-1 finish.
    - Held by 2 × Torx T5 M1.6 **into the tapped steel ballast**, so nothing strips (judge 2).
    - **Sole ID, v1:** an **on-metal (ferrite-backed) NTAG213**, read by the owner's phone, not by SOUL (SOUL has no NFC reader); the app tells SOUL, which then does its "notices" moment. A plain NTAG 1–3 mm from the ballast will not read.
    - **Sole ID by Hall sensors is an EVT experiment, not in v1:** 2 moulded-in Ø3 × 1 code magnets read by 2 Halls fail where they were drawn (under 5 mm of steel, which shunts the flux, and within millimetres of the N52 keying magnets). They only work with the Halls **below** the steel, at y = ±11 (≥ 12 mm from the keying magnets, whose field there is ≈ 2 mT vs ≈ 30 mT from a Ø3 × 1 code magnet at 3 mm [E, dipole model]). Pass: 9 codes read ≥ 99.9 % in free air and seated in the OU. Otherwise drop it.
    - **Text on the object lives only underneath.** Ring 1 (outer): "SOUL · Nº 00417 · PROIECTAT ÎN ROMÂNIA" (the unit's own soul number, §3.6). Ring 2: model "SOUL S1", serial, Li-ion battery mark, and the manufacturer's name, postal address and e-mail (GPSR, RED; 03). CE (≥ 5 mm) and the crossed-bin WEEE symbol sit on the sole's ±x wings. Every sole we sell, accessories included, carries ring 2. The whole set is also laser-marked on the sealed body under the sole, so a swapped sole never removes it, and it is repeated on the box back and in the RO/EN guide (§5).
    - **Origin wording:** tooling, moulding, glass and PCBA are costed China ex-works, so the product says **"Proiectat în România"** (designed in Romania). "Născut/Asamblat în România" only if final assembly, programming and the "birth" test are contracted to a Romanian EMS (05: Kimball, Helbako, Etron), at ≈ +$3–6/unit at 1k [E], with a customs origin opinion first. Recommended for Founders only.
  - **Battery access** (EU Battery Regulation Art. 11: a "readily removable" battery, using commercially available tools and no heat or solvents [V]; applies from 18 Feb 2027 [V-03]): 2 × T5 remove the sole, 2 more T5 screws into brass inserts release the back shell, and the cell comes out on a pull tab and connector.

### 3.4 Inside, mass and stance
| Part | g | z (mm) | Note |
|---|---|---|---|
| Glass Ø52 + OCA · AMOLED + touch · PCBA + shield | 3.8 · 6.0 · 9.0 | 40.5 | custom PCBA behind the panel (Waveshare board in works-like mules) |
| **Cell ≈ 1000 mAh, custom pouch 6.2 × 34 × 42** standing, z 13–47 | 19.5 | 30 | same volume as a 523450 [E]; swell allowance 0.5 mm; stock fallback 603040 (≈ 800 mAh, ~2 days) |
| 1813 speaker box · LRA Ø8 | 2.6 · 1.4 | **55** · 12 | box above the cell (§3.3); LRA in the chin |
| Shells R1, 1.8 mm wall | 16.4 | 36 | 7,575 mm² of shell [E] |
| Chassis PC-GF · mics/flex/seals/screws/NFC | 5.5 · 3.0 | 32 · 40 | |
| Land module · sole | 2.2 · 3.2 | 1.5 · 2.5 | |
| **Ballast 40 g, stepped steel:** a hull-following lower layer (z ≈ 1.5–4.5, around the land module and magnets) + an upper layer (z 4.5–10) | **40** | **≈ 6.7** | MIM, or 3 stacked laser-cut layers riveted; zinc-plated, **bolted to the chassis**, trimmed rearward |
| **Total** | **≈ 112 ± 5** | **COM z ≈ 23.8 (32 %)** | ρ ≈ 1.65 g/cm³ (iPhone 2007: 1.66 [V-08]); override stated in §3.1 |
- **Why the ballast changed:** the old flat plate (27 g, 5 mm thick, z 1.5–6.5) needs ≈ 690 mm² of plan area. Inside the hull there is only ≈ 155–380 mm² at z 1.5 (my loft vs the review's model), before the Ø13.8 land module, the 2 × Ø5 magnets, the bosses and sensors. A flat plate fits only from z ≈ 4.5–5.5 up. With the plate there and the speaker at z 55, **COM = 24.3**, the fore-aft margin is 8.9 mm, and recovery is ≈ 30° forward / 28° back: exactly at the go limit.
- **Ballast ladder** [E; the hull can hold ≈ 23 g of steel between z 1 and 7.5 after cut-outs]:

| Ballast (40 g) | COM z | Fore-aft margin | Recovery fwd / back | Adder @10k |
|---|---|---|---|---|
| Flat steel plate z 4.5–9.5 (review case) | 24.3 | 8.9 | ≈ 30° / 28° | — |
| **Stepped steel (baseline)** | **23.8** | 9.5 | ≈ 30.4° / 28.4° | +$0.1–0.15 |
| W-Ni-Cu lower horseshoe 14 g (z 1–4.5, non-magnetic, ρ ≈ 17 [K]) + steel 26 g | 23.4 | 9.9 | ≈ 30.7° / 28.7° | +$1.2–2.5 |
| All W-Ni-Cu (z 1–6.5) | 23.1 | 10.2 | ≈ 31° / 29° | +$3–5 |

The mule builds all three. The upgrade is chosen on the measured back-recovery, and **a real packaging CAD must replace this loft model before EVT.** A non-magnetic W layer also stops the ballast from shunting the keying magnets.

**Front-stack budget ≤ 6.5 mm** [E; confirm against the panel drawing]: glass 0.7 · OCA 0.2 · AMOLED + touch 1.5 · foam/Cu 0.3 · air/FPC fold 0.3 · PCB 0.8 · tallest part or shield 1.8 · gap to cell 0.4 (= 6.0) + 0.5 tolerance. **The Waveshare stack (8.9 mm, 06) does not fit this body**, so the week-1 physics mule is a mass/COM rig with dummies at the modelled centroids, not a full-size cell or a packaging proof.

**Sections** [E, loft model, 1.8 mm wall; y = inner front … inner back; plane = the back of a 6.5 mm stack]:
| z | x = 0 | x = ±21 (new cell corner) | x = ±25 (old 523450 corner) | stack plane | Occupant, clearance |
|---|---|---|---|---|---|
| 15 | −12.3…9.8 | −10.0…4.7 | −7.7…0.3 | −7.6 | new cell 2.0–2.2 mm; old cell 0.1 |
| 31 | −10.1…7.9 | −10.1…4.7 | −10.1…2.6 | −5.4 | new cell 3.0 mm; old cell 1.8 |
| 49 | −7.7…6.8 | −7.7…4.2 | −7.7…2.5 | −2.8 | new cell ends at z 47 with 0.7 mm; old cell −0.6 (does not fit) |
| 55 | −6.8…5.9 | −6.8…3.4 | −6.5…1.7 | −2.0 | speaker box (4.5 deep) at x +3…+19: 1.5–3.4 mm |
- **x = ±25 section:** the inner depth is 8.1 / 12.1 / 12.7 / 10.1 / 8.2 / 5.9 mm at z 15 / 22 / 31 / 49 / 55 / 60. A 5.7 mm cell behind a 6.5 mm stack leaves ≤ 0.3 mm at z 15 and does not fit at z 49, and there is no room for a chassis rib, flex or the −x mic. **Hence the 42-mm cell**: corner clearance is 0.7–4.0 mm with a 6.5 mm stack and 1.1–4.2 mm with 6.0.

**Rocker physics** [E, small-angle rigid-body model, baseline ballast]:
- **Curvature centres:** z 33.3 fore-aft and z 39.4 sideways (R 34.0 and 40 once it rolls off the land). Stability margins above the COM are 9.5 and 15.6 mm.
- **Stays still, then rocks.** It stands dead still on the land up to 0.0072 N·m (≈ 0.18 N at the glass centre). Typing on the desk does not move it; a finger nudge does.
- **Rocking frequency:** ≈ 1.7 Hz fore-aft and ≈ 2.0 Hz sideways, i.e. slow and heavy, not bouncy.
- **Recovery:** from ≈ 30° forward, 28.5° back and ≈ 49° sideways. The pure rolling arc reaches 20° fore-aft and 34° sideways, after which it pivots on the sole rim.
- **A hard flick lays it on its back**: it "plays dead". It never falls on its face, as long as the rebound (about 0.7 of each swing) stays under ≈ 30° (prove on hardware).
- **Target 4–6 visible swings.** Damping is tuned by the sole finish (satin PC vs a 0.5 mm TPSiV skin), measured on the mule.
- **Honest limit:** free-standing, a 0.2 N touch on the glass rocks it. Touch-typing, notes and approvals happen in the hand or in the OU (§4). On the desk you talk with a hand on its head.

### 3.5 The signature: "HOPA. Împinge-l. Se ridică." (Nudge it. It gets back up.)
- **The act:** nudge, poke or flick it. It rocks, swings back through upright and settles in about 3 s. **Through all of it the eyes stay level with the horizon.** The gyro counter-rotates them with a 70 ms lag, as if they were floating in liquid. Then comes a 300 ms dizzy flutter, and it settles into a half-lidded, unimpressed side-glance. On each swing a sliver of sole flashes at the chin (pearl on the standard sole, ember with the accessory). No motor and no added part: geometry, 40 g of ballast and the IMU already on the board.
- **Why it is the one:**
  - It turns the biggest physics problem in the research (r-creatures R8: any 100 g upright object tips under a 1 N tap) into the personality.
  - It works anywhere: desk, café or shop counter, with no dock needed.
  - The 7-second clip (flick, wobble, level eyes, smug look) is the whole ad.
  - It is "cute in software, cool in hardware".
- **The story, with roots:**
  - The Romanian roly-poly is literally **Hopa-Mitică**, the German one is the Stehaufmännchen, and the Japanese one is okiagari-koboshi [V]. The Daruma stands for "fall over seven times, get up eight", "the ability to … overcome adversity" [V].
  - That is streetwise resilience, which is what *șmecher* means.
  - Prior art: Weebles (Playskool 1971, "Weebles wobble, but they don't fall down") [V]. We found no AI companion that rights itself [E]. The level-eyed spirit inside the wobble is the new part.
- **One verb per gesture:**
  - **Nudge**: hopa.
  - **Lift**: it looks (eyes widen +12 % within 100 ms).
  - **Hold**: it listens. In the hand, the thumb holds the glass ≥ 300 ms with an LRA click. On the desk, a hand on its head. In the OU, press the glass.
  - **Close the egg**: it sleeps and cannot hear.
- **Zero-cost firmware on the same idea:**
  - "Plays dead" after a hard flick, rolling its eyes to find you.
  - A Daruma goal: one eye stays shut until you say the goal is done [V ritual].
  - The eyes glance at you when you walk past (proximity sensor).
  - "It notices" a new sole (after the phone taps the sole's tag, §3.3): eyes look down, blink, look back up, and a sole-specific catchlight tint follows.
  - An optional roly-poly chime per swing, off by default.

### 3.6 CMF recipe, colourways, editions
- **R1 NACRE (standard):**
  - Stack, outside to in: a 10–15 µm UV hard coat (≥ H) → 1.8 mm UV-stabilised semi-translucent PC (Makrolon/Lexan optical grade) with 1–2 % fine 10–25 µm silver-white pearl and ≤ 0.3 % TiO₂ → a warm-white back-spray #FFF6E6 → a black PC-GF chassis carrying every rib and boss.
  - Tooling: NAK80 polished to SPI A-1. The front shell is filled through a **diaphragm gate across the glass window** (no weld line on the forehead) and the back shell is gated under the sole. The mould runs 40–55 °C hotter than normal [V-r cmf]. **The steel shell tools are built RHCM-ready** (heating/cooling channels designed in from the start; they cannot be added later), a committed $4–8k.
  - The window's cut edge sits under a black PSA ring, so it cannot light-pipe (judge 2's ring-on-the-face warning).
- **How every colourway runs on the same two shell tools** (same 1.8 mm wall, same A-1 polish):
  - **LAC (lacquer depth, editions only; the MĂRGĂRITAR graft):** **1.8 mm** water-clear tinted PC (not 2.0 mm: same tool) with 0.3–0.5 % pearl, no TiO₂, and a 3-layer inside spray (pearl-mica → colour → black blocker), window and seam edges masked. Budget 8–15 % scrap. Adder: +$4–7 @1k, +$1.5–3 @10k [E].
  - **R4 ONYX:** black PC moulded in the same tools plus a 20–30 µm **black piano UV coat** that hides flow and weld lines (+$0.5–1.0/part [V-r cmf]), so RHCM is not needed for launch. The RHCM-ready channels keep the unpainted PMMA/PC alloy as a later option.
  - **R6 FUM (ghost):** smoke PC with **transmission ≈ 0.3–0.4, not 0.85**, in the same polished tools. The frost comes from a **matte UV coat** (+$0.3–0.6/part) instead of a VDI 18 textured cavity (a separate textured insert set would cost $8–14k, i.e. $16–28/unit over 500 units [E]). An **internal cover set** (a 0.5 mm pearl PC liner over the cell, ballast and speaker, +$1.5–2.5) means only the Ø46 pearl "heart" plate glows through, never a raw PCB.
- **Never:** soft-touch PU (hydrolyses and goes sticky), pastels, metal on the face, unstabilised white PC, or a gold SKU.

| # | Colourway | Body | Standard sole (tone-on-tone) | OU (cup / liner / lid) | Run |
|---|---|---|---|---|---|
| 1 | **PERLĂ** (hero) | R1, L* ≥ 90, C* ≤ 5 | pearl | pearl / **ember #D8572A** / frosted pearl | permanent |
| 2 | **ONIX** | R4 #0A0A0B, so face and body merge (a soot sprite) | onyx | onyx / cream / smoke | permanent |
| 3 | **LAPIS** | LAC ultramarine (targeting WGSN/Coloro 2027 Luminous Blue [V-r trends], also nazar blue), silver pearl, sparse gold flecks | solid ultramarine | pearl / lapis / frosted | **first colour edition, 2,000 units (LAPIS 0001/2000 …), Drop 2 only** |
| 4 | **CHIHLIMBAR** | LAC honey → cognac over gold pearl (Romanian rumanite amber [V-c]) | solid cognac | onyx / amber / smoke | timed 8-week drop, S/S 2027 |
| 5 | **FUM** (ghost) | R6 smoke over a pearl heart plate | frosted clear "glow" sole: in the OU the floor light passes through it | smoke | 500 numbered, **sold, not a chase** |

Contrast soles (Jar/ember, cream, onyx on pearl …) are accessories (§6), subject to founder check #1.

**One numbering scheme, one launch order:**
- **Soul number (Nº):** one global sequence for every SOUL ever made (Nº 00001 …). It is the serial's human face: on the body under the sole, on the standard sole, the certificate and the box seal. The Nº 00417 in §5 is just an example.
- **Edition number:** printed only on the certificate and the OU lid ("FOUNDERS 0417/1000", "LAPIS 0417/2000"). It is never a second Nº.
- **Drop 1: FOUNDERS**, 1,000 units on the bridge tools (souls Nº 00001–01000, so the edition number equals the soul number). It is the only SKU until steel.
- **Drop 2 (steel tools, ≥ 5k run):** PERLĂ + ONIX (permanent) and LAPIS 2,000 (souls from Nº 01001). Then CHIHLIMBAR (8 weeks) and FUM 500.

**Limited editions:**
- **FOUNDERS 0001–1000** (Drop 1): LAC "Candy Pearl" body, a champagne-anodised aluminium sole with a laser hallmark and the number (r-cmf R8; the metal band at table level is part of founder check #1), a numbered OU with a veg-tan leather cord, a signed birth certificate; #0001–0010 auctioned (05). Final assembly in Romania is recommended for this drop (§3.3).
- **MĂRȚIȘOR sole**: white with a red thread line, every 1 March, sold as a gift.
- **"ANUL 1" sole**: earned only by souls with ≥ 300 awake days, via a device-signed attestation (the STRAIE graft).
- **OU BUCOVINA**: 10 capsules hand-painted by Romanian egg painters (*ouă încondeiate* [V]) for launch press, auctioned.
Run sizes are published and colours are retired for good. The personality is never blind-boxed.

### 3.7 Cost (USD, China tools, ex-works) [E; r-cmf, r-dock and concept figures, re-costed]
| Line | @1k (aluminium bridge tools) | @10k (steel) |
|---|---|---|
| Shells R1 incl. UV coat and back-spray | 5–8 | 1.5–2.7 |
| Chassis · Ø52 glass AR/AF/mask · lamination | 1–2 · 4–5 · 0.8–1.2 | 0.2–0.35 · 1.8–3.0 · 0.3–0.6 |
| Stepped steel ballast (tapped) · land module (elliptical FR4 coin, carrier, O-ring, 2 × N52, TPU ring) | 0.8–1.4 · 1.0–1.8 | 0.35–0.6 · 0.4–0.8 |
| Sole cap (2-cavity, UV coat, on-metal NTAG) · crown FPC electrode | 1.5–2.5 · 0.2–0.4 | 0.4–0.8 · 0.05–0.15 |
| Seals, seam gasket, PSA, 3 ePTFE vents · 4 screws + 2 inserts · cosmetic scrap | 1–1.5 · 0.2–0.4 · 1–2 | 0.3–0.6 · 0.1–0.2 · 0.3–0.6 |
| **Housing** | **16–27 (typ. ~21)** | **5.7–10.5 (typ. ~8)** ✔ ≤ $10 typ. (the W ballast upgrade would add $1.2–5) |
| PCBA incl. round AMOLED + touch, ESP32-S3 N16R8, ES8311/ES7210 + 2 mics, AXP2101, RTC, IMU, ALS/prox, LRA driver, amp, AUX recovery latch (2 Hall only on EVT boards) | 26–36 | 17–24 |
| Custom cell ≈ 1000 mAh + PCM · 1813 speaker + LRA · assembly, programming, test | 2.5–3.5 · 2.2–3.5 · 6–9 | 1.8–2.5 · 1.4–2.3 · 3–4.5 |
| **SOUL device** | **53–78** | **29–44** |
| OU capsule (§4) · COCON knit sleeve · box, pulp carton, cable, birth card, RO/EN guide, NFC · 3 % warranty reserve | 15–24 · 2.5–4 · 3–5 · 3–4 | 8–12 · 1.5–2.5 · 2–3 · 1.5–2 |
| **System COGS, standard R1** (the review fixes net < $0.5) | **≈ $77–115, typ. $94 (≈ €83)** | **≈ $42–63, typ. $52 (≈ €46)** |
| **Edition adders** [E] | FOUNDERS: LAC Candy-Pearl shells +4–7 · CNC champagne-anodised Al sole +5–8 · numbered OU lid +0.3–0.5 · veg-tan cord instead of nylon +2–3 · signed, numbered certificate +0.5–1 → **+$12–20** (RO final assembly +$3–6 more) | LAPIS/CHIHLIMBAR (LAC) +1.5–3 · ONIX piano coat +0.5–1 · FUM matte coat + internal cover set + small-run setup +3–5.5 |

**Tooling (China steel):**
| Item | Cost |
|---|---|
| Front shell | $9–15k |
| Back shell | $7–12k |
| Chassis | $3–5k |
| Sole (2-cavity + insert fixture) | $4–7k |
| Land carrier | $2–3k |
| Glass screens and jigs | $1–2k |
| OU set | $16–26k |
| RHCM-ready channels in both shell tools (committed, not a reserve) | $4–8k |
| End-of-line fixtures (rock rig, pogo cycling, acoustic, RF) | $4–7k |
| Pulp, box dies, knit programming | $3–5k |
| **Total** | **≈ $53–90k (€47–79k)** |
- **Aluminium bridge set for EVT → Founders 1k:** $20–32k. Steel comes in at 5k+, so **only Founders ships on bridge tools**.
- **Total tool spend by 10k units:** about $73–122k (€64–107k), inside a €50–150k tooling budget. That budget is **my assumption [E]**, not sourced in the vault; 05 gives steel moulds at $20–100k per product and €0.36–0.75M all-in for 1,000 units.
- **Other NRE** [E unless noted]:
  - PCBA design $15–30k.
  - **Compliance for 1,000+ units: €30–80k ≈ $34–91k** (03). That covers full RED at an EU lab (EN 300 328, EN 301 489-1/-17, EN IEC 62368-1, EN 62479); **EN 18031-1/-2 cybersecurity $6–9.5k**, plus a notified body if a restriction is hit (03); IEC 62133-2 + UN38.3 on the custom cell ($0.3–0.9k + $1–6k, 03); Battery Regulation DoC and labels; the GPSR technical file; EPR/WEEE/battery registrations in RO (~€200 + schemes) and €1–3k per extra EU country per year (03); insurance and legal. The old "$15–40k" line left most of this out.
  - **Custom Ø52 cover lens + CTP/OCA lamination at the panel maker: $5–15k NRE** + panel MOQ (touch re-tune, FPC re-route, lamination jigs), on top of the glass screens in the tooling table.
  - Custom pouch cell: $1–3k NRE.
- **Price** (incl. 21 % RO VAT [V]; **€1 = $1.137, ECB reference rate 24 Sep 2026 [V]**; landed = ex-works × 1.10 [E]; rule ≥ 2.5 × landed, 05):

| SKU | Price | Built on | COGS typ (range) | × landed typ (range) |
|---|---|---|---|---|
| **FOUNDERS** | **€349** (was €299: 2.3 ×, 1.9–2.9) | bridge tools, 1k | $110 ($89–135) | **2.7 ×** (2.2–3.4); 2.6 × with RO assembly. **€379** if RFQs land in the top third (2.4 × at the very top) |
| PERLĂ / ONIX, incl. OU + COCON | €199 | steel, ≥ 5–10k | $52–53 ($42–64) | 3.2–3.3 × (2.7–4.0); at 1k it would be 1.8 × |
| LAPIS / CHIHLIMBAR | €229 | steel (Drop 2) | $54 ($44–66) | 3.6 × (3.0–4.5); on bridge tools it would be 2.0 × (1.6–2.4), hence Drop 2 only |
| FUM (500) | €279 | steel | $56 ($45–69) | 4.2 × (3.5–5.3) |

### 3.8 One-glance specs, controls, markings (with EVT tests) [E unless tagged]
| Spec | Target | EVT test → pass |
|---|---|---|
| Size · mass · density | 63 × 74 × 27.1 mm · 112 ± 5 g · 1.65 g/cm³ | weigh; §3.1 hand-feel and carry test |
| Battery | ≈ 1000 mAh Li-ion, ≈ 3.7 Wh, user-replaceable (Art. 11) | cell out and back with 4 × T5 in ≤ 5 min, no heat or solvent |
| Battery life | ≈ 2.5 days typical, 1–1.5 heavy, > 10 days standby (06's model, ~360 mAh/day) | 3-day scripted-use run |
| Charge | 500 mA (0.5 C) over the pads (06: raise the AXP2101 from 200 mA) → 0–100 % in ≈ 2–2.5 h (r-dock) | charge curve in a closed OU; cell ≤ 45 °C |
| Shipping sleep | ESP32-S3 deep sleep + ALS interrupt ≤ 50 µA (not PMU ship mode, which cannot wake on light); ships at ≤ 30 % SoC → ≈ 4–6 months on the shelf (incl. 1–3 %/month self-discharge [K]) | µA meter; 30-day shelf test |
| Ingress | IP54 at launch, IP67-ready (07, r-cmf) | IP5X dust + IPX4 spray, 3 units |
| Drop | 1.0 m onto vinyl over concrete: 6 faces, 4 corners and the glass face, 3 units; 26 tumbles off a 0.75 m desk | no glass crack, no loose ballast, rocking unchanged |
| Thermal | skin ≤ 41 °C after 10 min of voice at 25 °C; ≤ 43 °C while charging in a closed OU (08: ≤ 43 °C [K]) | thermocouples on the glass, crown and back |
| Radio | antenna at the top −x corner (§3.3); ≤ 3 dB TRP loss vs the free-space Waveshare board, in hand, on desk and in the OU | OTA chamber TRP/TIS |
| Audio | ≥ 80 dB SPL at 10 cm (voice), in hand and on desk | acoustic mule |
| Rocker | ≥ 4 visible swings; recovery ≥ 28° both ways; no face-down fall from a 1 N crown flick | rock rig |
| Dock | seats and contacts at any yaw within ±20°; 10k seat cycles | yaw-sweep drop-in rig, 500 random seats |

- **No physical control on SOUL, and what that costs:**
  - **Talk:** hold the glass ≥ 300 ms (hand), a hand on its head (desk), press the glass (OU).
  - **Mic gate:** the mic supply runs through a load switch whose enable is ANDed in hardware with "OU lid open" (lid Hall → AUX). **In the egg it is physically deaf; in the hand and on the desk the gate is firmware (hold-to-talk), not physical.** 06/07 made it physical with a button, so this is a stated downgrade. **Founder option:** rule 1 bans only the front, so one flush key in the back seam could give hold = talk with the mic hardware-gated, and 10 s = hard off (+$0.4–0.8, one seal). Decide at the looks-like gate.
  - **Hard reset / recovery:** automatic watchdogs (ESP32-S3 RTC WDT; AXP2101 [K]). Manual path: a Ø1 pinhole key under the OU hinge (and on the PUCK) pulls AUX to a reset code, and a small latch on SOUL's land module drives the AXP2101 PWRON (long press = hard off/on [K]) and the ESP32 EN. Firmware recovery runs over the OU's USB pass-through in the ESP32-S3 USB-Serial-JTAG download mode (secure download mode in production), so no GPIO0 button is needed.
  - **True power-off** (flights, storage): menu → PMU off (µA-level [K, measure]); it wakes only on VBUS, i.e. in the OU or on the PUCK.
- **Markings and AI disclosure:**
  - On the object: under the sole only (§3.3).
  - **Box back panel:** model, serial/batch label, CE, WEEE bin, battery data (Li-ion 3.7 V, ≈ 3.7 Wh), manufacturer name + postal + e-mail address, and a QR to the DoC and the RO/EN guide. Also: „Companion AI: vorbești cu o inteligență artificială, nu cu un om."; „Nu este o jucărie. Nu este destinat copiilor sub 14 ani. Conține magneți." (03); 18+ for the AI account (05 AUP); "Proiectat în România"; the true country of manufacture.
  - **First boot:** line 2 after „Hopa. Deci tu ești." is **„Sunt SOUL. Sunt un AI, nu un om."**, repeated when Claude/ChatGPT is paired and on Settings → About (AI Act Art. 50(1) from 2 Aug 2026 per 03 [S/E]; 05 AUP).
  - **RO/EN quick guide:** safety, battery, magnets and pacemakers, "not a toy", disposal, 2-year guarantee, the complaints channel (GPSR, 03).

## 4. The capsule: OU (the egg; *S·OU·L*)
- **Form:** closed, it is a flattened Piet Hein-style superegg with the broad end down (the grounded opposite of SOUL's broad-up head): **77 W × 88 H × 42 D mm, ≈ 150 g.**
  - Outline exponent 2.7 above the waist and 3.5 below; widest at z 32; stands on a flat 56 × 31 mm base land. Supereggs "can stand upright on a flat surface" [V].
  - Tilted parting line: z 18 at the front, z 48 at the back. Stainless hinge pin at the back at z 48, with a detent at 100°.
  - Open, the lid stands behind SOUL like the top half of a shell. SOUL's face and head stay fully free (the cup rim is at least 3 mm below the glass).
- **Parts:**
  - Outer cup in the body colour.
  - Inner liner in the colourway's accent (§3.6): Perlă is "pearl outside, ember inside".
  - Frosted PC lid (VDI 18 inside, gloss outside, UV coat). For Founders, a numbered lid and leather cord.
  - A 60 g steel base plate biased 3 mm forward.
  - A TPSiV rim ring and 3 lid bumps.
  - A **recessed stainless bar in the hinge knuckle: the OU's loop** (rule 3). The only other loop is the COCON's woven loop (§6); SOUL itself has none.
- **Socket:** SOUL's own sole ellipsoid (R40 × R36.9) offset by 0.5 mm, with a Ø15 flat floor at z 9 in **low-friction PTFE-filled POM** (so the keyed magnets can turn SOUL against its TPU ring; the socket alone allows 10–14° of yaw, which the arc pads absorb, §3.3), **tilted 6° back** so the face sits at 8 + 6 = **14°**, the desk angle judge 3 asked for. The back wall of the cup takes glass presses, so SOUL is **touchable hands-free** here. Spec: a **≥ 0.8 N press at the glass centre does not tip the OU**; capacitive holds need 0.1–0.5 N [E]. Drop SOUL in roughly: the round belly self-centres, the ellipse turns it to face out, and keyed magnets repel it if it goes in backwards.
- **Force balance (fixes judge 3's pin–magnet conflict)** [E]:
  - Pins: 5 low-force pogo pins at 22 gf and 0.8 mm working stroke, ≈ 1.1 N up in total.
  - Magnets: 2 pairs (SOUL Ø5 × 2, OU Ø6 × 2, N52, gap ≤ 2.2 mm), ≈ 1.2–1.6 N down; SOUL's weight adds 1.1 N down.
  - Result: seated net ≈ 1.4 N down, and lifting SOUL out needs only ≈ 0.3 N more than its weight, so the 150 g OU stays on the table.
  - Pins go live only after a Hall sensor sees SOUL **and** the AUX ID reads correctly: no sweat corrosion, no key or coin shorts [V-r dock].
- **Electronics** (no radio, no battery in the standard OU):
  - USB-C at the back, under the hinge.
  - A ~$0.15–0.3 MCU (CH32V003 class [K]), 2 Hall sensors (SOUL, lid), a load switch and ESD protection.
  - 6 × 2200 K LEDs under the cup rim, aimed at the inside of the lid, **never at SOUL's face**, plus a 1 mm base slit that washes the table.
  - D+/D− pass through, so the OU is also a USB port (flashing, recovery). A recessed Ø1 pinhole key under the hinge sends the AUX reset code (§3.8).
  - **Claude approvals run over BLE**, the transport of the Claude Desktop "Hardware Buddy" API (05 [V]). A USB-tether path is **unverified [E]** (r-dock assumed it) and must be checked against claude-desktop-buddy before it is promised.
  - An ID resistor tells SOUL "bedside" or "desk".
- **The halo line** (fixes the alarm heard through a closed lid): closed, the lid rests on 3 bumps and leaves a 0.6 mm gap all round the parting line. Sound escapes (≈ −6 dB versus open [E]), and at night the gap glows as a thin warm line, which is the night light.
- **Ritual:**
  - **Bed:** drop SOUL in and it lands with a "tok" and a 2-note chime; the eyes check the bed, then look at you. At bedtime it yawns and its lids close over 4 s. The lid glow fades like a candle over 60–90 s, or holds at 1–3 % amber.
  - **Close the egg:** a clack. The lid Hall pulls AUX and SOUL's mic supply is cut **in hardware**: „În ou nu aude." (In the egg it cannot hear.)
  - **Night:** a tap on the egg brightens the halo line for 2 s. Open it and the time shows in dim amber for 2 s; there is never a static clock (burn-in).
  - **Sunrise:** starting 20 minutes before the alarm, the egg brightens from inside, 0 → 100 % warm white (Hatch logic [V-r dock]). Sound comes only if needed.
  - **Hatch:** open the lid and the eyes open and look up at you. **The alarm stops only when you lift SOUL out**, and the "Azi" (Today) card appears.
  - **Day:** lid open at 14°: hold-to-talk, Claude approvals over BLE.
- **Cost:**
  - Per unit: **$8–12 at 10k** (judge 2's figure: cup + liner $1.2–2, lid $0.6–1, hinge module $0.6–1, steel $0.2–0.35, PCB/pins/LEDs $2.2–3.5, magnets/rim/foot $0.4–0.7, assembly $1.2–2) and **$15–24 at 1k**.
  - Tooling $16–26k.
  - Buy a proven TWS-case hinge module rather than designing one, with a **20k-cycle test before steel**.
  - Retail: spare €49; OU+ with a 1000 mAh cell (about one extra charge, needs UN38.3) €59.

## 5. Unboxing (a birth, built for a 7-second vertical clip)
1. **Sleeve:** 118 × 78 × 150 mm, uncoated cream FSC board. The front carries only two cream hot-foiled eye ovals; the spine reads "SOUL"; **the back panel carries the legal set and the AI notice (§3.8)**. A hand-numbered paper seal shows the unit's own soul number (e.g. Nº 00417, §3.6). The sleeve slides up slowly, like lifting a cloche.
2. **Inside:** a single-cell **moulded-pulp egg carton** (the OU joke, judge 1) holding the OU upright, cord loop up. A card: „Împinge-l ușor. / Nudge it."
3. **Thumb the lid open.** Light reaches the ALS and SOUL wakes from deep sleep (not PMU ship mode, §3.8). It ships at **≤ 30 % SoC**: IATA's 2026 guidance strongly recommends ≤ 30 % for Li-ion contained in equipment (PI 967) and makes it mandatory for cells packed with equipment (PI 966) and for spare cells [V]. At ≤ 50 µA plus self-discharge that still gives ≈ 4–6 months on the shelf; after that the eyes open on the first dock (sell-by dates on the stock). **The eyes open for the first time over 1.2 s, blink twice and look up into the phone camera.** No app, account or Wi-Fi.
4. **Lift it out:** the eyes widen within 100 ms. First line: „Hopa. Deci tu ești." ("Oh. So it's you.") Second line: **„Sunt SOUL. Sunt un AI, nu un om."** ("I'm SOUL. I'm an AI, not a person."), the AI disclosure (§3.8).
5. **Set it down and nudge it:** it wobbles, eyes level, dizzy, then the smug look. This is the clip people post.
6. **Under the carton:**
   - the **birth certificate** (soul number, edition number if any, the name it asks you for, its first-boot date, „Proiectat în România", NFC + QR anti-fake);
   - the RO/EN quick guide (§3.8);
   - a braided cream USB-C cable (no charger, EU unbundling);
   - the **COCON** knit sleeve with its loop (§6);
   - one card: „Ridică-l: se uită. Ține-l: te ascultă. Închide oul: doarme." (Lift it: it looks. Hold it: it listens. Close the egg: it sleeps.)
7. **Pairing your Claude or ChatGPT is optional and comes later.** The OU replaces a moulded insert, so packaging is $2–3 at 10k.

## 6. Accessories (carry lives here, never on SOUL)
| Item | What | Price | Cost @10k |
|---|---|---|---|
| **COCON** (in the box) | The rule-3 carry. A 3D-knit recycled-PET/TPU pouch, heat-set to SOUL: wall 1.5–2 mm, inside = SOUL + 0.5 mm; **outside ≈ 67 W × 84 H × 31 D mm closed** (the flap adds ~8 mm over the crown), ≈ 9 g [E]. A fold-over flap closes front-to-back with 2 sewn-in Ø6 × 1.5 magnets; a woven loop, 8 × 45 mm, sits on the back seam at the top. SOUL goes in face-first. It sleeps inside, and **pulled out it opens its eyes** (ALS + IMU) | spare €19 | $1.5–2.5 |
| **Soles** ("Swap the sole, keep the soul") | contrast colours (**Jar/Ember**, cream, onyx), Mărțișor, collabs, "Anul 1" (earned), **HEAVY** tungsten (lower COM, livelier wobble), **LINIȘTE** still sole (a flat Ø26 foot for offices; OU seating to validate) | €24 (Founders aluminium €49) | $1.2–2.5 |
| **Cords** for the OU | braided nylon, veg-tan leather, Mărțișor red-white | €15–29 | $1–4 |
| **PUCK** travel charger | Ø36 × 10 zinc cup with the 5-pin socket on 1 m of USB-C (the STRAIE graft) | €19 | $2–3 |
| **CUIB** desk nest | slip-cast pearl porcelain, 320 g, 12° backrest, ID = desk mode (porcelain lives here, not in the box) | €39 | $4.5–8 |
| **OU+** | OU with a 1000 mAh cell | €59 | +$3–5 |
| Year 2 | **OU DUBLU** (two souls sleep side by side and sync their blinks); DROP "soft" and CLOUD art head shells on the same chassis and sole standard | — | shell tools $10–16k each |
Never: a loop on SOUL, a phone-charging pad, Bluetooth in any dock, paid blind boxes, plush or ears.

## 7. The two alternates (clearly weaker; show them to the founder side by side)
**ALT A: PIATRA + OU nest ("the still stone that turns to face you"; OU concept, fixed).**
- **Body:** 62 × 70 × 26 → 17 mm D-section wedge (front superellipse exponent 3.2, back 2.2); a Ø25 × 1.2 zinc hover foot with a shadow line and bullseye gold rings (rotation-invariant contacts; they fit because the foot is Ø25); 30 g zinc in the chin; 105 g; tip angle ≈ 25°.
- **Rule 2:** speaker slot 12 × 0.9 in the +x seam at z 44–56; mics Ø0.7 in the −x seam at z 48 and z 20. Nothing on the front.
- **Capsule:** a pearl-PC nest (porcelain only in the Bucovina art edition, judge 2) and a frosted borosilicate dome (Tritan fallback). **Spin-to-face** comes from a diametric magnet pair; it is R&D, with a keyed-sole fallback.
- **Fixes applied:**
  - The seam moves onto the silhouette, which removes the ~3 mm die-lock (judge 2).
  - A separate 300 g desk pad at 12–15° is added, because the spinning nest cannot have a backrest (judge 3).
  - A vented dome rim.
- **Why weaker:** all its wow happens at home; the egg-under-glass archetype is crowded (Tamagotchi, cloche); spin-to-face is unproven.
- **Why show it:** it is the calmest, best in the hand, most Apple-minimal and steadiest, and it has the best night photo.
- **Numbers:** housing ~$8.5, nest + dome $9.5–17 at 10k; tooling $55–97k.

**ALT B: MĂRGĂRITAR + SCRIN ("the jewel in its casket", fixed).**
- **Body:** 63 × 72 × 24 → 16 mm pebble (sits on a flat land); **flat Ø52 2.5D glass at launch**, with the domed cabochon later on the same seat (judge 2); R1 for standard, LAC for editions; a champagne zamak sole with a hallmark and a sealed, blanked USB-C; 108 g; tip angle ≈ 16°.
- **Rule 2:** speaker slot 12 × 0.9 in the +x girdle at z 42–54; mics Ø0.7 in the −x girdle at z 46 and z 20.
- **Capsule:** the SCRIN is a 285 g plinth with a lift-off Surlyn crystal lid (no hinge) that flips into a key bowl, with vent slits. Fix: **5 pins, not 3**, so USB data works.
- **Why weaker:** no act of its own (its optical parallax is weak on video); the jewel/perfume codes dilute *șmecher*; the least stable stance; a home-only casket.
- **Why show it:** the most premium still image and material story; gift economics; the Brâncuși ovoid lineage as a press-only story [V-c].

## 8. Deliberately rejected, and why
| Rejected | Why |
|---|---|
| Plain circle / coin without a bail (v3 LENS, ORB; v4 AMULET) | no up or down; the founder's "small ugly circle" |
| Flat pebble lying down (v2); necklace or bail | founder rules 3 and 6; reads as a remote |
| The 35 mm HOPA belly | not portable; the COM depends on height, not depth, so a 27 mm belly keeps the physics |
| Titanium or zirconia bodies, rotating bezel, halo ring (08) | $30–55 housing, CIM tooling, RF; a ring on the face. The premium material path that remains is the metal sole and a zirconia back edition (§9, "reads as plastic") |
| STRAIE swappable coats + VITRINA | phone-case read; circular gap set by a removable part; EEE coats; loot-box and DRM optics; two-tone back |
| ECLIPSA crystal foot, floating glass carrier, RAMPĂ RGB ring | trophy/riser read; brittle structural PMMA; conflicts with flush fit and IP seal; "gaming RGB"; a halo ring round the face |
| Domed cabochon at launch; clear-PC body as standard | touch through 2.5 mm glass unproven; UI shrinks to Ø38; worst cosmetic yield |
| Porcelain + blown glass in the box; spin-to-face in the final | fragility and reject rates; the elliptical rocker cup already self-aligns |
| Qi; a USB-C port on SOUL (unless forced); Bluetooth docks | coil does not fit the land, heat; a hole plus a lever; the Playdate dock lesson |
| LEDs on SOUL, camera, wake word, motors, real maglev | rule 1, trust, cost; Earnshaw [V-c] |
| Soft-touch PU; pastels (mint, blush, lilac); 1-in-20 chase coat | sticky within years; 2024 kawaii; loot-box law risk |
| The SoulOS mock-up's front grille | banned by rule 1; remove from every public image (r-trends) |
| The SoulOS mock-up's side button | **not banned by rule 1** (it is not on the front); left out of v1 by choice, with reset, power-off and the mic gate solved in §3.8; a flush back key is the founder option |

## 9. Risks and mitigations
| Risk | Mitigation / kill criterion |
|---|---|
| COM misses (now ≈ 23.8 with stepped steel; 24.3 with a flat plate) and nudges become falls | Week-1 mule: SLA body, mass dummies at the modelled centroids, the three ballasts of §3.4. Go: ≥ 4 visible swings, recovery ≥ 28° forward **and** back, no face-down fall from a 1 N flick at the crown. Fallback: W-Ni-Cu lower horseshoe (+$1.2–2.5) or all-W (+$3–5). |
| **Packaging does not close** (cell, stack, speaker, ballast are loft-model numbers) | Packaging CAD before EVT with the §3.4 sections; stack ≤ 6.5 mm confirmed from the panel drawing; custom 42-mm cell quoted (fallback 603040, ≈ 800 mAh). Kill: any section with < 0.5 mm cell clearance → narrower cell or thinner stack, never a thicker body. |
| Reads as a toy (Weebles), perception | 112 g, gloss, slow 1.7 Hz wobble, adult lids, chime off by default, 18+. Test 10 people aged 18–35: ≥ 60 % "cool", ≤ 10 % "childish". |
| **Classified as a toy** (regulatory): a toddler-toy archetype (Hopa-Mitică, Weebles), a cute face and N52 magnets; 03: foreseeable use decides, and dual-purpose products count | That would add the Toy Safety Directive (Regulation 2025/2509 from 1 Aug 2030), EN 71-1 magnet rules and EN 62115, and would make RED 3.3(e) apply on toy grounds too (03). Mitigation: adult desk-object positioning, no child play claims or child imagery, "Nu este o jucărie / not for children under 14" on the box, guide and listings (03), 18+ account, magnets fully encapsulated and passing EN 71-1-style torque/tension/drop abuse tests anyway, "Hopa-Mitică" used only as heritage. A written classification opinion from the lab before DVT. Kill: if the opinion says toy, redesign the claims or budget toy compliance before any preorder. |
| **Reads as plastic / not premium** (founder rule 5). 08: a PC shell "is the look the founder rejected" and PC is "detected by weight and temperature" | Weight: 112 g, low COM. Temperature: glass on the face; metal where the hand meets it underneath. Blind test on the looks-like set (Perlă R1 vs the KEEL variant vs a ceramic reference). **Kill: ≥ 3 of 10 (or the founder) say "plastic/cheap".** Fallback 1: r-cmf **R8 KEEL** champagne-anodised Al sole on every SKU (+$1.5–2.5 @10k; price stays €199 at ≥ 3 ×). Fallback 2: a zirconia back-shell "Heirloom" edition (08; CIM tooling, €449+). Fallback 3: Ø54 glass (§3.2). |
| EVE resemblance (white egg with black face) | Round glass, not a visor; cream eyes; the ember OU liner; launch Onix and Lapis beside Perlă; trade-dress search before the reveal. |
| **Trademark: "SOUL" in class 9** is crowded (e.g. the SOUL Electronics headphone brand [K]); 05's io/iyO lesson | Clearance search (EUIPO/TMview, WIPO, RO OSIM) by counsel **before** the EUIPO filings, the domain and any public use. Fallback: a compound mark (e.g. "SOUL by …", "OU") or a rename before the reveal. |
| Misleading origin claim | "Proiectat în România" on product, box and certificate; "Asamblat/Născut în România" only with contracted RO final assembly and a customs origin opinion (§3.3). |
| Desk touch rocks it | Talk = hand on its head (IMU-gated electrode); text in the hand or in the OU at 14°; test with first-time users. |
| Crown electrode false triggers when grabbed | Gate on IMU upright + still + 300 ms hold; check which Waveshare touch GPIOs are free (unknown [K]). |
| Sole wear, a "tick" on glass tables, the sole band on the front | Satin UV-coated sole, TPU land ring, the €24 sole is replaceable; tone-on-tone by default; founder check #1 for contrast and metal soles (§3.2). |
| Portability (27.1 mm, 112 g, above 06/08 thresholds) | Stated override (§3.1); COCON in the box; "hand, bag, jacket pocket", never "jeans pocket". **Kill:** the §3.1 hand-feel and carry test → SOUL-24. |
| **Dock yaw misalignment** (the socket allows 10–14°; Ø1.8 dots tolerated ±7–8°; TPU friction fights the magnets) | Arc pads (±24° [E]), low-friction POM-PTFE floor, magnets key 180°. Test: yaw-sweep drop-in ±20°, 500 random seats, 100 % contact, < 100 mΩ per pad. |
| **Sole-code sensing** (flux shunted by steel, swamped by the keying magnets; NTAG detuned by metal; no NFC reader in SOUL) | v1: an on-metal NTAG read by the phone. Hall codes are an EVT experiment only (Halls below the ballast at y ±11, pass ≥ 99.9 % reads, §3.3); otherwise dropped. |
| Pogo chatter, lift-out, OU tipping | 22 gf pins, magnets > springs, ≥ 0.8 N press spec, 10k seat cycles, salt fog + sweat bias on the pads. |
| OU hinge failure | Buy a TWS hinge module; 20k open/close cycles before steel. |
| Pearl flow/weld lines; Onyx shows every defect | Diaphragm gate, uniform 1.8 mm wall, RHCM-ready tools, Onix piano coat, AQL at 30 cm / 2 s. |
| Sound muffled in the hand; longer duct | Acoustic mule with 3 slot positions × hand/desk, with the real 6–8 mm duct; target ≥ 80 dB SPL at 10 cm (voice). |
| No physical mic gate in the hand | Stated in §3.8; hardware cut in the closed OU; founder option of a flush back key. |
| EU common charger (pogo = wired) | Document the primary use as "AI companion"; get a written ANCOM/RED-lab view before steel; keep a keep-out for a vertical sealed USB-C in the land module (fallback land, no body re-tool). |
| Compliance scope and cost (EN 18031, battery, GPSR, EPR, markings, AI disclosure) | Budget €30–80k (03); the markings and disclosure plan in §3.3 and §3.8; technical file started at EVT. |
| Air freight | Ship at ≤ 30 % SoC (IATA 2026 [V]); spare cells and OU+ the same; UN38.3 on the custom cell. |
| Single-source round 1.75" AMOLED | Qualify a second 466² panel before DVT (the OP-1 lesson [V-r icons]). |
| Magnets and ingestion; batteries | All magnets fully encapsulated; aged-cell testing before PVT (05). |
| 1k economics thin | Founders-only first drop at **€349** (€379 if RFQs land high); standard €199 and the LAC editions only on steel, from 5–10k (§3.7). |

## 10. Next steps
1. **Weeks 0–2, works-like mules:**
   - Physics mule (above): a mass/COM rig with the three ballasts, not a packaging proof.
   - **Packaging CAD** of the §3.4 stack, cell, speaker box, ballast and antenna, with sections at z 15/31/49/55 and x = ±25; the panel drawing and custom-cell quotes in hand.
   - Level-eyes, dizzy and smug firmware on the Waveshare board; film the 7-second clip.
   - Crown electrode.
   - OU force and tipping mule (printed cup, 22 gf pins, magnets).
   - Acoustic mule (real duct length); dock yaw-sweep rig; shipping-sleep µA measurement.
2. **Weeks 2–6, looks-like set.** Vapor-polished, painted SLA, each weighted to its target mass:
   - final design in Perlă, Onix and Lapis;
   - a 35 mm HOPA for comparison;
   - ALT A and ALT B in Perlă;
   - SOUL-24 and a ρ 2.0 control (§3.1), a KEEL-sole variant, and the pearl vs ember sole (founder check #1).
   Then a blind "want it / cool / premium / plastic?" ranking with 10 people, the §3.1 hand-feel and carry test, a founder review, and **a decision gate** (including the back-key option, §3.8).
3. **RFQs on one STEP file:**
   - **Moulding:** Rosti (Prahova) [V-r cmf], a Dongguan moulder (HLH / Star Rapid / Firstmold class [K]), a Portuguese toolmaker.
   - **Cover glass:** Hengping [V-r cmf], Saiwei [V-s r-cmf], Lens Technology / Biel [K]; the panel maker quotes the CTP/OCA lamination NRE.
   - **AMOLED:** VIEWE + a second source.
   - **Cell:** a custom 6.2 × 34 × 42 pouch + UN38.3 (2 cell makers).
   - **Pogo pins:** CFE [V-r dock], Promax [V-s r-cmf], Jiatel [V-r dock].
   - **Final assembly (Founders):** a Romanian EMS (05: Kimball, Helbako, Etron) vs Shenzhen.
   - **Parts:** TWS hinge modules; FR4 hard-gold coins (PCBWay/JLC); stepped steel ballast (MIM vs laser-cut stack) and a W-Ni-Cu quote.
   - **Soft goods and packaging:** knit sleeve; pulp.
   - **Other:** a certification lab; Roctool (RHCM).
4. **Legal:** **trademark clearance first**, then EUIPO filings for SOUL, OU and HOPA; an ANCOM letter; a toy-classification opinion; a customs origin opinion if RO assembly is chosen; the GPSR technical file and the RO/EN guide; the Soul Pledge (05, r-trends O9). A colour-on-sole mark only after use: Louboutin's EU case took until 2018 [V].
5. **Then EVT → DVT → PVT:** 16–30 weeks (05). No deposits before DVT.

## 11. Sources
- [V] fetched 2026-09-25 (rev.): https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/eurofxref-graph-usd.en.html (EUR/USD 1.1367 on 24 Sep 2026; 1.134–1.170 Jun–Sep 2026) · https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-guidance-document.pdf (2026 guidance: ≤ 30 % SoC mandatory for PI 966 from 1 Jan 2026, strongly recommended for PI 967)
- [V] fetched today: https://en.wikipedia.org/wiki/Roly-poly_toy (Hopa-mitică, Stehaufmännchen, okiagari-koboshi, COM principle) · https://en.wikipedia.org/wiki/Weebles (Playskool 1971, slogan) · https://en.wikipedia.org/wiki/Daruma_doll (eye ritual, nanakorobi yaoki) · https://en.wikipedia.org/wiki/Christian_Louboutin (red sole 1992/93, CJEU June 2018) · https://en.wikipedia.org/wiki/Superegg (Hein p = 2.5, stands upright) · https://en.wikipedia.org/wiki/European_Union_value_added_tax (RO 21 %) · https://en.wikipedia.org/wiki/Egg_decorating_in_Slavic_culture (RO *încondeiate*) · https://eur-lex.europa.eu/eli/reg/2023/1542/oj/eng (recital 38 "readily removable"; today's summaries of the Art. 11 date were inconsistent, so 18 Feb 2027 is taken from [V-03])
- [V-r]/[V-0x]: research 05–08 and design-max r-icons, r-creatures, r-dock, r-cmf, r-trends (their URL lists). [V-c]: concept authors' fetches (ESP32-S3 touch channels, rumanite, Brâncuși, Earnshaw, yūrei).
- [E]: every geometry, mass, COM, frequency, force and cost number in §3–§6, computed from the tables above (a loft + superellipse-section model; rigid-body rocking ω² = g(R − h)/(k² + h²)). Rev.: ember visibility is an orthographic ray-cast of the loft ∩ sole ellipsoid (0.5 × 0.02 mm grid); the sections, cell clearances and ballast volumes come from 2-D offsets of the same loft (1.8 mm wall, 1.4 mm sole). This is not a packaging CAD. The earlier ember and ballast-fit claims were corrected by an independent review ray-cast; my numbers agree with it within ≈ 0.2 mm.
