# 02 · Manufacturing dossier

*SOUL package · 25 Sep 2026. Sources: `renders/v6/README.md` (final CMF), `research/10-carcasa-aluminiu.md` (aluminium route, suppliers, costs), `research/09-product-design-max-2026-09-24.md` (specs, OU, markings, tests), `prototip/cad/soul_p0.py` (the buildable P0), `blueprints/`, `cad/`. Tags: **[V]** verified, **[E]** estimate, **[GAP]** missing today.*

## 1. Which design gets built

| Design | What | Size | Status |
|---|---|---|---|
| **SOUL v6** (final look, design code HOPA) | Aluminium upright pebble, flat foot, 1.75" AMOLED behind black glass | ≈ 63 × 72.2 × 27 mm | **Renders only** (`renders/v6/`). There is no v6 production CAD yet: v6 exists as the Blender mesh (`renders/v6/src/soul_v6.py`). |
| **SOUL-P0** (DIY pilot) | The v6 silhouette, adapted around the **stock Waveshare 1.75 board** and its stock glass | ≈ 63 × 75 × 29.5 mm (+3 mm tall, +2.5 mm deep, because the Waveshare stack is 8.9 mm) | **CAD in progress** (`prototip/cad/soul_p0.py`, CadQuery). Another agent is still exporting parts. See §2. |
| Founders 00 (25 units) | **= P0 in aluminium** (the `alu` or `alu_band` variant), anodised, with a printed chassis | as P0 | Waits for P0 rev B, after a fit print and an RF test |
| Older concepts | `cad/` (OpenSCAD: coin, drop, gem and cloud for the 1.43/1.75 boards), `blueprints/` rev A (the oval v2), `blueprints/v3` | – | **Reference only. Do not send these to a supplier.** |

**Pending decision: a bigger screen** ([`research/12-ecran-mai-mare.md`](../research/12-ecran-mai-mare.md), renders in `renders/v7/`). The study compares three sizes:
- **S** = today's 1.75" AMOLED, body 63 × 72 × 27.
- **M** = 2.8" IPS 480², Waveshare ESP32-S3-Touch-LCD-2.8C, body ≈ 93 × 106 × 31.
- **L** = 3.4" IPS 800², ESP32-P4, body ≈ 113 × 129 × 34.

research/12 found that no round AMOLED larger than 1.75" can be bought in small quantities, so a bigger screen means IPS, and IPS has no true black. It recommends **S** as the hero product, with writing done on the phone or by voice, and **M** as a parallel prototype (~$40 board). **Everything in this dossier assumes S (1.75").** Choosing M or L means a new board, new CAD and new costs. Decide before any CNC order.

## 2. CAD / STL / STEP files, and which to send where

| File (path in the vault) | Format | Send to | Purpose |
|---|---|---|---|
| `prototip/stl/plastic/soul_p0_plastic_{front_shell,back_shell,chassis,pin_pwr,pin_boot}.stl` | STL, already in print pose | **Home FDM / Bambu** (fit test), then an **SLA print shop** (looks-like) | P0 plastic, 2.0 mm walls, M2 inserts. **Exported** (5 STL + 5 STEP in `prototip/step/plastic/`) |
| `prototip/step/alu/soul_p0_alu_front_shell.step` + `…_back_shell.step` | STEP AP214 | **CNC**: JLCCNC, PCBWay, RapidDirect, Weerg, Xometry, ARSAT, Alvi Technik (the same STEP to all) | P0 aluminium shells, 1.4 mm walls, tapped M2. **Only `front_shell` exists today** (17 MB STEP + STL; the zip ships it as `.step.gz`, so run `gunzip` first). **[GAP: back shell]** |
| `prototip/step/alu_band/…` + `prototip/stl/alu_band/…_seam_band.stl` | STEP + STL | CNC (shells) + SLA/MJF (3 mm band) | Variant with a plastic RF window at the seam. **Choose this one if the RSSI test loses more than 6 dB** |
| `prototip/stl/*/…_chassis.stl`, `…_pin_pwr.stl`, `…_pin_boot.stl` | STL | **SLA (black Tough) or MJF PA12** at JLC3DP / PCBWay / a local shop | Always printed, in both variants |
| `prototip/step/soul_p0_plastic_ASSEMBLY_with_board.step` | STEP assembly | Reference for suppliers and for you | Board, cell and speaker in place (112 MB; **not in the zip**, too big) |
| `prototip/cad/report_plastic.json` (+ `prototip/CHECKS.txt`, `prototip/img/` when exported) | JSON/text/PNG | You | Interference and clearance checks, maximum screw length, mass. The plastic report exists; the alu report **[GAP]** |
| `blueprints/*.svg/png`, `blueprints/v3/*` | A3 drawings | Reference only (older oval and amulet concepts) | Useful as a drawing template. The v6/P0 drawing (`blueprints/final/`) **[GAP]** |
| `cad/stl/ms175_*.stl` (33 STLs, all checked manifold) | STL | Only for testing the older shapes | Legacy |
| `renders/v6/src/soul_v6.py` | Blender Python | Nobody | Source of the final look; body mesh cached in `/tmp/soul_v6_cache` |

**RFQ settings for the CNC shells (paste into every quote form):**
- Material **Al 6061-T6**, 2 parts (front, back). Quantities to quote: **2 / 10 / 25 / 30**.
- Surface: **bead-blast (glass bead, fine, ~50 µm), then anodise type II, coloured + sealed**, 10–25 µm.
- **Re-cut the 45° chamfer (0.45 mm) around the glass seat after blasting and before anodising**, so it comes out bright and satin.
- Tolerance: ISO 2768-m general, **±0.05 mm on the glass seat and the seam faces**.
- No threads in the aluminium, except the tapped M2 in the `alu` variant (or ask for M2 helicoils).
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
| **Natural silver / Argint natural** | `#CBCDCF` | `#B4B6B8` | Most stable. **Founders 00 default.** |
| **Graphite / Grafit** | `#55575B` | `#3C3E41` | Stable. Black/grey inorganic dyes resist UV. **Second Founders colour.** |
| **Night blue / Albastru noapte** | `#26324C` | `#1D2435` | Blue fades under UV. Later edition, with a golden sample. |
| **Ember / Jar** | `#D2622C` | `#A44A22` | Orange is process-sensitive and varies between suppliers. Sample first. |
| **Champagne / Șampanie** | `#D8C3A2` | `#BDAA8A` | Gold/champagne is process-sensitive. Sample first. |

Rules:
- One alloy, one supplier and one bath per colour.
- Never mix 6061 and 6063 in one colour.
- Approve the golden sample under D65 light.
- Edges R ≥ 0.5 mm, or the anodise chips.

## 4. Tolerances and fits

| Feature | P0 plastic | P0 alu | Final v6 target |
|---|---|---|---|
| Wall | 2.0 mm | 1.4 mm (1.0 at the crown for mass) | 1.0–1.2 mm |
| Fit clearance to the board and glass | 0.2 mm | 0.1 mm | – |
| Glass lip overlap | 1.2 mm thick, 1.5 mm over | 0.8 mm thick, 1.5 mm over (covers the dead ring of the stock Ø48.96 glass) | Ø52 custom glass, 45° × 0.45 chamfer |
| Screws | M2 into brass heat-set inserts (Ø3.2 × 4.6 hole) | M2 tapped (Ø1.6 pilot, 4.5 deep) | 2 × Torx T5 in the foot |
| Seam | planar parting plane (no undercut, 3-axis machinable) | same; optional 3 mm plastic band | belt seam on the silhouette |
| Speaker slot | 1.2 mm slot, z 45.5–57.5, in the +x seam | same | 12 × 0.6 mm laser slot, z 46–58 |
| Mics | – | – | 2 × Ø0.7 holes in the −x seam |
| General | ISO 2768-m | ISO 2768-m, ±0.05 on the seat and seam | – |

**UNVERIFIED — measure with calipers before the final print** (marked in `soul_p0.py`):
- the USB-C cable overmould (12.4 × 7.0 assumed);
- the mated MX1.25 plug keep-out (14.0 mm deep);
- the real 503035 cell with its PCM;
- the kit speaker.

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

## 6. Assembly sequence (P0 / Founders 00, per unit, ~2–3 h at first, ~45 min in series)

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
- [ ] Mass on a 0.1 g scale, recorded (P0 alu target ≈ 115–125 g) [E].
- [ ] Boot: eyes appear, and the panel is not shifted 6 px (SH8601 vs CO5300).
- [ ] Touch: tap = boop, double tap = laugh, hold 1.2 s = approve. Test all 4 quadrants.
- [ ] IMU: pick-up wakes it, face-down sleeps it, shake makes it dizzy.
- [ ] Audio: the speaker plays a chime, and the 2 mics record (1.75 only, when voice firmware exists).
- [ ] Buttons: PWR and BOOT click through the pins.
- [ ] Battery: charges over USB-C, the charge current is ≤ 0.5 C (AXP2101 set by firmware), and the cell is ≤ 45 °C after 30 min.
- [ ] RF: BLE RSSI at 1 m and 5 m against a reference board, logged; loss ≤ 6 dB. Claude Desktop Buddy pairs with the 6-digit code.
- [ ] Standalone stability: SOUL stands upright on the flat foot, and a 1 N flick at the crown does not tip it.
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
- Legal line: model (e.g. SOUL-P0 / SL-175), batch, `ARTEMIS DIGITAL S.R.L., <address>, <e-mail>`, `Made in <country>`.
- Symbols: **CE**, **WEEE crossed-out wheelie bin** (EN 50419), the **battery** symbol / "Li-ion" with voltage and Wh, and the separate-collection bin for batteries (required since 18 Aug 2025).
- Minimum symbol height: CE ≥ 5 mm (proportional). If the base is too small, the CE and WEEE marks may go on the packaging and in the manual, but put them on the product whenever there is room.
- The polymer base plate can be laser-marked or pad-printed. On anodised aluminium, laser-mark after anodising for a white or dark mark.

## 11. What changes at 1k and 10k

| | Founders 00 (25) | 1k | 10k |
|---|---|---|---|
| Body | CNC 6061, 2 shells, China/EU | CNC 6061 in China, $25–45/set, fixtures only | **Deep-drawn 5052 shells + CNC finish + blast + anodise**, $9–14/set; tools $20–45k (research/10 §2) |
| Board | Waveshare 1.75 stock | **Custom PCB with ESP32-S3-WROOM-1** (reuses Espressif radio evidence), PCBA design $15–30k | same, at an EMS (Seeed Fusion / PCBWay, or final assembly in RO: Kimball, Helbako, Etron) |
| Glass | stock Ø48.96 | custom Ø52 cover lens + lamination ($5–15k NRE) | same |
| Cell | stock 503035 | custom ~1000 mAh pouch, IEC 62133-2 + UN38.3 | same |
| Base and foot | SLA/MJF painted | PC/ABS injection moulded | same |
| OU | SLA | aluminium bridge tools | steel tools $16–26k |
| Compliance | €5–12k (RO/PL lab, RO only) | €30–80k (full RED at an EU lab, EN 18031, EPR in 3–5 countries) | + CRA from 11 Dec 2027 |
| Assembly | the founder, by hand | EMS + end-of-line fixtures ($4–7k) | same |
| COGS per system | ≈ €190–210 | ≈ $77–115 (research/09 §3.7, PC version; add ~$6–20 for Al) | ≈ $42–63 + Al adder |
