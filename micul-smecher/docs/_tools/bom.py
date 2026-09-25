#!/usr/bin/env python3
"""Generate docs/BOM.csv + markdown tables for docs/01-BOM.md (EUR, €1 = $1.137)."""
import csv, sys

import os
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '')

# id, build, kind, part, spec, qty, supplier, url, p1, p10, p25, est, notes
# build: P0 = DIY prototype, F00 = Founders 00 run; kind: unit (per device) or batch (one-off for the run)
AE = 'https://www.aliexpress.com/w/wholesale-'
L = [
 # ---------------- (a) DIY prototype P0: per-unit parts
 ('P0-01', 'P0', 'unit', 'Waveshare ESP32-S3-Touch-AMOLED-1.75', 'ESP32-S3R8, 16 MB flash, 1.75" round AMOLED 466x466 (CO5300) + CST9217 touch, ES8311+ES7210 2 mics, QMI8658, RTC, AXP2101, PWR key; kit speaker', 1, 'Waveshare (or Eckstein DE / Botland PL)', 'https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm', 33, 31, 29, '', 'List $29.99-39.99 [V]; EUR incl. shipping share. Buy 2 for P0 (one spare).'),
 ('P0-02', 'P0', 'unit', 'LiPo cell 503035', '3.7 V ~500 mAh, protection PCM, 2-pin MX1.25 lead (check polarity vs board BAT connector); UN38.3 summary from seller', 1, 'AliExpress / Robofun / Optimus Digital', AE + '503035-lipo.html', 6, 4.5, 3.5, 'E', 'CAD envelope 30.5 x 36.5 x 5.3 mm incl. swell (prototip/cad/soul_p0.py BAT). Foam, never glue (Battery Reg. Art. 11).'),
 ('P0-03', 'P0', 'unit', 'Micro speaker 1511', '15 x 11 x 3.5 mm, 8 ohm 1 W, wire leads -> MX1.25', 1, 'AliExpress', AE + '1511-speaker-8ohm.html', 2, 1.5, 1.2, 'E', 'The board kit speaker may be larger; P0 keep-out is 15 x 11 x 3.6 behind the PCB.'),
 ('P0-04', 'P0', 'unit', 'M2 brass heat-set inserts', 'M2, OD 3.2 mm, L 4 mm (plastic variant only; alu variant uses tapped M2 holes)', 4, 'Ruthex / AliExpress', 'https://www.ruthex.de', 0.08, 0.06, 0.05, 'E', 'Pack of 100 ~EUR 6-9.'),
 ('P0-05', 'P0', 'unit', 'M2 screws, A2 stainless', 'M2 pan/countersunk, Torx T6 (or PH0); length <= screw_len_max in prototip/CHECKS.txt (typ. M2x5-M2x8)', 4, 'AliExpress / Bossard / local', AE + 'm2-torx-screw-stainless.html', 0.10, 0.08, 0.06, 'E', '2 lower (clamp chassis legs) + 2 upper (straight into front). Final v6 design: 2 x Torx T5 in the foot.'),
 ('P0-06', 'P0', 'unit', 'Neodymium magnets', 'Dia 6 x 2 mm N52, glued in base recesses (optional; dock alignment)', 2, 'AliExpress / supermagnete.de', AE + 'n52-magnet-6x2.html', 0.20, 0.15, 0.12, 'E', 'Keep >= 10 mm from antenna. "Contains magnets" warning in the guide.'),
 ('P0-07', 'P0', 'unit', 'Magnetic pogo connector pair', '5-pin (or 4-pin) magnetic pogo, 2.54 mm pitch, male + female (optional OU dock; P0 charges over the board USB-C)', 1, 'AliExpress', AE + 'magnetic-pogo-pin-connector-5pin.html', 4, 3, 2.5, 'E', 'Final design: 5 gold pads on an FR4 coin (JLCPCB ENIG/hard gold, EUR 1-3 at 25).'),
 ('P0-08', 'P0', 'unit', 'Foam, tapes', 'PU/PORON foam pad 0.8 mm under the cell, Kapton tape, thin 3M 9448/VHB for chassis', 1, 'AliExpress / TME', 'https://www.tme.eu', 1.0, 0.6, 0.4, 'E', 'No adhesive on the battery itself.'),
 ('P0-09', 'P0', 'unit', 'FDM fit-test print', 'PETG/PLA front + back + chassis, 0.2 mm layers (plastic variant STLs)', 1, 'home / Bambu / local print shop', 'https://craftcloud3d.com', 3, 3, 3, 'E', 'For fit only. Weigh and measure before ordering anything else.'),
 ('P0-10', 'P0', 'unit', 'Printed chassis + PWR/BOOT pins + seam band', 'SLA Tough/black resin or MJF PA12 dyed black; always printed (both variants)', 1, 'JLC3DP / PCBWay / RO print shop', 'https://jlc3dp.com', 12, 8, 6, 'E', 'Seam band only for the alu_band variant (RF window).'),
 ('P0-11', 'P0', 'unit', 'Looks-like shells (plastic variant)', 'SLA front + back shells, primer + metallic paint or Cerakote (20-30 um)', 1, 'JLC3DP / RO print shop + Cerakote applicator', 'https://jlc3dp.com', 45, 35, 0, 'E', 'Prototype 1-3 only; $15-40 print + $10-25 finish (research/10 section 6). Not used in Founders 00.'),
 ('P0-12', 'P0', 'unit', 'CNC aluminium shells (alu variant)', '6061-T6, 2 halves (front + back), bead-blast ~50 um glass bead, anodise type II coloured + sealed; ISO 2768-m, +-0.05 on glass seat and seam', 1, 'JLCCNC / PCBWay / RapidDirect (EU: Weerg; RO: ARSAT, Alvi Technik)', 'https://jlccnc.com', 200, 145, 92, 'E', 'research/10 section 1.3: $150-300/set at qty 2, $110-220 @10, $70-140 @25. Price at qty 1 = order of 2 sets.'),
 ('P0-13', 'P0', 'unit', 'OU capsule shell set', 'SLA cup + lid + liner, sanded, primed, painted (frosted lid: clear resin + matte coat)', 1, 'JLC3DP / RO print shop', 'https://jlc3dp.com', 55, 40, 30, 'E', 'research/10: capsule incl. finish $35-60 @10, $25-45 @25. STL for OU not yet in the vault (gap).'),
 ('P0-14', 'P0', 'unit', 'OU electronics', 'USB-C breakout (5 V), pogo female side (from P0-07), 2 magnets, silicone wire; optional 2200 K LED strip', 1, 'AliExpress / Optimus Digital', 'https://www.optimusdigital.ro', 5, 4, 3, 'E', 'Standard OU: no battery, no radio.'),
 ('P0-15', 'P0', 'unit', 'USB-C data cable', 'Braided USB-C to USB-C (or A-C), 1 m, data-capable (flashing)', 1, 'AliExpress / eMAG', AE + 'braided-usb-c-cable.html', 4, 3, 2.5, 'E', 'No charger in the box (EU common-charger rules).'),
 ('P0-16', 'P0', 'unit', 'Packaging', 'Rigid cream box or sleeve 118 x 78 x 150 mm, pulp/foam insert, quick-guide card', 1, 'Romanian print shop (tipografie)', 'https://www.google.com/search?q=cutii+rigide+personalizate+tiraj+mic', 15, 10, 8, 'E', 'research/10: $8-15 @10, $6-12 @25.'),
 ('P0-17', 'P0', 'unit', 'Freight + customs share', 'DHL Express CN->RO (~$14/kg) + ~6 % duty (B2B, HS 7616/8529 per broker) + 21 % import VAT + clearance fee', 1, 'DHL Express', 'https://www.dhl.com/ro-en/home.html', 25, 12, 6, 'E', 'Needs EORI. VAT deductible only if VAT-registered (ARTEMIS is not).'),
 # ---------------- (b) Founders 00: extra per-unit lines (on top of P0-01..P0-10, P0-12..P0-17)
 ('F-01', 'F00', 'unit', 'Laser marking on base', 'SOUL, No. (serial), PROIECTAT IN ROMANIA, model/batch, manufacturer + address, CE, WEEE crossed bin, battery Li-ion 3.7 V / Wh', 1, 'CNC supplier (add to RFQ) or RO fibre-laser shop', 'https://jlccnc.com', 0, 3, 2, 'E', 'Mask a ground contact spot during anodising (ESD).'),
 ('F-02', 'F00', 'unit', 'Coin PCB for 5 contacts', 'FR4 coin, ENIG or hard gold, 1 centre pad dia 1.8 + 4 arc pads', 1, 'JLCPCB', 'https://jlcpcb.com', 0, 2, 1.5, 'E', 'Final v6 foot contacts; P0 can skip.'),
 ('F-03', 'F00', 'unit', 'Birth certificate + RO/EN quick guide', 'Numbered certificate (No. 001-025), guide with safety, battery, magnets, not-a-toy, AI disclosure, disposal, 2-year guarantee', 1, 'Romanian print shop', '', 0, 2, 1.5, 'E', 'GPSR: instructions in Romanian.'),
 ('F-04', 'F00', 'unit', 'Legal label on box', 'Model, serial/batch, CE, WEEE bin, battery data, manufacturer, QR to DoC', 1, 'Romanian print shop', '', 0, 0.6, 0.5, 'E', ''),
 # ---------------- (b) Founders 00: one-off lines for the batch
 ('B-01', 'F00', 'batch', 'RF reference boards', '2 x Waveshare ESP32-S3-Touch-AMOLED-1.75C (factory CNC Al case) for the RSSI test', 2, 'Waveshare', 'https://www.waveshare.com/esp32-s3-touch-amoled-1.75c.htm', 37, 37, 37, '', 'List $39.99-41.99 [V].'),
 ('B-02', 'F00', 'batch', 'Spare CNC sets (same anodise bath)', '+5 sets (20 %) in the same order and bath for scrap/colour match', 5, 'JLCCNC / PCBWay', 'https://jlccnc.com', 92, 92, 92, 'E', 'Colour varies bath to bath: one golden sample, one bath.'),
 ('B-03', 'F00', 'batch', 'Spare boards + cells', '2 boards + 3 cells', 1, 'Waveshare / AliExpress', 'https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm', 70, 70, 70, 'E', ''),
 ('B-04', 'F00', 'batch', 'Tools', 'Soldering iron + M2 insert tip, Torx T5/T6 + PH0 drivers, digital calipers, ESD mat, kitchen scale 0.1 g, USB power meter', 1, 'eMAG / iFixit / TME', 'https://www.ifixit.com', 120, 120, 120, 'E', 'One-off, reused.'),
 ('B-05', 'F00', 'batch', 'CE / RED testing (radio, EMC, safety, RF exposure)', 'EN 300 328, EN 301 489-1/-17, EN IEC 62368-1, EN 62479; Module A self-declaration', 1, 'Test lab PL/RO (quote 3 labs)', '', 8500, 8500, 8500, 'E', 'research/03: EUR 5-12k PL/RO, 4-6 weeks best case, 8-12 with fixes. Bare ESP32-S3 (no module) = full radio tests.'),
 ('B-06', 'F00', 'batch', 'EN 18031 cybersecurity (RED 3.3 d/e/f)', 'Assessment + documentation; notified body only if a restriction is hit', 1, 'Same lab / consultant', '', 3000, 3000, 3000, 'E', 'research/03: EUR 0-9k ($6-9.5k full).'),
 ('B-07', 'F00', 'batch', 'Compliance consultant + technical file', '1 h scoping + DoC, risk analysis (GPSR), manuals, labels', 1, 'Consultant', '', 800, 800, 800, 'E', ''),
 ('B-08', 'F00', 'batch', 'ANMAP registrations + collective scheme', 'EEE producer 500 lei + battery producer 500 lei + scheme contract (Environ/Ecotic) year 1', 1, 'ANMAP + Environ / Ecotic', 'https://www.anmap.gov.ro', 500, 500, 500, 'E', 'Plus AFM monthly declarations.'),
 ('B-09', 'F00', 'batch', 'EU trademark SOUL', 'EUIPO, classes 9 + 42 (EUR 850 + 50); apply for SME Fund voucher FIRST', 1, 'EUIPO', 'https://www.euipo.europa.eu', 900, 900, 900, '', 'Up to 75 % back via SME Fund 2026 (deadline 4 Dec 2026, check availability).'),
 ('B-10', 'F00', 'batch', 'Product liability insurance (year 1)', '', 1, 'Romanian insurer / broker', '', 500, 500, 500, 'E', ''),
 ('B-11', 'F00', 'batch', 'Anodise colour golden sample', 'Physical sample per colour, approved under D65 light', 1, 'CNC supplier', 'https://jlccnc.com', 100, 100, 100, 'E', ''),
]

HDR = ['id', 'build', 'kind', 'part', 'spec', 'qty_per_unit', 'supplier', 'url', 'eur_unit_q1', 'eur_unit_q10', 'eur_unit_q25',
       'subtotal_per_unit_q1', 'subtotal_per_unit_q25', 'subtotal_batch25', 'estimate', 'notes']

# which P0 lines go into Founders 00 per unit
F00_FROM_P0 = [i for i in ['P0-%02d' % k for k in range(1, 18)] if i not in ('P0-09', 'P0-11')]


def rows():
    out = []
    for (i, b, k, part, spec, q, sup, url, p1, p10, p25, e, n) in L:
        s1 = round(q * p1, 2)
        s25 = round(q * p25, 2)
        if k == 'unit':
            batch = round(s25 * 25, 2) if (b == 'F00' or i in F00_FROM_P0) else 0
        else:
            batch = round(q * p25, 2)
        out.append([i, b, k, part, spec, q, sup, url, p1, p10, p25, s1, s25, batch, '[E]' if e else '', n])
    return out


R = rows()
with open(OUT + 'BOM.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(HDR)
    for r in R:
        w.writerow(r)
    # totals
    by = {r[0]: r for r in R}
    p0_plastic = sum(by[i][11] for i in ['P0-%02d' % k for k in range(1, 18)] if i != 'P0-12')
    p0_alu = sum(by[i][11] for i in ['P0-%02d' % k for k in range(1, 18)] if i not in ('P0-09', 'P0-11'))
    unit25 = sum(by[i][12] for i in F00_FROM_P0) + sum(r[12] for r in R if r[1] == 'F00' and r[2] == 'unit')
    unit10 = sum(by[i][5] * by[i][9] for i in F00_FROM_P0) + sum(r[5] * r[9] for r in R if r[1] == 'F00' and r[2] == 'unit')
    scrap25 = round(unit25 * 0.10, 2)
    batch_oneoff = sum(r[13] for r in R if r[2] == 'batch')
    hw_batch = round((unit25 + scrap25) * 25, 2)
    T = dict(p0_plastic=round(p0_plastic, 2), p0_alu=round(p0_alu, 2), unit10=round(unit10, 2), unit25=round(unit25, 2),
             scrap25=scrap25, hw_batch=hw_batch, oneoff=round(batch_oneoff, 2), total=round(hw_batch + batch_oneoff, 2))
    w.writerow([])
    for k, v in [('TOTAL P0 plastic looks-like, 1 unit', T['p0_plastic']), ('TOTAL P0 aluminium (CNC), 1 unit (CNC set bought as 2)', T['p0_alu']),
                 ('TOTAL Founders 00 hardware per unit @10', T['unit10']), ('TOTAL Founders 00 hardware per unit @25', T['unit25']),
                 ('+10 % scrap/reserve per unit @25', T['scrap25']), ('Founders 00 hardware, 25 units incl. reserve', T['hw_batch']),
                 ('Founders 00 one-off (compliance, spares, tools, IP)', T['oneoff']), ('Founders 00 TOTAL cash out (25 units)', T['total'])]:
        w.writerow(['TOTAL', '', '', k, '', '', '', '', '', '', '', '', '', v, '[E]', ''])

import json
json.dump(T, sys.stdout, indent=1)


def md():
    def f(x):
        return '–' if x == 0 else ('%.2f' % x).rstrip('0').rstrip('.')
    s = []
    for title, sel in [('P0', lambda r: r[1] == 'P0'), ('F00u', lambda r: r[1] == 'F00' and r[2] == 'unit'), ('F00b', lambda r: r[2] == 'batch')]:
        s.append('\n### ' + title + '\n')
        s.append('| ID | Part | Spec | Qty/unit | Supplier | €/unit @1 | @10 | @25 | Subtotal/unit @1 | Notes |')
        s.append('|---|---|---|---|---|---|---|---|---|---|')
        for r in R:
            if sel(r):
                sup = f'[{r[6]}]({r[7]})' if r[7] else r[6]
                s.append(f'| {r[0]} | **{r[3]}** {r[14]} | {r[4]} | {r[5]} | {sup} | {f(r[8])} | {f(r[9])} | {f(r[10])} | {f(r[11])} | {r[15]} |')
    return '\n'.join(s)


open(os.path.join(OUT, '_tools', 'bom_tables.md'), 'w').write(md())
