# Cheap-but-premium CMF & manufacturing for SOUL (2026-09-24)

Tags: **[V]** page fetched today (URL in §10) · **[V-s]** web-search summary today, page not opened · **[V-0x]** verified in note 0x · **[K]** background knowledge, verify before quoting · **[E]** estimate / engineering judgement.
Builds on 06 (board stack, BOM), 07 (caseback, battery), 08 (density, infinity glass, finish menu), `r-creatures` (upright pebble ≈ 60 W × 70 H mm, section 26 mm at the base → 16 mm at the top, base land 24–28 × 14–18 mm, 10–20 g ballast in the chin) and `r-icons` (Pearl / Onyx). Not repeated here.
**Hard rules applied:** front = body + screen only · speaker on the sides/back · charging contacts on the base + a SOUL capsule · no bail · stands upright · premium, not plastic-cheap · **housing ≤ $10/unit at 10k**.
**Consequence of rule 1:** the Ti/Al *bezel ring* from 08 is dead (it is a ring on the face). The highlight line must come from the glass edge and a polished lip on the shell. Metal moves to the base, where it pays (§1, R8).

---

## 0. The cheap architecture (what actually gets moulded) [E]
| Part | Material / process | Why |
|---|---|---|
| **Front shell** (face + upper flanks) | gloss PC or PC-skin (see recipes), ~2.0 mm wall, **diaphragm gate through the display window** (the window is moulded as a thin disc and punched/CNC'd out afterwards) | radial flow → **no weld line on the face** (a normal side gate splits around the Ø50 window and meets on the forehead: a dark line in pearl/metallic); the gate vestige hides under the glass |
| **Back shell** (back + chin) | same material, gated under the keel (hidden) | the speaker slot and mic holes sit near the gate, so their weld lines are short and hidden |
| **Inner chassis** | black PC-GF/PC-ABS, all the bosses, ribs, snaps, speaker box seat, antenna keep-out | cosmetic shells stay **rib-free** → no sink marks, no read-through on translucent skins |
| **Base keel** | zinc die-cast (7.1 g/cm³ [K]) or anodised Al | ballast (~15 g in a 30 × 18 × 4 mm plate), carries the charging pads + magnets, **is the battery door** (2 standard screws; Battery Reg. Art. 11 from 18 Feb 2027 [V-03]), carries the only logo |
| **Cover lens** | custom 2.5D glass Ø52–56 with black mask, or a plano-convex PMMA "cabochon" (§2) | the whole face |
Seams: 1 design seam (front/back shell on the side flank = where the speaker exits), 1 glass lip, 1 keel line underneath. No screws visible.

## 1. Process menu: look × cost × risk
| Process | What you get | Unit adder @10k [E] | Tooling / lead [V/E] | Watch-outs |
|---|---|---|---|---|
| **High-gloss moulded PC**, SPI A-1 (Ra 0.012–0.025 µm [V]) tool in NAK80 (38–42 HRC, mirror 10–12k mesh) or S136 (48–52 HRC, stainless) [V-s] | paint-free gloss | $0 (vs textured) | +polish 1–2 wk [E] | PC: low scratch resistance, yellows in UV unless stabilised/coated [V]; every sink/weld/gate mark shows |
| **Pearl pigment in a translucent resin** (mica + TiO₂/Fe₂O₃ platelets) | nacre depth, silky (fine 10–25 µm) or sparkle (coarse) [V] | +$0.03–0.10 material | none | pearl dies in opaque/filled resin (keep fillers < 1 % [V]); platelets orient at weld/flow lines → dark streaks; fix = single fan gate, uniform wall, mould 40–55 °C hotter than normal [V], gentle shear [V] |
| **Metallic flake (Al) "spray-free"** compounds | brushed/metal look without paint | +$0.05–0.15 | none | worst flow/weld-line contrast of all [V-s]; engineers "move flow lines into concealed areas" [V-s]. Only with RHCM or on weld-free geometry |
| **RHCM / induction heat-&-cool** (Roctool, FR) | eliminates weld lines, flow marks, sink; replication up to 97.2 % vs ~50 % [V] | +$0.05–0.15 (cycle) | +$4–8k per tool [E], licence | cycle can even drop (85 → 55 s demo [V]); worth it for pearl/metallic/black |
| **Two-shot (2K)** clear skin over opaque core | real "candy" depth: colour under a glassy skin | +$0.5–1.0/part | **$18–48k per part** vs $8.5–18k insert-overmould; 2K pays off from ~25k/yr [V] | 2K moulders: Rosti RO (Prahova) [V]; the skin must stay ≥ 0.8 mm for flow [E] |
| **Back-painted translucent shell** (ink/spray on the *inside*) | 80 % of the 2K depth at 20 % of the tooling | +$0.2–0.4 | spray masks $0.5–1k | the inner surface must be smooth (ribs on the chassis, not the shell) |
| **IMD** (roll-to-roll transfer: Kurz, Nissha) | printed gradient/metal/texture + UV hard coat in one shot, no paint [V] | +$0.3–0.8 | film MOQ; draw depth rarely > 6 mm [V-s] | our shells are ~10 mm deep → IMD only on a shallow back; deep = **IML/FIM** (print → form → trim → mould) [V] |
| **PC/PMMA composite film/sheet** (co-extruded, PMMA outside for hardness, PC inside for toughness; UV-transfer nano-texture → vacuum coat → print → high-pressure forming ~180 °C → CNC) [V/V-s] | "glasstic" phone-back depth: gradients, light-play textures (Galaxy S21's plastic back on a $799 flagship [V-s]) | +$0.8–1.6 as an IML insert | forming + trim tools $4–10k [E] | China suppliers: Kaixin, Dafu, OMAY [V-s]; 9H/AF claims are vendor claims [V] |
| **UV hard coat** (acrylate, spray 5–15 µm, 2–4 passes) [V-s] | gloss + scratch (phones need ≥ H pencil [V-s]) + hides micro-flaws + UV block | +$0.25–0.45/part | jigs | dust inclusions → 5–10 % rework [E]. **Yes to UV coat.** |
| **Soft-touch PU paint** | velvet | +$0.3–0.6 | — | **No.** PU hydrolyses → sticky, irreversible [V]; "usually sticky after ~10 years", faster in heat [V-s] |
| **TPSiV overmould** (silicone-TPV, bonds to PC) [V-s] | silky grip, hydrolysis-resistant [V-s] | +$0.3–0.7 | overmould tool $8.5–18k [V] | lint, jeans dye transfer on light colours [K]; base/case only |
| **Frosted texture** VDI 18–24 (Ra 0.8–1.6 µm; PC draft ≥ 1.0–1.5° [V]) | hides scratches/fingerprints/sink | $0, tool texture ~$0.5–1k [E] | +1 wk | opaque + matte = the rejected v2 look. Only on translucent (sea-glass) editions |
| **Vapor polishing** (PC, PMMA, PSU, ABS) [V] | clear gloss on CNC/SLA parts | $3–10 per proto part [E] | none | crazing → stress-relieve [V]. **Prototypes / looks-like only**; production gets gloss from the polished tool |
| **"Ceramic-look" PC**: opaque white PC + 2K/UV piano clear 20–30 µm, polished | porcelain/zirconia read at 1/10 the cost | +$0.5–1.0/part | paint line | fails the "cold + heavy" test (08) → rely on the keel's weight; yield 85–92 % [E] |
| **NCVM** (non-conductive vacuum metallisation, Sn/In islands + UV) [V-s] | chrome/champagne look that doesn't block RF | +$0.4–0.8 | jigs | for a metal-look keel or accents near the antenna |
| **Anodised Al** (CNC, bead-blast, diamond-cut chamfer) | cold, precise, "jewellery plinth" | keel $2.5–4.5 (vs zinc $1.0–2.0) | CNC fixtures $1–3k | never near the ESP32 antenna (top); pads isolated in a PC insert |
PC ≈ €2.6–2.8/kg, 1.20–1.22 g/cm³ [V] → a 9 g shell costs ~$0.03 of resin; **machine time, scrap and finishing are the real cost**, not material. Dry PC before moulding (splay [V]); 120 °C, 3–4 h [K].

## 2. The face: "body + screen", bezel-less
**Problem:** the Waveshare module has its own Ø48.96 cover glass over a Ø43.76 active area [V-06]. Any shell lip that stops at the module glass leaves a visible glass edge and a 2.6 mm dead ring.
| Option | Stack-up (top → down) | Look | Cost @10k [E] | Risks |
|---|---|---|---|---|
| **A · Infinity glass** (baseline) | 0.55–0.7 mm aluminosilicate Ø52–56, 2.5D edge, AR + AF, 2–3 layer black mask (OD ≥ 4, ink black matched to the AMOLED off-state) → OCA 0.1–0.2 mm → module glass (proto) or panel directly (production, panel-house lamination) | the eyes float in a Ø54 black disc; you can't see where the screen ends (08) | $1.8–3.0 glass ($1.5/pc ≥ 5k vs $4.5 at 200; < $3.5 with AR+AF at 15k/quarter [V-s]) + $0.3–0.6 lamination | never an air gap: each air/glass interface reflects ~4 %, so a gap adds ~8 % glare and greys the eyes [K/E, Fresnel]. Vendor samples 3 working days from drawing [V] |
| **B · Cabochon lens** (the wow option) | plano-convex PMMA ("hesalite" watch-crystal logic) Ø54, 1.5–2.5 mm sag, hard coat + AR; flat back OCA-laminated to the module glass; black mask printed on the flat back | eyes seem to sit *inside a drop*; slight magnification (~1.1–1.2× [E]) and a moving rim highlight = alive even when static | $0.5–1.2 (glass dome $3–8) | scratches, but polishes out (Speedmaster practice [V-s]); **touch through ~2.5–3.5 mm of dielectric**: CST9217 must be re-tuned, test first [E]; rim distortion hidden by the mask |
| **C · Full-face glass** | one shaped glass over the whole upper front, pearl-white back-print (3–5 white layers + backing [K]) around the black window | the SoulOS pebble look with one continuous glass skin | $3–6 | bigger glass = drop risk; white ink opacity and ±0.1 mm print registration |
Mounting: glass **flush ±0.1 mm** with the shell, 0.3–0.4 mm polished lip (the highlight line), 0.2–0.3 mm PSA ring that also seals (IP). No gasket visible. Recommendation: **A for launch, B prototyped in parallel** (it is the cheapest "innovation" on the list).

## 3. Speaker, mics, IP: a silent face, a voice from the side
| Option | How | Pros | Cons |
|---|---|---|---|
| **1 · "The seam sings"** (default) | 1511/1813 sealed box speaker in the chin; front chamber ≤ 0.15 cm³; exits through a 0.8–1.0 × 10–12 mm slot **hidden in the front/back shell seam** on one lower flank | invisible from the front; no grille; one line in the design does two jobs | seam tolerance becomes acoustic; one-sided sound |
| **2 · Back micro-perforation** | 40–80 laser-drilled holes Ø0.3 mm after moulding (no weld lines) in the lower back | invisible at arm's length | laser cost $0.1–0.2 [E]; holes collect lint |
| **3 · AirTag trick** | voice coil drives a magnet on the back shell, so the shell is the diaphragm; AirTag does this and is IP67 [V] | zero holes → IP67 almost free | quiet, weak below ~500 Hz, shell vibration leaks into the mics and makes AEC harder [E]. Experiment only |
| **4 · Chin underside** (down-forward, outside the base land) | slot under the chin | table boundary gain (~+3 dB half-space [K]); couples straight into the capsule | arguably "bottom" (the founder reserved the base for charging) → second choice |
**Acoustic numbers [E, from the Helmholtz formula f = (c/2π)·√(S / (l′·V)) [V-s]]:** slot 12 mm², front volume 0.10 cm³, 1.2 mm wall (l′ ≈ 4.5 mm with end corrections) → **f ≈ 8.9 kHz**, above the voice band ✔. The same speaker routed through an 8 mm duct to the seam (6 mm², 0.25 cm³) → **f ≈ 2.6 kHz**, a honky peak in the middle of speech ✗. Rules: duct ≤ 3 mm, slot ≥ 8–10 mm², front chamber ≤ 0.15 cm³, sealed box with its own back volume (never use the enclosure air: leaks, rattles, mic coupling) [K/E].
**Mics** (ES7210, 2 × MEMS [V-06]): Ø0.6–0.8 mm pinholes in the upper back seam, ≥ 40 mm from the speaker slot (AEC). **The capsule as a resonance chamber:** docked, the side slot lines up with a moulded throat in the capsule wall that curls into a forward-facing horn (mouth ~8 × 35 mm, 30–40 mm long). Retail horn stands claim +13–15 dB [V-s, marketing]; expect **+3–6 dB in the 1–5 kHz range** and no bass [E]. It costs ~$0 in tooling and lets SOUL "sing louder at home". A capsule with its own speaker (audio over 2 extra pogo pins) is a v2 option.
**IP:** launch at **IP54** (IP5X = dust-protected; IPX4 = splashes, 10 min [V]). Design for **IP67** (30 min at 1 m [V]): flush pads (no holes), glass PSA seal, seam gasket, keel O-ring, ePTFE vents on the mics (Gore GAW334: IP67/IP68 at 2 m for 1 h, < 2 dB loss at 1 kHz, 0.31 mm thick [V]) and the speaker (speaker membranes cost more dB [K]), plus 1 pressure vent. Adder for the IP67 path: +$0.4–0.9 [E].

## 4. Bottom charging + the capsule interface
- **Device side = pads, not pins:** 3 flush gold pads (V+, GND, ID), Ø2.5–3 mm, recessed 0.1–0.2 mm (so a table can't scratch or short them), hard gold over Ni [K], insert-moulded in a PC insulator inside the keel. No moving parts in the body, and it seals. Pogo vendors spec **IP67/IP68, no exposed holes when disconnected, 50k+ cycles, ~2 A** [V].
- **Capsule side = pogo pins:** 3 pins, 15–60 gf each [V-s], 1.0–1.5 mm working stroke [E], 10k–100k cycles [V-s]. Pins go **live only after an ID handshake**: no live pins on an empty dock, no electrolysis from sweat on undocked pads [E]. The device pads never carry voltage when undocked (disable PMU OTG, reverse-blocking path) [E]. USB-C lives in the capsule.
- **Magnets:** 2 × N52 Ø6 × 2 mm in the keel, opposite polarities = keyed (seats one way, snaps and self-aligns); matching magnets in the capsule. The QMI8658 is accel + gyro only, so there is no magnetometer to disturb [K]. Cost: pads + magnets $0.4–0.7 [E].
- **EU common charger risk:** USB-C is mandatory for *wired-charging* phones, tablets, cameras, headphones, headsets, **portable speakers**, consoles, e-readers, keyboards, mice, navigators, earbuds (laptops from 28 Apr 2026). Wireless-only devices and smartwatches/trackers are out of scope today [V]. Pogo charging is wired charging. An "AI companion" is not a listed category, but a market-surveillance authority could read it as a portable speaker [E]. → Write the classification rationale into the technical file and ask the RED lab. Fallback: a USB-C behind the keel/battery door (+$0.2–0.4), or Qi-only in v2 (+$3–5, heat in a sealed PC body [E], but out of scope).

## 5. Cosmetic defects → SOUL design rules
| Defect | Cause [V wiki unless tagged] | Rule for SOUL |
|---|---|---|
| Sink marks | thick sections, low hold pressure/time | no ribs/bosses on cosmetic shells (chassis carries them); where unavoidable, rib ≤ 40–50 % of the wall on gloss [K] |
| Weld/knit lines (+ pearl/metal flake lines) | flow fronts meet around holes | diaphragm gate through the window; holes near the gate or laser-drilled after moulding; RHCM on pearl/black [V] |
| Gate vestige, ejector marks | unavoidable, but they can be placed [V] | gates under the glass rim / keel; ejectors only on inner faces |
| Flow marks, jetting | slow injection; bad gate position [V] | fan gate into a wall, uniform 2.0 mm wall, no sudden thickness steps [V] |
| Splay / silver streaks | moisture in hygroscopic resin [V] | dryer log per lot (PC 120 °C, 3–4 h [K]) |
| Flash on the parting line | over-packing, damaged shut-off [V] | parting line inside the designed seam, never on a visible curve |
| Read-through | ribs/PCB visible through translucent walls [E] | opaque back-spray or 2K core; black chassis |
| Crazing / stress whitening | PC + solvents, stress [V] | PC-compatible PSAs/cleaners; no solvent bonding; stress-relieve vapor-polished protos [V] |
| Yellowing | UV on unstabilised PC [V] | UV-stabilised grade + UV hard coat, or a PMMA outer skin [K] (the Friend "yellowing white" lesson, 07) |
| Scratches/dust in coat | handling, paint booth | UV hard coat ≥ H [V-s], protective film in pack, clean-room paint line, AQL at 30 cm / 2 s viewing [K] |

## 6. Tooling, lead times, suppliers
- **China tool prices [V]:** prototype/bridge (Al or P20, ≤ 50k shots) $1–3k · low-volume P20, 1–2 cavities $2.5–8k · mid-volume 718H/H13 $5–15k+ · complex/precision (H13/S136) $20–80k. Chinese prices run 30–60 % below EU/US; the cheapest of 190 quotes was 30.8 % below the median [V]. Aluminium moulds: $2–5k for 1–5k units, 3–4 weeks; steel 4–8 weeks [V]. Modern Al tools can reach 100k+ shots [V].
- **Lead times [V]:** prototype tool 15–25 days · production tool 25–45 days · +1–2 weeks per T0/T1 correction loop · **first article 6–10 weeks by sea** (air 5–20 days). Add 1–2 weeks for A-1 polish or texture, +2–4 weeks for 2K, 4–8 weeks of IML film development [E].
- **Full SOUL tool set [E]:** 2 cosmetic shells (NAK80, A-1, diaphragm gate) $12–24k + chassis $3–5k + zinc keel die $3–6k + pad insert/fixtures $2–4k + glass screens/jigs $1–2k = **$21–41k China** (EU ≈ 1.4–2.5×). **1k strategy:** aluminium bridge tools for everything ≈ $10–18k, then steel at 5k+.
- **Materials:** pearl pigments: Susonity (ex-Merck Surface Solutions, Iriodin family, sold to China's GNMI, closed 31 Jul 2025) [V-s]; optical/pearl-ready PC: Covestro Makrolon, SABIC Lexan; Chinese spray-free compounds: Kingfa [K]. IMD/IML films: Kurz (DE) [K], Nissha (JP) [V]. Heat & cool: Roctool (Le Bourget-du-Lac, FR) [V].
- **China:** Dongguan/Shenzhen/Zhongshan moulders (e.g. HLH, Star Rapid, Firstmold [K]); cover glass: Hengping (0.33–5 mm, 2.5D/3D, black ink, AR/AF [V]), Saiwei [V-s], Lens Technology, Biel [K]; composite sheet: Kaixin, Dafu, OMAY [V-s].
- **Romania:** **Rosti** (Paulești, Prahova; 55+ presses, 2K/3K, insert, overmould, pad print, laser, assembly; appliances/power tools) [V] · **Nolato** (Ploiești; stack/cube high-cavitation, ISO 13485) [V] · **Plastor** (70 presses, 40–1300 tf, own mould shop) [V-s] · **PlasTec** (0.04–1000 g parts) [V-s] · **Mold Technology** (Cugir, mould maker) [V-s]. Assembly/EMS: see 05 (Kimball, Helbako, Etron).
- **EU tooling hub:** Portugal (Marinha Grande: ~250 mould companies; with Oliveira de Azeméis > 500 toolmakers and ~10.5k people; Iberomoldes exports 95 %) [V-s]. A common hybrid: tool built in China under Portuguese supervision (e.g. On-Time Moulds) [V-s].
- **Our play [E]:** China tools + China glass; mould in Romania (Rosti for 2K) or China. "Designed in Cluj, moulded in Prahova" is a story worth the +15–30 % per part at 1–5k.

## 7. Cost table (housing = shells + finish + chassis + glass + lamination + keel + pads/magnets + seals/acoustics + fasteners) [E]
Common core @10k: glass $1.8–3.0 · lamination $0.3–0.6 · chassis $0.2–0.35 · zinc keel incl. finish $1.0–2.0 · pads + magnets $0.4–0.7 · seals/mesh/vents/PSA $0.3–0.6 · screws $0.05–0.1 = **$4.1–7.4**. Scrap allowance is included in the shell figures.
| Recipe | Shells + finish @10k | **Housing @10k** | Housing @1k (bridge tools, small-lot glass) | Tooling (China) | ≤ $10? |
|---|---|---|---|---|---|
| R1 Nacre | $1.5–2.7 | **$5.6–10.1 (typ. ~7.5)** | $14–22 | $21–41k (+RHCM $4–8k) | ✔ |
| R2 Candy Pearl (2K) | $2.4–4.0 | **$6.5–11.4 (typ. ~8.5)** | $18–28 (2K bridge scarce → insert-overmould at 1k) | $45–110k (2K on the back only: $33–77k) | ✔ typ. |
| R3 Porcelain | $1.7–3.2 | **$5.8–10.6** | $15–24 | $22–43k | ✔ typ. |
| R4 Onyx | $1.5–2.5 | **$5.6–9.9** | $14–21 | $25–49k (with RHCM) | ✔ |
| R5 Aurora (IML) | $1.6–2.9 | **$5.7–10.3** | $17–27 (film MOQ) | $26–54k | ✔ typ. |
| R6 Ghost (frost) | $1.0–1.7 | **$5.1–9.1** | $12–19 | $19–37k | ✔ |
| R7 Silk-Base (R1 + TPSiV) | $1.8–3.4 | **$5.9–10.8** | $15–24 | $30–59k | ✔ typ. |
| R8 Keel (R1/R2 + anodised Al keel) | +$1.5–2.5 over R1 | **$7.1–12.6** | $20–30 | R1 + $1–3k fixtures, minus the zinc die | ✗ premium SKU |
Amortised tooling adds **$2–4/unit over 10k** (R1) and ~$10–18 over 1k with bridge tools. For comparison: 08's Ti housing was $35–55 @10k, and its Al version $12–20. **All plastic recipes beat Al on cost; weight and "tock" come from the zinc keel.**

## 8. Eight CMF recipes (name · stack-up outside → in · look · cost @10k housing)
1. **R1 · NACRE (hero Pearl)**: UV hard coat 10–15 µm gloss → 2.0 mm PC, UV-stabilised, 1–2 % fine silver-white pearl (10–25 µm), ≤ 0.3 % TiO₂ so it stays semi-translucent → inner back-spray warm white (#FFF6E6) → black chassis. SPI A-1 NAK80 tool, diaphragm gate, RHCM if flow lines show at T1. *Look:* a glossy pearl creature; the colour glows from 2 mm under the surface, porcelain-meets-pearl, never flat. **~$7.5**.
2. **R2 · CANDY PEARL (Founders)**: UV coat → 1.0–1.2 mm clear PC (or PMMA-rich alloy) skin with 0.5–1 % pearl + faint tint → 2K opaque core in cream or blush (carries snaps) → chassis. *Look:* hard-candy / Japanese-lacquer depth; highlights ride on the skin, colour floats beneath. Moulder: Rosti RO. **~$8.5**.
3. **R3 · PORCELAIN**: 20–30 µm UV/2K aliphatic piano clear, polished → opaque high-white PC (TiO₂ 3–5 %) → chassis. *Look:* white zirconia/porcelain like the SoulOS pebble; the cheapest "ceramic" read. Weakness: warm to the touch → the zinc keel carries the weight. **~$8**.
4. **R4 · ONYX**: AF + UV hard coat → jet-black PMMA/PC alloy (PMMA outside for scratch/gloss [V-s]) with an optional 0.1 % micro silver sparkle, RHCM (black shows every weld line) → chassis. *Look:* obsidian; body and black glass merge, so the eyes float in a black stone (soot-sprite read, r-creatures). **~$7.5**.
5. **R5 · AURORA (drops)**: IML film = hard coat / PMMA → printed gradient (pearl → blush, or pearl → lavender, like the v1 lineup halos) + NCVM shimmer → PC film, formed + trimmed → back-moulded PC. *Look:* soap-bubble/opal gradient that changes as you turn it; every season a new film, **same tools**. **~$8**.
6. **R6 · GHOST (limited)**: 2.0 mm translucent PC, exterior VDI 18 (Ra 0.8 µm, 1° draft [V]) or light bead texture, no coat → *designed* white inner chassis (no raw PCB visible). In the capsule, the capsule's light shines up through the base and the body glows softly (the face stays unlit). *Look:* sea glass, Nothing-style honesty. **~$7**.
7. **R7 · SILK-BASE**: R1 body + a TPSiV overmoulded foot/chin in a matching shade (non-sticky, hydrolysis-resistant [V-s], anti-slip for standing). *Look:* pearl top, velvet bottom, a creature "sitting". Keep it small (lint, dye transfer). **~$8**.
8. **R8 · KEEL (premium plinth)**: R1/R2 body + CNC 6063 Al keel, bead-blast, champagne or clear anodise, one diamond-cut chamfer; pads in a PC insert; laser-engraved soul no. and "born in Romania" underneath. NCVM plastic keel as the cheap look-alike. *Look:* a pearl sitting on a jewellery plinth; metal only where it touches the table, the capsule and your fingers underneath. **~$10–11**.

## 9. Recommendation [E]
- **Standard SKU:** R1 Nacre (Pearl) + R4 Onyx, zinc keel, infinity glass A, side-seam speaker, 3 flush pads, IP54 (IP67-ready). Housing **~$7–8 @10k**, tooling ~$25–45k.
- **Founders (numbered):** R2 Candy Pearl + R8 Al keel + cabochon lens B (if the touch test passes). ~$11–13.
- **Drops:** R5 Aurora films on the R1 tools (low risk, recurring revenue); R6 Ghost as a 500-unit collector run.
- **Never:** soft-touch PU paint, metal rings on the face, a visible grille, opaque matte bodies, unstabilised white PC.
- **Next 6 weeks:** (1) SLA + vapor-polished looks-like in R1/R3/R4, weighed to 90–100 g with lead shot; (2) laminate a Ø54 infinity glass and a PMMA cabochon onto the Waveshare module and test CST9217 touch + glare; (3) seam-slot vs micro-perforation acoustic mule, with and without a capsule horn (measure SPL at 50 cm); (4) quote Rosti (2K), one Dongguan moulder and a Portuguese toolmaker on the same STEP; (5) RED-lab opinion on the common-charger classification.

## 10. Sources (fetched 2026-09-24 unless [V-s])
- https://en.wikipedia.org/wiki/Injection_moulding [V] (defect table, Al vs steel, 2K) · https://en.wikipedia.org/wiki/In-mould_decoration [V] · https://en.wikipedia.org/wiki/Polycarbonate [V] · https://en.wikipedia.org/wiki/Vapor_polishing [V] · https://en.wikipedia.org/wiki/IP_code [V] · https://en.wikipedia.org/wiki/Optical_bonding [V] · https://en.wikipedia.org/wiki/IPhone_5C [V] (hard-coated PC + steel frame as antenna, 132 g, "not premium" criticism)
- https://formlabs.com/blog/injection-molding-cost/ [V] · https://www.haizol.com/blog/injection-molding-tooling-cost-china [V] · https://xinyangmfg.com/overmolding-cost-guide-startups/ [V] · https://hlhrapid.com/knowledge/injection-moulding-vdi-surface-finish/ [V]
- https://www.ptonline.com/articles/how-to-get-the-most-out-of-pearlescent-pigments [V] · https://www.roctool.com/technology/heat-cool-for-plastic-injection-molding/ [V] · https://connect.nissha.com/ime/en/decorative_molding/ [V] · https://www.allpcb.com/allelectrohub/composite-plastic-smartphone-back-cover-production-process [V]
- https://motleyscience.com/2024/12/19/sticky-plastics/ [V] · GORE GAW334 datasheet (groupgets-files.s3.amazonaws.com/AudioMoth/GORE-Acoustic-Vent-GAW334-Datasheet-en.pdf) [V] · https://www.ifixit.com/News/50145/airtag-teardown-part-one-yeah-this-tracks [V]
- https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/radio-equipment-directive-red/one-common-charging-solution-all_en [V] · https://cfeconn.com/pogo-pin-magnetic-charging-solution-for-smart-sports-watches/ [V] · https://hpcoverglass.com/applications/smart-watch-cover-glass/ [V]
- https://www.rosti.com/locations/europe/romania/ [V] · https://www.nolato.com/en/Group-companies/Nolato-Romania [V]
- [V-s] search summaries only: plasticsdecorating.com (IMD draw depth > 6 mm rare); S136/NAK80 steel pages (sositarmould, peifengmold); RHCM reviews (MDPI Materials 15/10/3725, Packson); flake-line research (PMC11768285, all-about-industries); NCVM (yajoy-technology); UV hard coat (patsnap/NEI); TPSiV (DuPont/specialchem); Galaxy S21 "glasstic" (digitaltrends, androidpolice); PC/PMMA sheet (kaixinfilm, dafufilm, pc-film.com); cover-glass prices (alibaba/accio/saiweiglass); pogo specs (promaxpogopin, vitalconn); horn stands (vat19, Amazon listings); watch crystals (bobswatches, fratellowatches); Helmholtz/front-cavity patents (USPTO 10299032); Merck → GNMI/Susonity (emdgroup.com 2025); Portugal moulds (moldmakingtechnology.com, Wikipedia Marinha Grande/Iberomoldes, ontime.pt); Plastor/PlasTec/Mold Technology (ensun.io, plastec-romania.ro, mould.ro).
- plastor.ro, the hpcoverglass black-mask guide, the digitaltrends glasstic page and the Nothing Ear (1) Wikipedia page failed to load → facts from them are [V-s] or [K].
- Not verified ([K]/[E]): all per-part costs and tooling totals for SOUL, the Helmholtz worked examples, cabochon magnification, touch-through-thickness limits, zinc density/keel mass, hard-gold thickness, PMMA vs PC pencil hardness, QMI8658 having no magnetometer, AQL viewing norms.
