# 01 · Bill of materials (P0 prototype + Founders 00)

*SOUL package · 25 Sep 2026 · all prices in **EUR** (€1 = $1.137, the ECB rate used in research/09). **[E]** = estimate, **[V]** = checked list price. No price here is a real quote until the same STEP goes to the suppliers (see [02-MANUFACTURING](02-MANUFACTURING.md) §4).*

Machine-readable version: **[BOM.csv](BOM.csv)** (same rows, with URLs, subtotals and totals). It is generated from `docs/_tools/bom.py`, so edit that script and re-run it: `python3 docs/_tools/bom.py`.

## Totals

| What | Per unit | Batch | Notes |
|---|---|---|---|
| **P0 plastic looks-like** (1 unit, SLA shells + metallic paint) | **≈ €211** [E] | – | Includes the OU print, box and freight share. Board alone is €33. |
| **P0 aluminium** (1 unit, CNC set bought as a pair) | **≈ €363** [E] | ≈ €563 if you pay for both CNC sets | CNC shops quote 2 sets minimum. The second set is your spare. |
| **Founders 00 hardware @ 10 units** | ≈ €271 [E] | ≈ €2.7k | Why 25 beats 10: CNC set-up is 40–60 % of the price at small quantities. |
| **Founders 00 hardware @ 25 units** | **≈ €190** [E] (+10 % scrap reserve = €209) | **≈ €5.2k** | Matches research/10 §1.3 (≈ $230 ≈ €200). |
| **Founders 00 one-off costs** (CE/RED, EN 18031, ANMAP, trademark, spares, tools, insurance) | – | **≈ €15.0k** [E] | CE/RED is €5–12k. That range decides the total. |
| **Founders 00 total cash out** | ≈ €810 per unit if the one-off costs are spread over 25 | **≈ €20.3k** [E] | Revenue at €349 × 25 = €8.7k gross. **Certification is a brand investment, not COGS.** Options are in research/10 §6. |

Not included:
- Assembly labour: 2–3 h per unit, done by the founder.
- AI accounts: the user brings their own key, or uses no AI.
- Marketing and the photo shoot.
- Contingency: add 15–20 %.

## What P0 contains

P0 ("SOUL-P0") is the DIY pilot enclosure from `prototip/cad/soul_p0.py`. It is **not** the final v6 body.
- **Parts:** front shell, back shell, a printed chassis, PWR/BOOT key pins and an optional seam band (the RF window).
- **Board:** the stock Waveshare board with its stock Ø48.96 glass.
- **Body:** about 63 × 75 × 29.5 mm, 2.5 mm deeper than v6 because the Waveshare stack is 8.9 mm deep.
- **Closure:** 4 × M2 screws from the back.
- **Charging:** over the board's own USB-C. Pogo contacts and the OU dock are optional in P0.

Three CAD variants:
- `plastic`: FDM/SLA, 2.0 mm walls, M2 heat-set inserts.
- `alu`: CNC 6061, 1.4 mm walls, tapped M2.
- `alu_band`: alu plus a 3 mm printed plastic band at the seam, which is the RF window.

## Tables

### (a) DIY prototype P0: parts per unit
Qty 1 = one prototype. Build 2–3: the price per unit drops toward the @10 column only for printed parts.

| ID | Part | Spec | Qty/unit | Supplier | €/unit @1 | @10 | @25 | Subtotal/unit @1 | Notes |
|---|---|---|---|---|---|---|---|---|---|
| P0-01 | **Waveshare ESP32-S3-Touch-AMOLED-1.75**  | ESP32-S3R8, 16 MB flash, 1.75" round AMOLED 466x466 (CO5300) + CST9217 touch, ES8311+ES7210 2 mics, QMI8658, RTC, AXP2101, PWR key; kit speaker | 1 | [Waveshare (or Eckstein DE / Botland PL)](https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm) | 33 | 31 | 29 | 33 | List $29.99-39.99 [V]; EUR incl. shipping share. Buy 2 for P0 (one spare). |
| P0-02 | **LiPo cell 503035** [E] | 3.7 V ~500 mAh, protection PCM, 2-pin MX1.25 lead (check polarity vs board BAT connector); UN38.3 summary from seller | 1 | [AliExpress / Robofun / Optimus Digital](https://www.aliexpress.com/w/wholesale-503035-lipo.html) | 6 | 4.5 | 3.5 | 6 | CAD envelope 30.5 x 36.5 x 5.3 mm incl. swell (prototip/cad/soul_p0.py BAT). Foam, never glue (Battery Reg. Art. 11). |
| P0-03 | **Micro speaker 1511** [E] | 15 x 11 x 3.5 mm, 8 ohm 1 W, wire leads -> MX1.25 | 1 | [AliExpress](https://www.aliexpress.com/w/wholesale-1511-speaker-8ohm.html) | 2 | 1.5 | 1.2 | 2 | The board kit speaker may be larger; P0 keep-out is 15 x 11 x 3.6 behind the PCB. |
| P0-04 | **M2 brass heat-set inserts** [E] | M2, OD 3.2 mm, L 4 mm (plastic variant only; alu variant uses tapped M2 holes) | 4 | [Ruthex / AliExpress](https://www.ruthex.de) | 0.08 | 0.06 | 0.05 | 0.32 | Pack of 100 ~EUR 6-9. |
| P0-05 | **M2 screws, A2 stainless** [E] | M2 pan/countersunk, Torx T6 (or PH0); length <= screw_len_max in prototip/CHECKS.txt (typ. M2x5-M2x8) | 4 | [AliExpress / Bossard / local](https://www.aliexpress.com/w/wholesale-m2-torx-screw-stainless.html) | 0.1 | 0.08 | 0.06 | 0.4 | 2 lower (clamp chassis legs) + 2 upper (straight into front). Final v6 design: 2 x Torx T5 in the foot. |
| P0-06 | **Neodymium magnets** [E] | Dia 6 x 2 mm N52, glued in base recesses (optional; dock alignment) | 2 | [AliExpress / supermagnete.de](https://www.aliexpress.com/w/wholesale-n52-magnet-6x2.html) | 0.2 | 0.15 | 0.12 | 0.4 | Keep >= 10 mm from antenna. "Contains magnets" warning in the guide. |
| P0-07 | **Magnetic pogo connector pair** [E] | 5-pin (or 4-pin) magnetic pogo, 2.54 mm pitch, male + female (optional OU dock; P0 charges over the board USB-C) | 1 | [AliExpress](https://www.aliexpress.com/w/wholesale-magnetic-pogo-pin-connector-5pin.html) | 4 | 3 | 2.5 | 4 | Final design: 5 gold pads on an FR4 coin (JLCPCB ENIG/hard gold, EUR 1-3 at 25). |
| P0-08 | **Foam, tapes** [E] | PU/PORON foam pad 0.8 mm under the cell, Kapton tape, thin 3M 9448/VHB for chassis | 1 | [AliExpress / TME](https://www.tme.eu) | 1 | 0.6 | 0.4 | 1 | No adhesive on the battery itself. |
| P0-09 | **FDM fit-test print** [E] | PETG/PLA front + back + chassis, 0.2 mm layers (plastic variant STLs) | 1 | [home / Bambu / local print shop](https://craftcloud3d.com) | 3 | 3 | 3 | 3 | For fit only. Weigh and measure before ordering anything else. |
| P0-10 | **Printed chassis + PWR/BOOT pins + seam band** [E] | SLA Tough/black resin or MJF PA12 dyed black; always printed (both variants) | 1 | [JLC3DP / PCBWay / RO print shop](https://jlc3dp.com) | 12 | 8 | 6 | 12 | Seam band only for the alu_band variant (RF window). |
| P0-11 | **Looks-like shells (plastic variant)** [E] | SLA front + back shells, primer + metallic paint or Cerakote (20-30 um) | 1 | [JLC3DP / RO print shop + Cerakote applicator](https://jlc3dp.com) | 45 | 35 | – | 45 | Prototype 1-3 only; $15-40 print + $10-25 finish (research/10 section 6). Not used in Founders 00. |
| P0-12 | **CNC aluminium shells (alu variant)** [E] | 6061-T6, 2 halves (front + back), bead-blast ~50 um glass bead, anodise type II coloured + sealed; ISO 2768-m, +-0.05 on glass seat and seam | 1 | [JLCCNC / PCBWay / RapidDirect (EU: Weerg; RO: ARSAT, Alvi Technik)](https://jlccnc.com) | 200 | 145 | 92 | 200 | research/10 section 1.3: $150-300/set at qty 2, $110-220 @10, $70-140 @25. Price at qty 1 = order of 2 sets. |
| P0-13 | **OU capsule shell set** [E] | SLA cup + lid + liner, sanded, primed, painted (frosted lid: clear resin + matte coat) | 1 | [JLC3DP / RO print shop](https://jlc3dp.com) | 55 | 40 | 30 | 55 | research/10: capsule incl. finish $35-60 @10, $25-45 @25. STL for OU not yet in the vault (gap). |
| P0-14 | **OU electronics** [E] | USB-C breakout (5 V), pogo female side (from P0-07), 2 magnets, silicone wire; optional 2200 K LED strip | 1 | [AliExpress / Optimus Digital](https://www.optimusdigital.ro) | 5 | 4 | 3 | 5 | Standard OU: no battery, no radio. |
| P0-15 | **USB-C data cable** [E] | Braided USB-C to USB-C (or A-C), 1 m, data-capable (flashing) | 1 | [AliExpress / eMAG](https://www.aliexpress.com/w/wholesale-braided-usb-c-cable.html) | 4 | 3 | 2.5 | 4 | No charger in the box (EU common-charger rules). |
| P0-16 | **Packaging** [E] | Rigid cream box or sleeve 118 x 78 x 150 mm, pulp/foam insert, quick-guide card | 1 | [Romanian print shop (tipografie)](https://www.google.com/search?q=cutii+rigide+personalizate+tiraj+mic) | 15 | 10 | 8 | 15 | research/10: $8-15 @10, $6-12 @25. |
| P0-17 | **Freight + customs share** [E] | DHL Express CN->RO (~$14/kg) + ~6 % duty (B2B, HS 7616/8529 per broker) + 21 % import VAT + clearance fee | 1 | [DHL Express](https://www.dhl.com/ro-en/home.html) | 25 | 12 | 6 | 25 | Needs EORI. VAT deductible only if VAT-registered (ARTEMIS is not). |

### (b) Founders 00, 25 units: extra parts per unit
Per unit, a Founders 00 SOUL = P0-01…P0-08, P0-10 and P0-12…P0-17 at the @25 price, **plus** the lines below. P0-09 (the FDM fit test) and P0-11 (the plastic looks-like shells) are not used.

| ID | Part | Spec | Qty/unit | Supplier | €/unit @1 | @10 | @25 | Subtotal/unit @1 | Notes |
|---|---|---|---|---|---|---|---|---|---|
| F-01 | **Laser marking on base** [E] | SOUL, No. (serial), PROIECTAT IN ROMANIA, model/batch, manufacturer + address, CE, WEEE crossed bin, battery Li-ion 3.7 V / Wh | 1 | [CNC supplier (add to RFQ) or RO fibre-laser shop](https://jlccnc.com) | – | 3 | 2 | – | Mask a ground contact spot during anodising (ESD). |
| F-02 | **Coin PCB for 5 contacts** [E] | FR4 coin, ENIG or hard gold, 1 centre pad dia 1.8 + 4 arc pads | 1 | [JLCPCB](https://jlcpcb.com) | – | 2 | 1.5 | – | Final v6 foot contacts; P0 can skip. |
| F-03 | **Birth certificate + RO/EN quick guide** [E] | Numbered certificate (No. 001-025), guide with safety, battery, magnets, not-a-toy, AI disclosure, disposal, 2-year guarantee | 1 | Romanian print shop | – | 2 | 1.5 | – | GPSR: instructions in Romanian. |
| F-04 | **Legal label on box** [E] | Model, serial/batch, CE, WEEE bin, battery data, manufacturer, QR to DoC | 1 | Romanian print shop | – | 0.6 | 0.5 | – |  |

### (b) Founders 00: one-off costs for the batch
The "Subtotal/unit @1" column here is the line total for the batch.

| ID | Part | Spec | Qty/unit | Supplier | €/unit @1 | @10 | @25 | Subtotal/unit @1 | Notes |
|---|---|---|---|---|---|---|---|---|---|
| B-01 | **RF reference boards**  | 2 x Waveshare ESP32-S3-Touch-AMOLED-1.75C (factory CNC Al case) for the RSSI test | 2 | [Waveshare](https://www.waveshare.com/esp32-s3-touch-amoled-1.75c.htm) | 37 | 37 | 37 | 74 | List $39.99-41.99 [V]. |
| B-02 | **Spare CNC sets (same anodise bath)** [E] | +5 sets (20 %) in the same order and bath for scrap/colour match | 5 | [JLCCNC / PCBWay](https://jlccnc.com) | 92 | 92 | 92 | 460 | Colour varies bath to bath: one golden sample, one bath. |
| B-03 | **Spare boards + cells** [E] | 2 boards + 3 cells | 1 | [Waveshare / AliExpress](https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm) | 70 | 70 | 70 | 70 |  |
| B-04 | **Tools** [E] | Soldering iron + M2 insert tip, Torx T5/T6 + PH0 drivers, digital calipers, ESD mat, kitchen scale 0.1 g, USB power meter | 1 | [eMAG / iFixit / TME](https://www.ifixit.com) | 120 | 120 | 120 | 120 | One-off, reused. |
| B-05 | **CE / RED testing (radio, EMC, safety, RF exposure)** [E] | EN 300 328, EN 301 489-1/-17, EN IEC 62368-1, EN 62479; Module A self-declaration | 1 | Test lab PL/RO (quote 3 labs) | 8500 | 8500 | 8500 | 8500 | research/03: EUR 5-12k PL/RO, 4-6 weeks best case, 8-12 with fixes. Bare ESP32-S3 (no module) = full radio tests. |
| B-06 | **EN 18031 cybersecurity (RED 3.3 d/e/f)** [E] | Assessment + documentation; notified body only if a restriction is hit | 1 | Same lab / consultant | 3000 | 3000 | 3000 | 3000 | research/03: EUR 0-9k ($6-9.5k full). |
| B-07 | **Compliance consultant + technical file** [E] | 1 h scoping + DoC, risk analysis (GPSR), manuals, labels | 1 | Consultant | 800 | 800 | 800 | 800 |  |
| B-08 | **ANMAP registrations + collective scheme** [E] | EEE producer 500 lei + battery producer 500 lei + scheme contract (Environ/Ecotic) year 1 | 1 | [ANMAP + Environ / Ecotic](https://www.anmap.gov.ro) | 500 | 500 | 500 | 500 | Plus AFM monthly declarations. |
| B-09 | **EU trademark SOUL**  | EUIPO, classes 9 + 42 (EUR 850 + 50); apply for SME Fund voucher FIRST | 1 | [EUIPO](https://www.euipo.europa.eu) | 900 | 900 | 900 | 900 | Up to 75 % back via SME Fund 2026 (deadline 4 Dec 2026, check availability). |
| B-10 | **Product liability insurance (year 1)** [E] |  | 1 | Romanian insurer / broker | 500 | 500 | 500 | 500 |  |
| B-11 | **Anodise colour golden sample** [E] | Physical sample per colour, approved under D65 light | 1 | [CNC supplier](https://jlccnc.com) | 100 | 100 | 100 | 100 |  |
