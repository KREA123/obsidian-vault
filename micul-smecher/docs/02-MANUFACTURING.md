# 02 · Manufacturing dossier

*SOUL package · 25 Sep 2026, size S since 22 Oct 2026 (product S, prototype M). Sources: [`size-s.json`](size-s.json) + [`12-SIZE-S.md`](12-SIZE-S.md) (the S numbers; they win over anything below), `renders/v6/README.md` (CMF), `research/10-carcasa-aluminiu.md` (aluminium route, suppliers, costs), `research/09-product-design-max-2026-09-24.md` (OU, markings, tests), `prototip/cad/soul_p0_s.py` (the buildable S-P0), `prototip/cad/soul_p0.py` (the M kit), `blueprints/final/`. Tags: **[V]** verified, **[E]** estimate, **[GAP]** missing today.*

## 1. Which design gets built

| Design | What | Size | Status |
|---|---|---|---|
| **SOUL S** (the product; decision 20 Oct 2026) | MĂRGĂRITAR at its design scale: aluminium upright pebble, flat foot, 1.75" AMOLED 466² behind flat black glass Ø52 | **63 × 70.8 × 23.0 mm** (`size-s.json`) | **Renders** (`renders/v10/`) + GA drawing (`blueprints/final/soul_s_1_general_arrangement*`). No production CAD at 23.0 mm yet: the shape is `renders/v9/src/marg_geo.py` (MargaritarV9, s_back 0.807); stack-up and battery in `12-SIZE-S.md` §2. |
| **SOUL S-P0** (DIY pilot of S) | The MĂRGĂRITAR S outline around the **stock Waveshare ESP32-S3-Touch-AMOLED-1.75** and its stock glass (Ø48.96) | **63 × 70.8 × 25.65 mm** (uncompressed back: the stock 8.7 mm board stack + a cell only fit at that depth) | **CAD exported** (`prototip/cad/soul_p0_s.py`; `prototip/stl/s/`, `prototip/step/s/`, plastic shells). Cell: a 503030 class, ~450 mAh [E], in both `size-s.json` and the CAD (the 503035 first planned does not fit beside the USB-C tunnel; see the script header). |
| **SOUL M** (the working prototype) | MĂRGĂRITAR × 1.43 around the Waveshare 2.8C (2.8" IPS 480²) | design 90 × 101 × 31.5; DIY P0-M kit 112.1 × 125.1 × 31.6 mm | For tests and the PoC TRL 3 proof only (`prototip/README.md`, `renders/v9/`). |
| Founders 00 (25 units) | Historical plan (= P0 in aluminium). The current sale is a waitlist from €249, no Founders edition (`site/README.md`) | – | Not planned |
| Older concepts | `prototip/legacy-S/` (the HOPA S P0: ≈ 63 × 75 × 29.5 mm), `cad/` (OpenSCAD: coin, drop, gem and cloud for the 1.43/1.75 boards), `blueprints/` rev A (the oval v2), `blueprints/v3`, `renders/v6` (HOPA S, ≈ 63 × 72.2 × 27) | – | **Reference only. Do not send these to a supplier.** |

**Size: decided (20 Oct 2026, `03 Decizii/Jurnal decizii.md`).** S (1.75" AMOLED) is the product; M (2.8" IPS, Waveshare 2.8C) stays the prototype. The size study is in [`research/12-ecran-mai-mare.md`](../research/12-ecran-mai-mare.md) and `renders/v7/`; the S numbers (stack-up, battery, CNC, cost delta vs M) are in [`12-SIZE-S.md`](12-SIZE-S.md). The process sections below were written for the old HOPA S and still apply to S; where a number is size-specific, `size-s.json` wins.

## 2. CAD / STL / STEP files, and which to send where

| File (path in the vault) | Format | Send to | Purpose |
|---|---|---|---|
| `prototip/stl/s/soul_s_p0_plastic_{front_shell,back_shell,chassis,pin_pwr,pin_boot}.stl` | STL, already in print pose | **Home FDM / Bambu** (fit test), then an **SLA print shop** (looks-like) | **S-P0**, plastic, 2.0 mm walls, M2 inserts, 62.96 × 70.8 × 25.65 mm. Assembly note in `prototip/stl/s/README.md` (RO); all parts in place in `prototip/stl/s/assembly/` |
| `prototip/step/s/soul_s_p0_plastic_*.step.gz` | STEP (gzip; run `gunzip` first) | Print shops; **reference geometry for the CNC RFQ** | S-P0 shells, chassis, pins. The S-P0 aluminium variant is **not exported yet** (`python3 prototip/cad/soul_p0_s.py alu`) **[GAP]** |
| `blueprints/final/soul_s_1_general_arrangement*.{png,svg}`, `soul_s_2_p0_kit.*` | A3 drawings | CNC and glass suppliers (with the RFQ), you | GA of the product S (63 × 70.8 × 23.0, glass Ø52) and the dimensioned S-P0 kit |
| `prototip/cad/report_s_plastic.json` | JSON | You | S-P0 interference and clearance checks (60 pairs; min. gaps 0.17–0.53 mm) |
| **Production S body, 23.0 mm** (custom glass Ø52, own PCB, 750 mAh) | STEP | CNC (the RFQ), CAM simulation | **[GAP]** not drawn yet: `renders/v9/src/marg_geo.py` `MargaritarV9(s_back=0.807)` + a chassis for the custom stack (`12-SIZE-S.md` §4.7). Until then, quote the S-P0 STEP and ask how the price changes at 23 mm |
| `prototip/stl/plastic/soul_m_plastic_*.stl`, `prototip/{stl,step}/alu/soul_m_alu_*` | STL / STEP | Print shop (M kit only) | **M prototype** kit around the 2.8C (112.1 × 125.1 × 31.6 mm), for tests and TRL 3. Drawings `blueprints/final/soul_m_*`. **Not the product: never send it as the SOUL RFQ** |
| `prototip/legacy-S/`, `cad/stl/ms175_*.stl`, `blueprints/` rev A + `v3` | various | Nobody | Older HOPA S kit and concept shells. Legacy |
| `renders/v10/src/soul_v10.py`, `renders/v9/src/marg_geo.py` | Python (Blender / geometry) | Nobody | Source of the S look and of the MĂRGĂRITAR outline |

**RFQ settings for the CNC shells (paste into every quote form):**
- Material **Al 6061-T6**, 2 parts (front, back). Quantities to quote: **2 / 10 / 25 / 30**. Size **S**: attach the S-P0 STEP + the S GA drawing and ask for the 23.0 mm delta. Planning numbers [E]: billet **0.4 kg/set**, cycle **~24 min/set** (M: 1.0 kg, 45 min; `size-s.json` `cnc`).
- Surface: **bead-blast (glass bead, fine, ~50 µm), then anodise type II, coloured + sealed**, 10–25 µm.
- **Re-cut the 45° chamfer (0.45 mm) around the glass seat after blasting and before anodising**, so it comes out bright and satin.
- Tolerance: ISO 2768-m general, **±0.05 mm on the glass seat and the seam faces**.
- No threads in the aluminium, except the tapped M2 in the `alu` variant (or ask for M2 helicoils).
- Glass seat for the product: **flat Ø52 × 0.7 mm 2.5D cover glass**, 45° chamfer seat [E] (S-P0: the stock Ø48.96 board glass under a lip).
- **Mask** a Ø3 spot inside each shell from anodising, for the ESD ground contact.
- One anodise bath for the whole lot, a **physical golden sample before the run**, and 20 % spare sets.
- Laser marking on the base, if the supplier offers it (see §6).
- Ask for DHL Express, DAP, and a correct customs description: "housing for electronic device", not "aluminium article" (7616 99 90 carries anti-dumping risk).

**3D-print settings:**
- **FDM fit test:** PETG, 0.2 mm layers, 3 perimeters, 20 % gyroid infill, supports only on the glass lip. Tolerance 0.3 mm (the CAD uses 0.2).
- **SLA:** Tough 2000 / grey or black standard resin, 50 µm layers, supports off the cosmetic faces. The chassis in black.
- **MJF:** PA12, dyed black, then vapour-smoothed if you can.
- **Looks-like finish:** sand 400 → 800, filler primer, then metallic silver or Cerakote (20–30 µm). Cerakote is the best "fake metal" (research/10 §1.1 c2).

## 3. Materials and finishes per colour (from `renders/v6/README.md`)

**Body:**
- Material: **Al 6061-T6**, finely and evenly bead-blasted (glass bead ≈ 50 µm), **anodise type II, coloured and sealed**.
- **Base plate and foot:** PC/ABS with VDI 27 texture, in the body's tone. It is the only non-metal part and also the antenna window. For the pilot, print it SLA/MJF and paint it matte in tone.
- The **chamfer** is cut after blasting and anodised with the part, so it keeps the colour but reads satin-glossy with circular tool marks.

| Colour (EN / RO) | Aluminium (sRGB) | Base plate + foot, polymer (sRGB) | Anodise risk [V research/10] |
|---|---|---|---|
| **Natural silver / Argint natural** | `#CBCDCF` | `#B4B6B8` | Most stable. **Default for the first S units.** |
| **Graphite / Grafit** | `#55575B` | `#3C3E41` | Stable. Black/grey inorganic dyes resist UV. **Second launch colour.** |
| **Night blue / Albastru noapte** | `#26324C` | `#1D2435` | Blue fades under UV. Later edition, with a golden sample. |
| **Ember / Jar** | `#D2622C` | `#A44A22` | Orange is process-sensitive and varies between suppliers. Sample first. |
| **Champagne / Șampanie** | `#D8C3A2` | `#BDAA8A` | Gold/champagne is process-sensitive. Sample first. |

Rules:
- One alloy, one supplier and one bath per colour.
- Never mix 6061 and 6063 in one colour.
- Approve the golden sample under D65 light.
- Edges R ≥ 0.5 mm, or the anodise chips.

## 4. Tolerances and fits

| Feature | S-P0 plastic | S-P0 alu | Product S target |
|---|---|---|---|
| Wall | 2.0 mm | 1.4 mm (1.0 at the crown for mass) | 1.4 mm alu (counted 1.6 along the ray; `12-SIZE-S.md` §2.2) |
| Fit clearance to the board and glass | 0.2 mm | 0.1 mm | – |
| Glass lip overlap | 1.2 mm thick, 1.5 mm over | 0.8 mm thick, 1.5 mm over (covers the dead ring of the stock Ø48.96 glass) | Ø52 custom glass, 45° × 0.45 chamfer |
| Screws | 2 × M2×12 + 2 × M2×8 into brass heat-set inserts | M2 tapped (Ø1.6 pilot, 4.5 deep) | 2 × Torx T5 in the foot |
| Seam | planar parting plane (no undercut, 3-axis machinable) | same; optional 3 mm plastic band | belt seam on the silhouette |
| Speaker slot | 1.2 mm slot, z 45.5–57.5, in the +x seam | same | 12 × 0.6 mm laser slot, z 46–58 |
| Mics | – | – | 2 × Ø0.7 holes in the −x seam |
| General | ISO 2768-m | ISO 2768-m, ±0.05 on the seat and seam | – |

**UNVERIFIED — measure with calipers before the final print** (marked in `soul_p0_s.py`):
- the USB-C cable overmould (12.4 × 7.0 assumed);
- the mated MX1.25 plug height (SPK plug gap 0.17 mm in the CAD);
- the real 503030-class cell with its PCM;
- the kit speaker (the chassis frame is 15 × 11);
- the PWR/BOOT key travel.

## 5. Suppliers (online + Romania) and order settings

Full contact table: [06-SUPPLIERS](06-SUPPLIERS.md). Short list:

| Job | Online (CN) | Online (EU) | Romania |
|---|---|---|---|
| CNC shells + blast + anodise | **JLCCNC**, **PCBWay**, RapidDirect | **Weerg** (Venice, 2-day), Xometry EU, Hubs, Protolabs | **ARSAT** (Pecica, Arad: ~100 CNC machines, anodising, blasting), **Alvi Technik** (Cluj), Rombis, KlassCNC, cnc-3d.ro |
| SLA / MJF prints | **JLC3DP**, PCBWay | Craftcloud (marketplace), Weerg, Protolabs | local print shops; Alvi Technik (Stratasys F370) |
| Cerakote / paint | – | – | Cerakote applicators (auto/gun shops) [K] |
| PCB coin (contacts) | **JLCPCB** (ENIG / hard gold) | – | – |
| Electronics | Waveshare, AliExpress, LCSC | Eckstein (DE), Botland (PL), Mouser, TME | Robofun, Optimus Digital |
| Box, certificate, guide | – | – | Bucharest print shop (tipografie), quote rigid box at 25–50 |

Rules:
- Send the **same STEP to 5–7 CNC shops** for 2 / 10 / 25 / 30 sets, in natural silver and graphite. That gives you a real quote table in 24 h.
- China: 7–12 days plus DHL 3–5 days. EU: 3–10 days, no customs.
- Romania: you see the part and the bath, but ask for a "cosmetic sample", because few local shops do fine 3D work plus coloured cosmetic anodising.

## 6. Assembly sequence (S-P0 / a first S batch, per unit, ~2–3 h at first, ~45 min in series)

The step-by-step for the printed S-P0 (RO) is `prototip/stl/s/README.md`; the M kit has its own in `prototip/README.md`.

1. **Incoming check:**
   - shells: colour against the golden sample, no dents, the chamfer bright, the seat and seam within tolerance;
   - board: boots, and the `i` IMU readout is sane;
   - cell: voltage 3.7–3.9 V, no swelling.
2. **Flash the board before assembly:** `pio run -e amoled175 -t upload`, then serial `?`. Check the panel orientation, touch and IMU (see [03-SOFTWARE](03-SOFTWARE.md) §1).
3. **Plastic variant:** press 4 M2 brass inserts into the front bosses with the iron at ~220 °C (PETG/SLA), flush. **Alu:** check the tapped holes with an M2 screw.
4. Put the **board** with its stock glass face-down into the front shell's glass seat. The glass sits on the lip, and the USB-C lines up with its opening.
5. Place the **PWR/BOOT pins** in their guides and check that both keys click.
6. Connect the **speaker** (MX1.25) and lay it on the PCB back, membrane toward the back shell. Kapton over the wires.
7. Stick the **foam pad** on the chassis. Plug in the **cell** (check polarity!) and seat it on the foam. **No glue on the cell.**
8. Place the **printed chassis** over the board. Its legs are clamped by the 2 lower screws.
9. Optional: glue **2 × Ø6×2 magnets** into the base recesses (polarity mark), and the pogo male with its leads.
10. Close with the **back shell** (with the seam band in `alu_band`). **4 × M2**: the 2 lower through the chassis legs, the 2 upper straight into the front. Use a length ≤ `screw_len_max` from `prototip/CHECKS.txt`, and torque by hand (~0.15 N·m).
11. **Serial number:** write Nº on the certificate and in firmware NVS (planned). The base carries the laser mark.
12. Run the QC below, charge to ≤ 30 % for shipping (IATA PI 967), and pack.

## 7. QC checklist (every unit)

- [ ] Visual: no dents or scratches > 0.3 mm, colour matches the golden sample under D65, the seam gap is even (≤ 0.1 mm step), screws are flush.
- [ ] Mass on a 0.1 g scale, recorded (S-P0 alu ≈ 90 g, product S ≈ 85 g, range 75–95 g [E], `size-s.json`).
- [ ] Boot: eyes appear, and the panel is not shifted 6 px (SH8601 vs CO5300).
- [ ] Touch: tap = boop, double tap = laugh, hold 1.2 s = approve. Test all 4 quadrants.
- [ ] IMU: pick-up wakes it, face-down sleeps it, shake makes it dizzy.
- [ ] Audio: the speaker plays a chime, and the 2 mics record (ES8311/ES7210, when the S audio driver exists).
- [ ] Buttons: PWR and BOOT click through the pins.
- [ ] Battery: charges over USB-C, the charge current is ≤ 0.5 C (AXP2101 set by firmware), and the cell is ≤ 45 °C after 30 min.
- [ ] RF: BLE RSSI at 1 m and 5 m against a reference board, logged; loss ≤ 6 dB. Claude Desktop Buddy pairs with the 6-digit code.
- [ ] Standalone stability: SOUL stands upright on the flat foot, and a 1 N flick at the crown does not tip it (the S base is ≈ 38 × 16 mm [E]: test it on the S-P0, `12-SIZE-S.md` §4.6).
- [ ] 10-minute burn-in in demo mode (`D`), with no reboot.
- [ ] Base marking legible: Nº, CE, WEEE bin, battery symbol.
- [ ] Record serial, colour, mass, RSSI and firmware version in the batch sheet (GPSR traceability, 10 years).

## 8. Packaging

- **Sleeve:** 118 × 78 × 150 mm, uncoated cream FSC board. Front: two hot-foiled cream eye ovals. Spine: "SOUL". Hand-numbered paper seal "Nº 0xx" (research/09 §5).
- **Inside:**
  - SOUL in the OU (or in a moulded pulp / foam cradle for the pilot);
  - the birth certificate;
  - the RO/EN quick guide;
  - a braided USB-C cable (no charger);
  - the "Nudge it" card.
- **Back panel (legal set):**
  - model, serial/batch, CE, WEEE bin, battery data (Li-ion 3.7 V, Wh);
  - manufacturer name + postal and e-mail address (ARTEMIS DIGITAL S.R.L.);
  - QR to the DoC and the guide;
  - „Companion AI: vorbești cu o inteligență artificială, nu cu un om.";
  - „Nu este o jucărie. Nu este destinat copiilor sub 14 ani. Conține magneți.";
  - "Proiectat în România" + the true country of manufacture.
- **Shipping:** ≤ 30 % state of charge, UN3481 PI 967 Section II. Use DHL/UPS/FedEx or RO couriers by road. Not Deutsche Post or Poste Italiane.

## 9. The OU capsule

- **Design (research/09 §4):**
  - a superegg 77 W × 88 H × 42 D mm, ≈ 150 g;
  - cup + liner + frosted lid on a stainless hinge pin (detent at 100°);
  - a 60 g steel base plate;
  - a socket tilted 6° back, so the face sits at 14°;
  - 5 low-force pogo pins + 2 magnet pairs;
  - USB-C at the back;
  - a small MCU + 2 Hall sensors (SOUL present, lid) + 6 × 2200 K LEDs aimed at the lid;
  - lid closed = the mic is cut in hardware.
- **Pilot version:** SLA cup, lid and liner (painted; lid in clear resin with a matte coat), a steel washer stack for mass, a USB-C breakout feeding the pogo female, and 2 magnets.
  - Leave out the MCU, Hall sensors and LEDs in P0, or use a simple always-on 2200 K LED strip.
  - €30–55 per unit (BOM P0-13/14).
- **Files:** **[GAP]** there is no OU CAD yet (only renders: `renders/v6/soul_v6_ou_night.png`, `renders/v5/soul_v5_ou_*.png`).
- **At volume:** tooling $16–26k, $8–12 per unit at 10k. Buy a proven TWS-case hinge module and run a 20k-cycle test.

## 10. Marking on the base (laser, from `renders/v6/src/tex_v6.py`)

- Line 1: `SOUL · Nº 00417 · PROIECTAT ÎN ROMÂNIA` (the Nº is the unit's serial).
- Legal line: model (e.g. SOUL S / S-P0), batch, `ARTEMIS DIGITAL S.R.L., <address>, <e-mail>`, `Made in <country>`.
- Symbols: **CE**, **WEEE crossed-out wheelie bin** (EN 50419), the **battery** symbol / "Li-ion" with voltage and Wh, and the separate-collection bin for batteries (required since 18 Aug 2025).
- Minimum symbol height: CE ≥ 5 mm (proportional). If the base is too small, the CE and WEEE marks may go on the packaging and in the manual, but put them on the product whenever there is room.
- The polymer base plate can be laser-marked or pad-printed. On anodised aluminium, laser-mark after anodising for a white or dark mark.

## 11. What changes at 1k and 10k

| | First S batch (25; ex Founders 00, none planned) | 1k | 10k |
|---|---|---|---|
| Body | S-P0 alu: CNC 6061, 2 shells, China/EU (25.65 mm) | CNC 6061 in China, $25–45/set, fixtures only | **Deep-drawn 5052 shells + CNC finish + blast + anodise**, $9–14/set; tools $20–45k (research/10 §2) |
| Board | Waveshare ESP32-S3-Touch-AMOLED-1.75 stock | **Custom PCB with ESP32-S3-WROOM-1** (reuses Espressif radio evidence), PCBA design $15–30k | same, at an EMS (Seeed Fusion / PCBWay, or final assembly in RO: Kimball, Helbako, Etron) |
| Glass | stock Ø48.96 | custom Ø52 cover lens + lamination ($5–15k NRE) | same |
| Cell | S-P0: stock-class 503030, ≈ 450 mAh [E] (`size-s.json`; the 503035 first planned does not fit beside the USB-C tunnel) | **LiPo 603040, 750 mAh** (EVT), then a custom pouch of the same envelope (≤ 6.2 × 31 × 43 mm, 750–800 mAh [E]) at DVT, IEC 62133-2 + UN38.3 (`12-SIZE-S.md` §2.4) | same |
| Base and foot | SLA/MJF painted | PC/ABS injection moulded | same |
| OU | SLA | aluminium bridge tools | steel tools $16–26k |
| Compliance | €5–12k (RO/PL lab, RO only) | €30–80k (full RED at an EU lab, EN 18031, EPR in 3–5 countries) | + CRA from 11 Dec 2027 |
| Assembly | the founder, by hand | EMS + end-of-line fixtures ($4–7k) | same |
| Hardware per unit [E] | ≈ €190–210 (01-BOM (b)); ≈ €144 at 100 | **≈ €74** incl. external shell (`12-SIZE-S.md` §3.1, 01-BOM (c)); M would be ≈ €98 | ≈ $42–63 + Al adder (research/09 §3.7, PC version) |
| CNC per set | ~24 min, 0.4 kg billet [E] | ~17 sets / machine / shift; ≈ 3,740 / year on 1 shift (`12-SIZE-S.md` §3.2) | deep draw replaces most of it |
