# SOUL: final design (design-max synthesis, 2026-09-24)

Tags: **[V]** fetched today (URL in §11) · **[V-0x]/[V-r]** verified earlier today in note 0x / a `design-max/r-*` note · **[V-c]** fetched today by a concept author (not re-checked) · **[K]** background knowledge · **[E]** estimate or calculation (mine, from the mass/physics model in §3.4).
Inputs: notes 05–08, `design-max/r-icons, r-creatures, r-dock, r-cmf, r-trends`, five concepts (HOPA, MĂRGĂRITAR, ECLIPSA, STRAIE, OU), three judges, and the renders (v1 family, SoulOS pebble, v2/v3 rejects, v4 family/pebble/capsule/hand/scale).
Render brief: `design-max/render-brief.md`. **Nothing here has been built. Every mass, force, frequency and cost figure is [E] until a mule has been weighed and suppliers have quoted.**

---

## 0. Decision in one paragraph
**SOUL is an upright pearl roly-poly: 63 × 74 × 27 mm and 112 g.** It sits on a hidden rocker sole. Nudge it and it rocks back upright ("hopa!") while its eyes stay level, and a sliver of ember flashes underneath. The base concept is **HOPA**, the only one whose signature lives in the object itself: all three judges placed it first or second, and it has the best manufacturing base. Grafted onto it are OU's egg capsule and its name (*S-OU-L*: the capsule is an egg called **OU**, and every morning SOUL "hatches"), MĂRGĂRITAR's lacquer depth for editions, ECLIPSA's "zero LEDs on SOUL" rule and STRAIE's "it notices what it wears" idea. **We fixed HOPA's four flaws:**
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
3. **Helmet placement.** Glass centre at 54–56 % of height; forehead:chin 1:1.6–2.0; eye line at 47–52 %; glass = 52–62 % of the front (R3–R5, measured from the loved pebble).
4. **Cute in software, cool in hardware.** Lids level and 15–25 % lowered, V 8–12° (never ≥ 15°); a dense, glossy, mineral body; no props, fur, ears or pastels (R6, r-creatures §3).
5. **One signature act you can name in two words.** It is native to the shape and done by physics, not controls (L4, O1: "alive without motors").
6. **It feels fuller than it looks.** ρ ≥ 1.6 g/cm³, zero creak, a dull "tock" when tapped, one precise line (L8, 08 §1).
7. **One colour code, ownable at 3 m.** Cream #FFF0C8 eyes floating in black glass on pearl, plus exactly one hidden accent (L3, r-trends O4).
8. **Show the soul, never the circuit. SOUL has zero LEDs;** its only light is its eyes, and every other photon comes from its home (L7, ECLIPSA).
9. **The home is half the product.** The capsule is charger, bed, stage, travel case, packaging and the only place for a loop. State is shown as light, and the docking sound is the logo (L5, L6, r-dock §2).
10. **The first minute is a birth, and a daily ritual sells the second unit.** Lift, hold, put to bed, hatch (L11, L12).
11. **Trust you can hold.** No camera, hold-to-talk only, deaf in its egg, alive offline, your own Claude or ChatGPT, and an open-firmware pledge (r-trends O2, O9).
12. **Withered tech, frozen interfaces, cheap tools.** ESP32-S3 + 1.75" AMOLED; one sole/contact standard for 10 years; every colour on the same tools; housing ≤ $10 at 10k; the round panel dual-sourced (L10, r-dock, r-cmf).

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
- Below z 6.3 the outline *is* the lateral rocker, an arc of R40 about (0, 39.4) that the table clips into a flat land 13.8 mm wide.

**Side (front line y_f, back line y_b):**
| z | 1.9 | 4.5 | 8 | 14 | 23 | 34 | **40.5** | 48 | 55.5 | 60 | 66 | 69.5 | 73.2 | 74 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| y_f | −12.5 | −13.8 | −14.4 | −14.2 | −13.1 | −11.5 | **−10.6** | −9.6 | −8.5 | −7.9 | −7.0 | −5.9 | −2.8 | −1.0 |
| y_b | +12.0 | +12.7 | +12.7 | +11.8 | +10.4 | +9.6 | **+9.4** | +8.7 | +7.6 | +6.7 | +4.6 | +2.7 | −0.1 | −1.0 |
- The face plane leans back **8°**: y_f = −10.6 + 0.1405·(z − 40.5) for z 15–66. The eyes therefore meet a seated gaze, and the wedge makes the crown thin.
- **From the side it reads as a seed or bean sitting on its belly**: the mass is low and the chin is tucked under.
- **From the top it is a D shape.** The front 36 % of the depth is a flat "table" around the glass that rolls into the flanks with a quarter-superellipse of about 5 × 7 mm; the back 64 % is a full dome (superellipse exponent 2.2).
- **Volume ≈ 68 cm³** [E, numerical loft].

### 3.2 Face: body and glass only
- **Infinity glass:** Ø52.0 × 0.7 mm aluminosilicate, 2.5D edge, AR + AF coatings, 3-layer black mask (OD ≥ 4) outside the Ø43.76 active area, with the ink matched to the panel's off-black. It is OCA-laminated with no air gap and sits flush ±0.1 mm in a flat Ø52.3 table with a 0.15 mm shadow gap.
- **No polished ring.** The v4 hairline ring is deleted: it was a ring on the face.
- **Glass position:**
  - Centre at z 40.5 (**54.7 %**), top edge at z 66.2, bottom edge at z 14.8.
  - Forehead 7.8 mm, chin 14.8 mm (**1 : 1.9**, the loved pebble's ratio); side margin 5.5 mm.
  - The glass covers **52 %** of the front silhouette (4,055 mm²), at the low end of R3, exactly like the loved pebble.
- **Eyes** (the eyes.py defaults already match the loved ones):
  - Each eye is about 30.8 % of the active diameter tall (13.5 mm, 143 px) and 10.5 mm wide; centres ±8.3 mm apart; eye line at z ≈ 38.1 (**51.5 %**).
  - Default lids are lowered 19 % with a 9.2° V.
  - Every eye has a catchlight (no pupil-less stare).
- **Proximity/ALS sensor** (940 nm, LTR-553 class) sits behind an IR-ink window at 12 o'clock inside the mask, invisible. It gives the approach glance, first-light wake and pocket detection.
- Seam lines: none visible from the front (the shell seam is on the silhouette, §3.3). **At table level the ember sole shows as a ≤ 1 mm line at the chin; from 15° or more above the desk it is hidden** [E, projected geometry]. This is **founder check #1**. If he reads it as a front detail, the Perlă SKU ships with a pearl sole and ember becomes an accessory sole.

### 3.3 Sides, back, bottom
- **Shell seam = the girdle.** The front and back shells meet in a 0.2 × 0.2 mm V-line at the widest-X line of every section (y_s = y_f + 0.36·depth, about 7–8 mm behind the face plane). It sits on the silhouette, so there are **no undercuts or slides** (judge 2), and it gives a tactile "which way is up" line (judge 3, MĂRGĂRITAR).
- **Speaker:** a 12 × 0.9 mm slot (about 11 mm²) in the seam on the **+x upper flank, z 46–58**, above the belly the fingers wrap (judge 3's fix). Behind it: a sealed 1813 box (0.7–1 W, its own back volume), a front chamber ≤ 0.12 cm³, a duct ≤ 3 mm and an ePTFE vent. Helmholtz peak ≈ 8–9 kHz, above the voice band [E, r-cmf formula]. The slot is edge-on and invisible from the front.
- **Mics:** 2 × MEMS (ES7210) behind Ø0.7 pinholes in the −x seam at z 50 and z 22. They sit about 62–66 mm from the speaker for echo cancellation [E] and have ePTFE vents.
- **Back:** one blank, glossy, convex dome with no text, screws or port.
- **Crown:** a capacitive electrode (a 20 × 10 mm LDS pad under the shell) on an ESP32-S3 touch channel [V-c]. It powers "hand on its head", gated by the IMU (upright and still) and a 300 ms hold.
- **Bottom = the land plus the SOLE:**
  - **Land** (part of the sealed body): a flat Ø13.8 mm spot where the rocker ellipsoid meets the table. It carries an FR4 coin with **5 hard-gold pads** (Ø1.8, 0.76 µm Au over Ni, in a cross: VBUS · GND · D+ · D− · AUX).
    - The pads are recessed 0.15 mm inside a 0.2 mm clear TPU perimeter ring. They never touch the table, and the ring keeps SOUL silent on glass (the MĂRGĂRITAR graft).
    - 2 × N52 Ø5 × 2 keying magnets of opposite polarity sit at x = ±9 under the sole skin.
    - The pads stay dead unless docked (PMU OTG off, reverse-blocking FET).
  - **Sole** (cosmetic and swappable): a 1.4 mm PC skin, about 45 × 24.5 mm in plan, covering the whole rolling surface up to its rim. The rim is at z ≈ 1.9 front, 1.6 back and 7 at the sides. **So the rocker never rolls over a seam** (judge 2).
    - Satin-gloss with a UV hard coat, which hides rolling scuffs better than an A-1 finish.
    - Held by 2 × Torx T5 M1.6 **into tapped steel ballast**, so nothing strips (judge 2).
    - Carries an NTAG213 tag and 2 moulded-in Ø3 × 1 "code" magnets read by 2 Hall sensors: 9 codes, so **SOUL knows which sole it wears** (the STRAIE graft; no electronics in the sole, so no EEE burden).
    - Laser ring around the land: "SOUL · Nº 0001 · NĂSCUT ÎN ROMÂNIA", the only text on the object.
  - **Battery access** (EU Battery Regulation Art. 11: a "readily removable" battery, using commercially available tools and no heat or solvents [V]; applies from 18 Feb 2027 [V-03]): 2 × T5 remove the sole, 2 more T5 screws into brass inserts release the back shell, and the cell comes out on a pull tab and connector.

### 3.4 Inside, mass and stance
| Part | g | z (mm) | Note |
|---|---|---|---|
| Glass Ø52 + OCA · AMOLED + touch · PCBA + shield | 3.8 · 6.0 · 9.0 | 40.5 | custom PCBA behind the panel (Waveshare board in works-like mules) |
| Cell 1000 mAh 523450 (5.2 × 34 × 50) standing, z 15–49 | 19.5 | 31 | behind the lower half of the board; swell allowance 0.5 mm |
| 1813 speaker box · LRA Ø8 | 2.6 · 1.4 | 16 · 12 | chin |
| Shells R1, 1.8 mm wall | 16.4 | 36 | 7,575 mm² of shell [E] |
| Chassis PC-GF · mics/flex/seals/screws/NFC | 5.5 · 3.0 | 32 · 40 | |
| Land module · sole | 2.2 · 3.2 | 1–3 | |
| **Ballast: steel plate 27 g (5 mm, z 1.5–6.5) + chin block 13 g** | **40** | 4.6 · 9.5 | laser-cut, zinc-plated, **bolted to the chassis**, trimmed 2–3 mm rearward |
| **Total** | **≈ 112 ± 5** | **COM z ≈ 23 (31 %)** | ρ ≈ 1.65 g/cm³ (iPhone 2007: 1.66 [V-08]) |

**Rocker physics** [E, small-angle rigid-body model]:
- **Curvature centres:** z 33.3 fore-aft and z 39.4 sideways. Stability margins above the COM are 10.3 and 16.4 mm.
- **Stays still, then rocks.** It stands dead still on the land up to 0.0072 N·m (≈ 0.18 N at the glass centre). Typing on the desk does not move it; a finger nudge does.
- **Rocking frequency:** ≈ 1.75 Hz fore-aft and ≈ 2.0 Hz sideways, i.e. slow and heavy, not bouncy.
- **Recovery:** from ≈ 31° forward, 29° back and 50° sideways. The pure rolling arc reaches 20° fore-aft and 34° sideways, after which it pivots on the sole rim.
- **A hard flick lays it on its back**: it "plays dead". It never falls on its face, as long as the rebound (about 0.7 of each swing) stays under 31° (prove on hardware).
- **Target 4–6 visible swings.** Damping is tuned by the sole finish (satin PC vs a 0.5 mm TPSiV skin), measured on the mule.
- **Honest limit:** free-standing, a 0.2 N touch on the glass rocks it. Touch-typing, notes and approvals happen in the hand or in the OU (§4). On the desk you talk with a hand on its head.

### 3.5 The signature: "HOPA. Împinge-l. Se ridică." (Nudge it. It gets back up.)
- **The act:** nudge, poke or flick it. It rocks, swings back through upright and settles in about 3 s. **Through all of it the eyes stay level with the horizon.** The gyro counter-rotates them with a 70 ms lag, as if they were floating in liquid. Then comes a 300 ms dizzy flutter, and it settles into a half-lidded, unimpressed side-glance. On each swing a sliver of ember sole flashes at the chin. No motor and no added part: geometry, 40 g of steel and the IMU already on the board.
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
  - "It notices" a new sole: eyes look down, blink, look back up, and a sole-specific catchlight tint follows.
  - An optional roly-poly chime per swing, off by default.

### 3.6 CMF recipe, colourways, editions
- **R1 NACRE (standard):**
  - Stack, outside to in: a 10–15 µm UV hard coat (≥ H) → 1.8 mm UV-stabilised semi-translucent PC (Makrolon/Lexan optical grade) with 1–2 % fine 10–25 µm silver-white pearl and ≤ 0.3 % TiO₂ → a warm-white back-spray #FFF6E6 → a black PC-GF chassis carrying every rib and boss.
  - Tooling: NAK80 polished to SPI A-1. The front shell is filled through a **diaphragm gate across the glass window** (no weld line on the forehead) and the back shell is gated under the sole. The mould runs 40–55 °C hotter than normal, with RHCM held in reserve [V-r cmf].
  - The window's cut edge sits under a black PSA ring, so it cannot light-pipe (judge 2's ring-on-the-face warning).
- **LAC (lacquer depth, editions only; the MĂRGĂRITAR graft):** 2.0 mm water-clear tinted PC with 0.3–0.5 % pearl, no TiO₂, and a 3-layer inside spray (pearl-mica → colour → black blocker), window and seam edges masked. Budget 8–15 % scrap, acceptable at 500–2,000 units.
- **R4 ONYX:** jet-black PMMA/PC alloy, with RHCM mandatory. **R6 GHOST:** VDI 18 frosted smoke PC over a designed pearl "heart" plate, never a raw PCB.
- **Never:** soft-touch PU (hydrolyses and goes sticky), pastels, metal on the face, unstabilised white PC, or a gold SKU.

| # | Colourway | Body | Sole (the flash) | OU (cup / liner / lid) | Run |
|---|---|---|---|---|---|
| 1 | **PERLĂ** (hero) | R1, L* ≥ 90, C* ≤ 5 | **Jar/Ember #D8572A** | pearl / ember / frosted pearl | permanent |
| 2 | **ONIX** | R4 #0A0A0B, so face and body merge (a soot sprite) | Cream #FFF0C8, the eye colour | onyx / cream / smoke | permanent |
| 3 | **LAPIS** | LAC ultramarine (targeting WGSN/Coloro 2027 Luminous Blue [V-r trends], also nazar blue), silver pearl, sparse gold flecks | pearl | pearl / lapis / frosted | **launch edition Nº 0001–2000, then retired** |
| 4 | **CHIHLIMBAR** | LAC honey → cognac over gold pearl (Romanian rumanite amber [V-c]) | onyx | onyx / amber / smoke | timed 8-week drop, S/S 2027 |
| 5 | **FUM** (ghost) | R6 frosted smoke over a pearl heart plate | frosted clear "glow" sole: in the OU the floor light passes through it | smoke | 500 numbered, **sold, not a chase** |
**Limited editions:**
- **FOUNDERS Nº 0001–1000**: LAC "Candy Pearl" body, a champagne-anodised aluminium sole with a laser hallmark and the number, a numbered OU with a veg-tan leather cord, a signed birth certificate; #0001–0010 auctioned (05).
- **MĂRȚIȘOR sole**: white with a red thread line, every 1 March, sold as a gift.
- **"ANUL 1" sole**: earned only by souls with ≥ 300 awake days, via a device-signed attestation (the STRAIE graft).
- **OU BUCOVINA**: 10 capsules hand-painted by Romanian egg painters (*ouă încondeiate* [V]) for launch press, auctioned.
Run sizes are published and colours are retired for good. The personality is never blind-boxed.

### 3.7 Cost (USD, China tools, ex-works) [E; r-cmf, r-dock and concept figures, re-costed]
| Line | @1k (aluminium bridge tools) | @10k (steel) |
|---|---|---|
| Shells R1 incl. UV coat and back-spray | 5–8 | 1.5–2.7 |
| Chassis · Ø52 glass AR/AF/mask · lamination | 1–2 · 4–5 · 0.8–1.2 | 0.2–0.35 · 1.8–3.0 · 0.3–0.6 |
| Steel ballast (2 parts, tapped) · land module (FR4 coin, carrier, O-ring, 2 × N52, TPU ring) | 0.6–1.0 · 1.0–1.8 | 0.25–0.45 · 0.4–0.8 |
| Sole cap (2-cavity, UV coat, code magnets, NTAG) · crown electrode | 1.5–2.5 · 0.2–0.4 | 0.4–0.8 · 0.05–0.15 |
| Seals, seam gasket, PSA, 3 ePTFE vents · 4 screws + 2 inserts · cosmetic scrap | 1–1.5 · 0.2–0.4 · 1–2 | 0.3–0.6 · 0.1–0.2 · 0.3–0.6 |
| **Housing** | **16–26 (typ. ~21)** | **5.6–10.3 (typ. ~8)** ✔ ≤ $10 |
| PCBA incl. round AMOLED + touch, ESP32-S3 N16R8, ES8311/ES7210 + 2 mics, AXP2101, RTC, IMU, 2 Hall, ALS/prox, LRA driver, amp | 26–36 | 17–24 |
| Cell 1000 mAh + PCM · 1813 speaker + LRA · assembly, programming, test | 2.5–3.5 · 2.2–3.5 · 6–9 | 1.8–2.5 · 1.4–2.3 · 3–4.5 |
| **SOUL device** | **53–78** | **29–44** |
| OU capsule (§4) · COCON knit sleeve · box, pulp carton, cable, birth card, NFC · 3 % warranty reserve | 15–24 · 2.5–4 · 3–5 · 3–4 | 8–12 · 1.5–2.5 · 2–3 · 1.5–2 |
| **System COGS** | **≈ $77–115, typ. $94 (≈ €86)** | **≈ $42–63, typ. $52 (≈ €48)** |
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
| RHCM reserve | $4–8k |
| End-of-line fixtures (rock rig, pogo cycling, acoustic, RF) | $4–7k |
| Pulp, box dies, knit programming | $3–5k |
| **Total** | **≈ $53–90k (€49–83k)** |
- **Aluminium bridge set for EVT → Founders 1k:** $20–32k. Steel comes in at 5k+.
- **Total tool spend by 10k units:** about $73–122k, inside the €50–150k budget.
- **Other NRE:** PCBA design $15–30k; certification (CE/RED, EMC, LVD/62368, UN38.3, RoHS) $15–40k (05).
- **Price** (incl. 21 % RO VAT [V]; €1 ≈ $1.09 [K]; rule ≥ 2.5 × landed, 05):
  - **Founders €299** (1k): 2.4–2.7 × landed. Raise to €329 if RFQs land at the top of the range.
  - **Standard Perlă/Onix €199 including the OU and sleeve**, only at ≥ 5–10k: ~3.1 ×. At 1k it would be 1.8 ×, so **the first 1,000 are Founders only**.
  - Lapis / Chihlimbar €229; Fum €279.

## 4. The capsule: OU (the egg; *S·OU·L*)
- **Form:** closed, it is a flattened Piet Hein-style superegg with the broad end down (the grounded opposite of SOUL's broad-up head): **77 W × 88 H × 42 D mm, ≈ 150 g.**
  - Outline exponent 2.7 above the waist and 3.5 below; widest at z 32; stands on a flat 56 × 31 mm base land. Supereggs "can stand upright on a flat surface" [V].
  - Tilted parting line: z 18 at the front, z 48 at the back. Stainless hinge pin at the back at z 48, with a detent at 100°.
  - Open, the lid stands behind SOUL like the top half of a shell. SOUL's face and head stay fully free (the cup rim is at least 3 mm below the glass).
- **Parts:**
  - Outer cup in the body colour.
  - Inner liner in the sole colour: "pearl outside, ember inside".
  - Frosted PC lid (VDI 18 inside, gloss outside, UV coat). For Founders, a numbered lid and leather cord.
  - A 60 g steel base plate biased 3 mm forward.
  - A TPSiV rim ring and 3 lid bumps.
  - A **recessed stainless bar in the hinge knuckle: the only loop in the system** (rule 3).
- **Socket:** SOUL's own sole ellipsoid (R40 × R36.9) offset by 0.5 mm, with a Ø15 flat floor at z 9, **tilted 6° back** so the face sits at 8 + 6 = **14°**, the desk angle judge 3 asked for. The back wall of the cup takes glass presses, so SOUL is **touchable hands-free** here. Spec: a **≥ 0.8 N press at the glass centre does not tip the OU**; capacitive holds need 0.1–0.5 N [E]. Drop SOUL in roughly: the round belly self-centres, the ellipse turns it to face out, and keyed magnets repel it if it goes in backwards.
- **Force balance (fixes judge 3's pin–magnet conflict)** [E]:
  - Pins: 5 low-force pogo pins at 22 gf and 0.8 mm working stroke, ≈ 1.1 N up in total.
  - Magnets: 2 pairs (SOUL Ø5 × 2, OU Ø6 × 2, N52, gap ≤ 2.2 mm), ≈ 1.2–1.6 N down; SOUL's weight adds 1.1 N down.
  - Result: seated net ≈ 1.4 N down, and lifting SOUL out needs only ≈ 0.3 N more than its weight, so the 150 g OU stays on the table.
  - Pins go live only after a Hall sensor sees SOUL **and** the AUX ID reads correctly: no sweat corrosion, no key or coin shorts [V-r dock].
- **Electronics** (no radio, no battery in the standard OU):
  - USB-C at the back, under the hinge.
  - A ~$0.15–0.3 MCU (CH32V003 class [K]), 2 Hall sensors (SOUL, lid), a load switch and ESD protection.
  - 6 × 2200 K LEDs under the cup rim, aimed at the inside of the lid, **never at SOUL's face**, plus a 1 mm base slit that washes the table.
  - D+/D− pass through, so the OU is also a USB port (flashing, recovery, the Claude Desktop buddy tether).
  - An ID resistor tells SOUL "bedside" or "desk".
- **The halo line** (fixes the alarm heard through a closed lid): closed, the lid rests on 3 bumps and leaves a 0.6 mm gap all round the parting line. Sound escapes (≈ −6 dB versus open [E]), and at night the gap glows as a thin warm line, which is the night light.
- **Ritual:**
  - **Bed:** drop SOUL in and it lands with a "tok" and a 2-note chime; the eyes check the bed, then look at you. At bedtime it yawns and its lids close over 4 s. The lid glow fades like a candle over 60–90 s, or holds at 1–3 % amber.
  - **Close the egg:** a clack. The lid Hall pulls AUX and SOUL's mic supply is cut **in hardware**: „În ou nu aude." (In the egg it cannot hear.)
  - **Night:** a tap on the egg brightens the halo line for 2 s. Open it and the time shows in dim amber for 2 s; there is never a static clock (burn-in).
  - **Sunrise:** starting 20 minutes before the alarm, the egg brightens from inside, 0 → 100 % warm white (Hatch logic [V-r dock]). Sound comes only if needed.
  - **Hatch:** open the lid and the eyes open and look up at you. **The alarm stops only when you lift SOUL out**, and the "Azi" (Today) card appears.
  - **Day:** lid open at 14°: hold-to-talk, Claude approvals through the USB tether.
- **Cost:**
  - Per unit: **$8–12 at 10k** (judge 2's figure: cup + liner $1.2–2, lid $0.6–1, hinge module $0.6–1, steel $0.2–0.35, PCB/pins/LEDs $2.2–3.5, magnets/rim/foot $0.4–0.7, assembly $1.2–2) and **$15–24 at 1k**.
  - Tooling $16–26k.
  - Buy a proven TWS-case hinge module rather than designing one, with a **20k-cycle test before steel**.
  - Retail: spare €49; OU+ with a 1000 mAh cell (about one extra charge, needs UN38.3) €59.

## 5. Unboxing (a birth, built for a 7-second vertical clip)
1. **Sleeve:** 118 × 78 × 150 mm, uncoated cream FSC board. The only mark is two cream hot-foiled eye ovals; the spine reads "SOUL". A hand-numbered paper seal (Nº 0417). The sleeve slides up slowly, like lifting a cloche.
2. **Inside:** a single-cell **moulded-pulp egg carton** (the OU joke, judge 1) holding the OU upright, cord loop up. A card: „Împinge-l ușor. / Nudge it."
3. **Thumb the lid open.** Light reaches the ALS and SOUL wakes from ship mode (≥ 60 % charged, µA drain). **The eyes open for the first time over 1.2 s, blink twice and look up into the phone camera.** No app, account or Wi-Fi.
4. **Lift it out:** the eyes widen within 100 ms. First line: „Hopa. Deci tu ești." ("Oh. So it's you.")
5. **Set it down and nudge it:** it wobbles, eyes level, dizzy, then the smug look. This is the clip people post.
6. **Under the carton:**
   - the **birth certificate** (soul number, the name it asks you for, „Născut în România", NFC + QR anti-fake);
   - a braided cream USB-C cable (no charger, EU unbundling);
   - the **COCON** knit sleeve with its loop;
   - one card: „Ridică-l: se uită. Ține-l: te ascultă. Închide oul: doarme." (Lift it: it looks. Hold it: it listens. Close the egg: it sleeps.)
7. **Pairing your Claude or ChatGPT is optional and comes later.** The OU replaces a moulded insert, so packaging is $2–3 at 10k.

## 6. Accessories (carry lives here, never on SOUL)
| Item | What | Price | Cost @10k |
|---|---|---|---|
| **COCON** (in the box) | 3D-knit recycled-PET/TPU sleeve, heat-set to SOUL, woven loop, magnetic flap; it sleeps inside, and **pulled out it opens its eyes** | spare €19 | $1.5–2.5 |
| **Soles** ("Swap the sole, keep the soul") | colours, Mărțișor, collabs, "Anul 1" (earned), **HEAVY** tungsten (lower COM, livelier wobble), **LINIȘTE** still sole (a flat Ø26 foot for offices; OU seating to validate) | €24 (Founders aluminium €49) | $1.2–2.5 |
| **Cords** for the OU | braided nylon, veg-tan leather, Mărțișor red-white | €15–29 | $1–4 |
| **PUCK** travel charger | Ø36 × 10 zinc cup with the 5-pin socket on 1 m of USB-C (the STRAIE graft) | €19 | $2–3 |
| **CUIB** desk nest | slip-cast pearl porcelain, 320 g, 12° backrest, ID = desk mode (porcelain lives here, not in the box) | €39 | $4.5–8 |
| **OU+** | OU with a 1000 mAh cell | €59 | +$3–5 |
| Year 2 | **OU DUBLU** (two souls sleep side by side and sync their blinks); DROP "soft" and CLOUD art head shells on the same chassis and sole standard | — | shell tools $10–16k each |
Never: a loop on SOUL, a phone-charging pad, Bluetooth in any dock, paid blind boxes, plush or ears.

## 7. The two alternates (clearly weaker; show them to the founder side by side)
**ALT A: PIATRA + OU nest ("the still stone that turns to face you"; OU concept, fixed).**
- **Body:** 62 × 70 × 26 → 17 mm D-section wedge (front superellipse exponent 3.2, back 2.2); a Ø25 × 1.2 zinc hover foot with a shadow line and bullseye gold rings; 30 g zinc in the chin; 105 g; tip angle ≈ 25°.
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
- **Capsule:** the SCRIN is a 285 g plinth with a lift-off Surlyn crystal lid (no hinge) that flips into a key bowl, with vent slits. Fix: **5 pins, not 3**, so USB data works.
- **Why weaker:** no act of its own (its optical parallax is weak on video); the jewel/perfume codes dilute *șmecher*; the least stable stance; a home-only casket.
- **Why show it:** the most premium still image and material story; gift economics; the Brâncuși ovoid lineage as a press-only story [V-c].

## 8. Deliberately rejected, and why
| Rejected | Why |
|---|---|
| Plain circle / coin without a bail (v3 LENS, ORB; v4 AMULET) | no up or down; the founder's "small ugly circle" |
| Flat pebble lying down (v2); necklace or bail | founder rules 3 and 6; reads as a remote |
| The 35 mm HOPA belly | not portable; the COM depends on height, not depth, so a 27 mm belly keeps the physics |
| Titanium or zirconia bodies, rotating bezel, halo ring (08) | $30–55 housing, CIM tooling, RF; a ring on the face |
| STRAIE swappable coats + VITRINA | phone-case read; circular gap set by a removable part; EEE coats; loot-box and DRM optics; two-tone back |
| ECLIPSA crystal foot, floating glass carrier, RAMPĂ RGB ring | trophy/riser read; brittle structural PMMA; conflicts with flush fit and IP seal; "gaming RGB"; a halo ring round the face |
| Domed cabochon at launch; clear-PC body as standard | touch through 2.5 mm glass unproven; UI shrinks to Ø38; worst cosmetic yield |
| Porcelain + blown glass in the box; spin-to-face in the final | fragility and reject rates; the elliptical rocker cup already self-aligns |
| Qi; a USB-C port on SOUL (unless forced); Bluetooth docks | coil does not fit the land, heat; a hole plus a lever; the Playdate dock lesson |
| LEDs on SOUL, camera, wake word, motors, real maglev | rule 1, trust, cost; Earnshaw [V-c] |
| Soft-touch PU; pastels (mint, blush, lilac); 1-in-20 chase coat | sticky within years; 2024 kawaii; loot-box law risk |
| The SoulOS mock-up's front grille and side button | banned by rule 1; remove from every public image (r-trends) |

## 9. Risks and mitigations
| Risk | Mitigation / kill criterion |
|---|---|
| COM misses 23 mm (panel and glass sit high) and nudges become falls | Week-1 mule: SLA body, Waveshare board, dummy cell, 32/40/48 g steel. Go: ≥ 4 visible swings, recovery ≥ 28° forward, no face-down fall from a 1 N flick at the crown. Fallback: tungsten chin block (+$1–2). |
| Reads as a toy (Weebles) | 112 g, gloss, slow 1.75 Hz wobble, adult lids, chime off by default, 18+. Test 10 people aged 18–35: ≥ 60 % "cool", ≤ 10 % "childish". |
| EVE resemblance (white egg with black face) | Round glass, not a visor; cream eyes; the ember sole; launch Onix and Lapis beside Perlă; trade-dress search before the reveal. |
| Desk touch rocks it | Talk = hand on its head (IMU-gated electrode); text in the hand or in the OU at 14°; test with first-time users. |
| Crown electrode false triggers when grabbed | Gate on IMU upright + still + 300 ms hold; check which Waveshare touch GPIOs are free (unknown [K]). |
| Sole wear, a "tick" on glass tables, the ember hairline | Satin UV-coated sole, TPU land ring, the €24 sole is replaceable; founder check #1 (pearl-sole fallback). |
| Portability (27 mm, 112 g) | COCON sleeve in the box; market it as "goes in your bag", never "pocket". |
| Pogo chatter, lift-out, OU tipping | 22 gf pins, magnets > springs, ≥ 0.8 N press spec, 10k seat cycles, salt fog + sweat bias on the pads. |
| OU hinge failure | Buy a TWS hinge module; 20k open/close cycles before steel. |
| Pearl flow/weld lines; Onyx shows every defect | Diaphragm gate, uniform 1.8 mm wall, RHCM reserve, AQL at 30 cm / 2 s. |
| Sound muffled in the hand | Acoustic mule with 3 slot positions × hand/desk; target ≥ 80 dB SPL at 10 cm (voice). |
| EU common charger (pogo = wired) | Document the primary use as "AI companion"; get a written ANCOM/RED-lab view before steel; keep a keep-out for a vertical sealed USB-C in the land module (fallback land, no body re-tool). |
| Single-source round 1.75" AMOLED | Qualify a second 466² panel before DVT (the OP-1 lesson [V-r icons]). |
| Magnets and ingestion; batteries | All magnets fully encapsulated; aged-cell testing before PVT (05). |
| 1k economics thin | Founders-only first run at €299–329; standard €199 only from 5–10k. |

## 10. Next steps
1. **Weeks 0–2, works-like mules:**
   - Physics mule (above).
   - Level-eyes, dizzy and smug firmware on the Waveshare board; film the 7-second clip.
   - Crown electrode.
   - OU force and tipping mule (printed cup, 22 gf pins, magnets).
   - Acoustic mule.
2. **Weeks 2–6, looks-like set.** Vapor-polished, painted SLA, each weighted to its target mass:
   - final design in Perlă, Onix and Lapis;
   - a 35 mm HOPA for comparison;
   - ALT A and ALT B in Perlă.
   Then a blind "want it / cool / premium" ranking with 10 people, a founder review, and **a decision gate**.
3. **RFQs on one STEP file:**
   - **Moulding:** Rosti (Prahova) [V-r cmf], a Dongguan moulder (HLH / Star Rapid / Firstmold class [K]), a Portuguese toolmaker.
   - **Cover glass:** Hengping, Saiwei, Lens/Biel.
   - **AMOLED:** VIEWE + a second source.
   - **Pogo pins:** CFE, Promax, Jiatel.
   - **Parts:** TWS hinge modules; FR4 hard-gold coins (PCBWay/JLC); laser-cut steel.
   - **Soft goods and packaging:** knit sleeve; pulp.
   - **Other:** a certification lab; Roctool (RHCM).
4. **Legal:** EUIPO filings for SOUL, OU and HOPA; an ANCOM letter; the Soul Pledge (05, r-trends O9). A colour-on-sole mark only after use: Louboutin's EU case took until 2018 [V].
5. **Then EVT → DVT → PVT:** 16–30 weeks (05). No deposits before DVT.

## 11. Sources
- [V] fetched today: https://en.wikipedia.org/wiki/Roly-poly_toy (Hopa-mitică, Stehaufmännchen, okiagari-koboshi, COM principle) · https://en.wikipedia.org/wiki/Weebles (Playskool 1971, slogan) · https://en.wikipedia.org/wiki/Daruma_doll (eye ritual, nanakorobi yaoki) · https://en.wikipedia.org/wiki/Christian_Louboutin (red sole 1992/93, CJEU June 2018) · https://en.wikipedia.org/wiki/Superegg (Hein p = 2.5, stands upright) · https://en.wikipedia.org/wiki/European_Union_value_added_tax (RO 21 %) · https://en.wikipedia.org/wiki/Egg_decorating_in_Slavic_culture (RO *încondeiate*) · https://eur-lex.europa.eu/eli/reg/2023/1542/oj/eng (recital 38 "readily removable"; today's summaries of the Art. 11 date were inconsistent, so 18 Feb 2027 is taken from [V-03])
- [V-r]/[V-0x]: research 05–08 and design-max r-icons, r-creatures, r-dock, r-cmf, r-trends (their URL lists). [V-c]: concept authors' fetches (ESP32-S3 touch channels, rumanite, Brâncuși, Earnshaw, yūrei).
- [E]: every geometry, mass, COM, frequency, force and cost number in §3–§6, computed today from the tables above (a loft + superellipse-section model; rigid-body rocking ω² = g(R − h)/(k² + h²)).
