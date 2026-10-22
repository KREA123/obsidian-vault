# 12 · SOUL S: hardware spec, stack-up, battery, BOM delta

*SOUL package · 20 Oct 2026 · ARTEMIS DIGITAL S.R.L. · decision of 20 Oct 2026 (`03 Decizii/Jurnal decizii.md`): the final product is size **S**; the working prototype stays **M**. Machine-readable numbers: [`size-s.json`](size-s.json) (single source of truth; if this page and the JSON disagree, the JSON wins).*

*Tags: **[V]** checked today on Waveshare's product page, wiki, dimension drawing or STEP file · **[V-s]** a third-party listing or search snippet, not a datasheet in hand · **[R]** read from this repo · **[E] / [estimare]** estimate, with the reasoning next to it. Every price is [E] until a quote arrives.*

## Rezumat (RO)

- **SOUL S = MĂRGĂRITAR la scara lui de design: 63 × 70,8 × 23,0 mm**, sticlă neagră plată **Ø52**, ecran rotund **AMOLED 1,75″ 466×466** (negru adevărat). Adâncimea aleasă e **23,0 mm**: cu 1 mm mai mult decât randările M împărțite la 1,43 (22,05). Doar spatele e cu 1 mm mai plin; fața, sticla și silueta rămân identice.
- **Baterie: 750 mAh** (celulă LiPo 603040, 6,2 × 30,5 × 42 mm, 2,8 Wh). Încape cu **0,9 mm rezervă** la colțul cel mai strâmt, cu 10 % loc de umflare. La 22,0 mm rezerva ar fi doar 0,13 mm, adică nerealist.
- **Autonomie [estimare]: ~27 h** pe ziua-model din docs/09 (interval 21–34 h). E aproape cât M-ul (~32 h cu 1500 mAh), pentru că AMOLED-ul nu are lumină de fundal și ochii stau pe negru. Cu firmware care pune procesorul în light sleep (posibil pe AMOLED, imposibil pe ecranul RGB al lui M): **~2 zile**.
- **Placa de dezvoltare** Waveshare ESP32-S3-Touch-AMOLED-1.75, verificată azi: are 2 microfoane, codec și difuzor din cutie. **$29,99–39,99** la Waveshare (se poate comanda). Pe Pi Hut e £28,80 (standard), dar e epuizată. Nu am găsit vânzător în România.
- **Produsul final** are PCB propriu (ESP32-S3-WROOM-1 + panou AMOLED 1,75″ gol). Panouri goale există: Tailor-Pixels TOH175XRT-02CG, 0,8 mm, $9–17; NoseDisplay ND018ECG466466-A02; Lianxun LX175A3101CTP01. MOQ-ul se află doar prin cerere de ofertă.
- **Prototipul S-P0**, pe placa Waveshare cu sticla ei: **63 × 70,8 × 25,65 mm** (forma MĂRGĂRITAR necomprimată), baterie LiPo clasa 503030, ~450 mAh [estimare], ~16 h [estimare]. Planul de hârtie era 503035 / 500 mAh / ~18 h; CAD-ul exportat (22.10) arată că 35 mm nu încap lângă tunelul mufei USB-C (§2.3).
- **Costuri [estimare]:**
  - Placa + carcasa la 100 buc.: **≈ −70 € / buc. față de M** (−33 %). Placa e mai ieftină și nu mai trebuie microfon + amplificator, dar cel mai mult scade carcasa.
  - La 1.000 buc.: **≈ −24 € / buc.**
  - Carcasa CNC: semifabricat **0,4 kg** (M: 1,0 kg), ciclu **~24 min** (M: 45). Rezultă ~17 seturi / schimb / mașină în loc de 9.
- **M rămâne prototipul** pentru teste și dovada TRL 3, cu SoulOS 1.9.1 (`firmware/release/SOUL-2.8C-install.bin`; pentru S: `SOUL-1.75-install.bin`, tot 1.9.1).

---

## 0 · At a glance

| | **SOUL S (product)** | S-P0 (dev-board build) | M (prototype, unchanged) |
|---|---|---|---|
| Body W × H × D | **62.96 × 70.8 × 23.0 mm** | 62.96 × 70.8 × **25.65** mm | design 89.9 × 101.1 × 31.5; DIY P0-M kit 112.1 × 125.1 × 31.6 [R] |
| Shape | MĂRGĂRITAR v9, `marg_geo.py` local scale, back compressed s_back **0.807** | same, **uncompressed** back (s_back 1.0) | v9 × K (K = 90/63), s_back 0.735 |
| Glass | **Ø52** flat 2.5D black, 0.7 mm [E] | stock Ø48.96 × 1.10 under a lip [V] | stock Ø95.86 × 0.7 [R] |
| Screen | 1.75″ round AMOLED 466², active Ø43.76, CO5300 / QSPI [V] | same panel on the board | 2.8″ round IPS 480², ST7701 / RGB [R] |
| Electronics | custom PCB: ESP32-S3-WROOM-1-N16R8 + bare panel [E, EVT] | Waveshare ESP32-S3-Touch-AMOLED-1.75 | Waveshare ESP32-S3-Touch-LCD-2.8C |
| Audio | 2 MEMS mics + codec + 15 × 11 mm speaker in the +x seam [E] | on board: dual mics, ES7210 + ES8311, 8 Ω 2 W kit speaker [V] | optional INMP441 + MAX98357 [R] |
| Battery | **750 mAh** LiPo 603040 class (2.8 Wh) | ≈ 450 mAh LiPo 503030 class [E] (§2.3) | 1500 mAh LiPo 803450 [R] |
| Battery life (docs/09 day) [E] | **≈ 27 h** (21–34); ≈ 55 h with light-sleep firmware | ≈ 16 h | ≈ 32 h [R: docs/09 §3] |
| Weight [E] | **≈ 85 g** (75–95) | ≈ 90 g | – |

Why 23.0 mm and 750 mAh: §2.4. What it costs: §3.

---

## 1 · The board and the panel, checked today (20 Oct 2026)

### 1.1 Waveshare ESP32-S3-Touch-AMOLED-1.75

| Item | Value | Tag |
|---|---|---|
| SoC / memory | ESP32-S3R8 (dual LX7 240 MHz, 8 MB PSRAM stacked), 16 MB external flash | [V] wiki + product page |
| Radio | 2.4 GHz Wi-Fi b/g/n + BLE 5; onboard chip antenna, IPEX1 option by moving a resistor | [V] |
| Display | 1.75″ AMOLED, 466 × 466, 16.7 M colours, **CO5300**, **QSPI**; 700 cd/m², 100 000:1 | [V] product page |
| Display geometry (drawing) | touch panel OD **Ø48.96**, viewing area Ø44.16, **active area Ø43.76**; cover glass **1.10**, display stack total **2.05 mm** | [V] dimension drawing `ESP32-S3-Touch-AMOLED-1.75.pdf` in the wiki's 3D zip |
| Touch | **CST9217**, I2C | [V] |
| IMU / RTC | **QMI8658** 6-axis / **PCF85063** (kept by the AXP2101) | [V] |
| PMU / charger | **AXP2101** | [V] |
| Audio | **dual microphone array**, **ES7210** (echo cancellation / capture) and **ES8311** (codec; its datasheet is in the wiki's resources), speaker on an MX1.25 2-pin header, **8 Ω 2 W speaker in the kit** | [V] |
| Battery | MX1.25 2-pin, 3.7 V Li-ion/LiPo, charge + discharge | [V] |
| USB | USB-C to the S3's native USB (flash + log) | [V] |
| Buttons | PWR (programmable) + BOOT | [V] |
| Other | TCA9554 IO expander, TF slot, 8-pin 2.54 mm header (3 GPIO, UART, I2C) | [V] |
| Variants | Standard (board + speaker) · **-B** with protective case · **-G** with LC76G GNSS. A separate **AMOLED-1.75C** has a CNC aluminium case | [V] product page; 1.75C [R: docs/01 B-01] |
| PCB | **Ø46.0**, 1.2 mm thick; 3 × M2 SMT standoffs (H3.5) | [V] drawing + STEP |
| Depths behind the glass front | PCB front **5.70** · PCB back **6.90** · tallest SMD **8.70** · USB-C **10.15** · standoff tips **10.40** · MX1.25 connectors **11.70** · 8-pin header **12.70** (= STEP bounding box 48.96 × 48.96 × 12.70) | [V] STEP `ESP32-S3-Touch-AMOLED-1_75.stp` measured with CadQuery; matches `prototip/legacy-S/cad/soul_p0.py` |
| Price | **$29.99–39.99** on waveshare.com (the per-variant split is not in the page text); orderable ("Add to Cart") | [V] |
| EU / UK stock | The Pi Hut (UK, incl. VAT): Standard **£28.80**, +Case £32.70, +GPS £38.40, all **sold out** today; openelab (EU) -B €39.85, sold out | [V] Pi Hut page · [V-s] openelab |
| Romania | No Romanian seller found (eMAG / Optimus Digital / Robofun not listing it) | [V-s] search, not exhaustive |
| Power figures | none published for this board. Sibling AMOLED-2.06 owners report **deep sleep ≈ 2.1 mA**, ≈ 35 mA for a stripped firmware | [V-s] GitHub issue waveshareteam/ESP32-S3-Touch-AMOLED-2.06#6 |

**Buy plan:** order **3 Standard boards from waveshare.com directly** (EU distributors are out of stock). That is 1 for firmware, 1 for the S-P0 build and 1 spare. Add **2 × AMOLED-1.75C** for the aluminium-case RSSI test (docs/01 B-01). The extra cost is about €100 [E].

**Firmware state [R, updated 22 Oct 2026]:** `pio run -e amoled175` builds SoulOS **1.9.1** (`firmware/release/SOUL-1.75-install.bin`, sha256 `b208fbbb…`; `src/board.h`: CST9217, QMI8658, AXP2101 set up register by register). **S layout done:** the S density profile and every SoulOS Alive screen on 466 px (commits b3aee4c, b9c683d; `firmware/SOUL-S.md`). **ES8311 speaker driven** in 1.9.1 (DAC + amplifier on GPIO 46: alarms, test tone `A`; `firmware/SOUL-S.md` §4, §9). **Still to do:** the ES7210 microphones (voice) and light sleep between frames (§2.5). 245 native tests green; not yet run on a board (`firmware/BRINGUP.md` §S).

### 1.2 Bare 1.75″ round panel + custom PCB (the product path)

| Panel | Driver / touch | Interface | Outline | Price / MOQ | Tag |
|---|---|---|---|---|---|
| **Tailor-Pixels TOH175XRT-02CG** | CO5300 + CST820B, on-cell touch | MIPI / QSPI | **45.93 × 46.35 × 0.8 mm**, AA 43.76 × 43.76, 700 cd/m², cover glass optional ("CG") | **$9–17**, MOQ not stated, customisation offered | [V] tailorpixels.com |
| **NoseDisplay ND018ECG466466-A02** | **CO5300 + CST9217** (the Waveshare pair: least firmware change) | QSPI / MIPI, 24-pin | "without frame" | on request | [V-s] search snippet (page did not load) |
| **Lianxun LX175A3101CTP01** (BOE glass) | CO5300 + CST820, on-cell | QSPI / MIPI, 31-pin | 51.5 × 51.5 × 1.67 mm (likely incl. cover lens), AA 43.76 | on request; also resold by Eurocoin Components | [V-s] search snippets (pages returned 503 / empty) |
| Visionox 1.75″ CO5300 (Shenzhen trader) | CO5300 | MIPI / QSPI | – | **MOQ 10** | [V-s] Alibaba snippet |

What this says:
- **The path exists.** The panel used on the Waveshare board (CO5300, QSPI, 466², Ø43.76 active area) is sold bare by several Shenzhen module houses at **$9–17 at sample quantity**.
- **Panel + touch is ≈ 0.8–0.95 mm thick:**
  - 0.8 mm is the TOH175 listing [V];
  - 0.95 mm is the Waveshare stack: 2.05 mm total minus the 1.10 mm cover glass [V].
- **MOQ needs a quote.** Only one trader states one (10 pcs). Send the RFQ to all three named suppliers and ask for:
  - the FPC drawing;
  - the bonding (on-cell vs. separate CTP);
  - a 2nd-source plan.

  research/09 asks for a second qualified 466² panel before DVT.
- **The custom board** stays on the same architecture, so the firmware carries over:
  - ESP32-S3-WROOM-1-N16R8 (18 × 25.5 × 3.1 mm module), which keeps Espressif's radio evidence;
  - CO5300 over QSPI;
  - AXP2101-class PMU;
  - ES8311 + ES7210-class audio;
  - QMI8658;
  - 5 pogo pads in the foot.

  NRE: PCBA design $15–30k, custom glass + lamination $5–15k [R: 02-MANUFACTURING §11].

---

## 2 · Internal stack-up of the MĂRGĂRITAR S body

### 2.1 Method (reproducible)

- **Body**: `renders/v9/src/marg_geo.py` at local scale (W 62.96, H 70.8 incl. the 1.2 mm foot, glass Ø52 centred at z 38.9 on the 8°-leaning face). The back half behind the seam is compressed by `s_back`:
  - **0.735 → 22.05 mm**: the M renders' ratio;
  - **1.0 → 25.65 mm**: the shape uncompressed.
- **Available depth**: for points on the glass plane, march along the inward face normal until the ray leaves the outer surface (`ring(z)` point-in-polygon at 0.05 mm steps). Take the **minimum over a battery footprint**: the back is a superellipse, so the corners are the tight spot. Then search the footprint's height on the face for the best position.
- **Wall**: aluminium 1.4 mm (CNC variant of `soul_p0.py`), counted as **1.6 mm along the ray** for obliquity. Plastic P0 2.0 → 2.2 mm.

### 2.2 Stack, product (custom PCB), along the face normal from the glass front

| Layer | mm | Depth after it | Basis |
|---|---:|---:|---|
| Cover glass Ø52, 2.5D | 0.70 | 0.70 | [E] typical 2.5D lens; Waveshare uses 1.10 [V] |
| OCA + AMOLED panel with on-cell touch | 0.95 | 1.65 | [V] Waveshare stack 2.05 − 1.10 glass; TOH175 0.8 [V] |
| Foam / Cu-graphite sheet + gap | 0.40 | 2.05 | [E] |
| Mid-frame (polymer or Al) | 0.60 | 2.65 | [E] |
| PCB, 4-layer | 0.80 | 3.45 | [E] |
| Low parts under the battery (≤ 0.8 mm: QFN, passives) + air | 1.00 | 4.45 | [E] tall parts (WROOM 3.1, codec, pogo) go **outside** the battery footprint: there is ≥ 14.4 mm at r = 23 |
| PU foam under the cell | 0.30 | 4.75 | [E] (docs/01 P0-08: foam, never glue) |
| **Cell 603040**, 6.2 mm + **10 % swell** | 6.82 | 11.57 | [V-s] cell size; swell allowance [E] |
| Air | 0.20 | 11.77 | [E] |
| Aluminium back wall (1.4, 1.6 along the ray) | 1.60 | **13.37** | [R] `soul_p0.py` alu |

Speaker: a 15 × 11 × 3.5 mm unit (docs/01 P0-03) **in the +x seam beside the cell**, where v9 already has the slot. Mics: two ports on −x (v9 already has two holes). Pogo + magnets in the foot. Nothing is stacked behind the cell.

### 2.3 Stack, S-P0 (stock Waveshare board)

The glass sits 0.65 mm behind the face, under a 0.8 mm lip. The layers then add up as follows (first paper plan, 503035):
- tallest SMD at **8.70** [V] → 9.35 mm;
- foam 0.3 → 9.65 mm;
- **503035** cell, 5.05 + 0.5 swell → 15.20 mm;
- air 0.2 → 15.40 mm;
- wall 1.6 → **17.0 mm** (alu) or 17.6 mm (plastic).

**What the exported S-P0 uses (22 Oct 2026): a 503030-class cell, ≈ 450 mAh [E], ≈ 16 h [E].** The depth stack above holds, but the footprint does not: in the CAD (`prototip/cad/soul_p0_s.py`, batfit search of 20 Oct) the USB-C plug tunnel under the board takes the bottom of the cavity, and a 35 mm-long cell no longer fits the narrower MĂRGĂRITAR bottom. A 30 mm cell (envelope 30.5 × 31 × 5.55 mm incl. PCM tape + 0.5 swell, tilted 6°) does, with 0.43 mm to the back shell (`prototip/stl/s/README.md`). `size-s.json` `variants.S-P0_dev_board` follows the CAD. The capacity is the listing class [E] until a cell is in hand; the life is 18 h × 450 / 500 [E].

The MX1.25 plugs on the −x edge reach 14.0 mm behind the board glass (`soul_p0.py`, plug height UNVERIFIED) → 16.25 mm with the wall.

### 2.4 Available depth vs body depth, and the choice

Minimum available depth along the normal (mm) over each footprint, best position:

| Body D (s_back) | 31 × 43 (603040) | 31 × 36.5 (603035 / 703035) | 30.5 × 36.5 (503035) | Disc edge r = 23 | −x connectors |
|---|---:|---:|---:|---:|---:|
| 19.50 (0.537) | 11.6 | 12.5 | 12.6 | 11.6 | 12.0 |
| 20.50 (0.616) | 12.3 | 13.4 | 13.5 | 12.4 | 12.8 |
| 22.00 (0.731), the M renders' ratio | 13.5 | 14.6 | 14.8 | 13.6 | 13.9 |
| **23.00 (0.807)** | **14.3** | 15.5 | 15.6 | 14.4 | 14.7 |
| 24.50 (0.917) | 15.4 | 16.7 | 16.8 | 15.5 | 15.8 |
| **25.65 (1.000)**, uncompressed | 16.2 | 17.6 | **17.8** | 16.3 | 16.6 |

What fits where (needed depth → margin at the worst corner):

| Option | Needed | 22.0 mm | **23.0 mm** | 25.65 mm |
|---|---:|---:|---:|---:|
| Product + 503035, 500 mAh | 12.1 (31 × 36.5) | +2.5 | +3.4 | +5.5 |
| Product + 603035, ≈ 600 mAh [E] | 13.15 | +1.45 | +2.35 | +4.45 |
| Product + 703035, ≈ 700 mAh [E: capacity per listing varies] | 14.25 | +0.35 | +1.25 | +3.35 |
| **Product + 603040, 750 mAh** | **13.37** (31 × 43) | +0.13 ✗ | **+0.93** | +2.83 |
| S-P0 (stock board) + 503035, alu wall | 17.0 | ✗ | ✗ | **+0.8** in depth (footprint ✗ beside the USB-C tunnel, §2.3) |
| S-P0 (stock board) + 503035, plastic wall | 17.6 | ✗ | ✗ | +0.2 (tight; footprint ✗) |
| **S-P0 (stock board) + 503030, as exported** | 17.0 / 17.6 | ✗ | ✗ | **fits** (CAD: 0.43 mm to the back shell) |

Decisions:
- **Minimum realistic depth: ≈ 20.5 mm** for the product with a 500 mAh cell. That gives 13.4 available vs 12.1 needed, so 1.3 mm of margin. Below ~19.5 mm, even 500 mAh no longer has a safe margin. The back would also be compressed to about half, and MĂRGĂRITAR would stop reading as a pebble.
- **Target: 23.0 mm, 750 mAh.**
  1. A full carried day needs about **≥ 700 mAh** at today's firmware: the model day uses ≈ 661 mAh (§2.5).
  2. The standard 603040-class cell gives 750 mAh. It fits at 23.0 mm with **0.93 mm** to spare at the worst corner, after 10 % swell.
  3. At 22.0 mm the margin is 0.13 mm. That is not buildable with CNC tolerances and a pouch cell.
  4. +1 mm only fills the back half (s_back 0.807 instead of the M renders' 0.735). The face, glass, chamfer, rolls and silhouette are identical. The body is still 2.65 mm thinner than the uncompressed shape.
  5. 2.8 Wh is far below 20 Wh, so standard UN38.3 shipping applies (04-COMPLIANCE).
- **S-P0: 25.65 mm** (the uncompressed shape). It is the only depth where the stock 8.7 mm board stack plus a ≈ 450–500 mAh cell fits. The exported CAD uses a **503030-class cell (≈ 450 mAh [E])**: the 503035 fits in depth but not beside the USB-C plug tunnel (§2.3). The plastic variant is exported and checked; alu / alu_band are generated on demand.
- **Optional for S-P0:** a Ø52 × 0.7 black overlay glass over the stock glass gives the product's face. It costs +0.85 mm, taken from the 0.8 mm margin, so it fits only with a 403035-class cell [E] (research/08 §infinity glass).

Candidate cells (all 3.7 V, with PCM, 2-pin lead; check polarity vs the board, docs/01):

| Cell | Size (T × W × L) | mAh | Wh | Use | Sources |
|---|---|---:|---:|---|---|
| 503030 class | 5.0 × 30 × 30 | ≈ 450 [E] | ≈ 1.7 | **S-P0 (as exported)** | AliExpress size class, listing capacity [E] |
| 503035 | 5.05 × 30.0 × 35.5 | 500 | 1.85 | first S-P0 plan (does not fit beside the USB-C tunnel); product fallback | [V-s] PKCell LP503035 sheet (TI-hosted), BerryBase, Welectron; eBay.de €6–9 |
| 603035 | 6.0 × 30 × 35 | ≈ 600 [E] | ≈ 2.2 | product fallback | AliExpress size class [E] |
| **603040** | **6.2 × 30.5 × 42** | **750 typ / 720 min** | **2.8** | **product (EVT)** | [V-s] A&S Power listing (HKTDC): 4.2 V charge, 750 mA max charge/discharge, UL2054/CB/KC; eBay.de 800 mAh listings of the same size class |
| custom pouch | ≤ 6.2 × 31 × 43, top corners cut to the back curve | 750–800 [E] | ≈ 2.9 | product (DVT, IEC 62133-2 + UN38.3) | 02-MANUFACTURING §11 |

### 2.5 Battery life (same day as docs/09 §3)

docs/09's model day: 1 h awake, 15 h asleep or screen off, 8 h night deep sleep, 50 questions. The S currents are built bottom-up [E].

- **CPU:** PERF.md's model, ESP32-S3 modem sleep. 33 mA at idle at 240 MHz, plus 29 mA × core-1 duty. **Redone 2026-10-22 with PERF.md's "SOUL S" table (firmware 1.9.1):** a standby frame is 8.1 ms render + 8.1 ms push + 1 ms loop = 17.2 ms at 24 fps = **41 % duty** → ≈ 45 mA (the first estimate used 28 % → 41 mA).
- **QSPI push:** ≈ 54 k px a standby frame, 8.1 ms at the estimated 16 MB/s payload [E] → +≈ 7 mA at 24 fps (first estimate: 5.7 ms at the raw 20 MB/s, +5 mA).
- **Charge voltage:** firmware 1.9.1 charges to **4.2 V** (the cell's rating; `firmware/SOUL-S.md` §8). At xiaozhi's 4.1 V about 10 % of the capacity would go unused [E] (≈ 23 h instead of ≈ 26 h).
- **AMOLED:**
  - static (driver + DC-DC) ≈ 10 mW;
  - full white at the 1.75″ size ≈ 250–350 mW [E: watch panels scaled by area, no panel datasheet with a power table found];
  - SoulOS Alive keeps the eyes on black, so the average picture level is ≈ 10–15 % → **≈ 10–20 mA**.

  A full-white screen (maps, a white app) would add ≈ 60–90 mA while it is on.
- **The M board** spends most of its 177–227 mA on the IPS backlight [R: BRINGUP §4].

| State | M (2.8C, IPS) [R] | **S (AMOLED)** [E] |
|---|---|---|
| Awake, eyes, Wi-Fi modem sleep | 177–227 mA | **70–100 mA** (CPU ~45, panel 10–20, Wi-Fi + touch + IMU + PMU ~15) |
| Asleep glow (eyes closed, 10 fps) | 70–100 mA | 40–50 mA |
| Screen off (Mode Off, 80 MHz) | 35–60 mA | 25–35 mA (panel sleep-in) |
| Deep sleep | ≈ 0 (docs/09) | dev board ≈ 2 mA [V-s, sibling board]; custom PCB ≤ 0.3 mA target |
| **mAh per model day** | ≈ 1,130 | **≈ 661** (85 + 15 h × 38 + 2 + 4) |
| **Battery life** | 1500 mAh → **≈ 32 h** | **750 mAh → ≈ 27 h** (21–34 h); S-P0 ≈ 450 mAh (503030) with a 2 mA deep sleep → ≈ 16 h (≈ 18 h with the 500 mAh first planned) |

**Redo with the 1.9.1 numbers [E] (`firmware/SOUL-S.md` §8):** awake ≈ 77–87 mA, asleep glow ≈ 45–55 mA, screen off 25–35 mA → ≈ 690 mAh for the model day → **≈ 26 h** (21–33 h). The ≈ 27 h above stays inside that range; both wait for BRINGUP §S-f's meter.

**The AMOLED's other win:** the panel keeps its own frame memory (GRAM), so the S3 may **light-sleep between frames and while the screen is dark**. On the M's RGB panel that is impossible: the DMA must keep scanning [R: PERF.md *Power*]. Two numbers drive the gain:

| | Today's firmware | With light sleep |
|---|---|---|
| Asleep glow | 40–50 mA | ~20 mA |
| Screen off | 25–35 mA | ~6–8 mA |
| Blended over the 15 h | ~38 mA | ~15 mA |
| Model day | ≈ 661 mAh → **≈ 27 h** | ≈ 316 mAh → **≈ 55 h (≈ 2 days)** |

- It is a firmware task for SoulOS on S, not hardware: explicit `esp_light_sleep_start()`, because Arduino's prebuilt core has no `esp_pm` dynamic frequency scaling [R: PERF.md].
- Measure it on the AMOLED-1.75 with BRINGUP §5d's method before promising either figure.

---

## 3 · What changes in cost and in the factory

### 3.1 BOM delta per unit, S vs M

The table uses the factory model's lines and conventions (`docs/factory/SOUL-fabrica-model.xlsx`, sheet *Scenarii*):
- EUR, net of VAT;
- $1 = €0.87;
- logistics ≈ 12 % of imports at 100 and ≈ 8 % at 1,000.

| Line | M @100 (Waveshare 2.8C) [R] | **S @100 (Waveshare AMOLED-1.75)** | M @1000 (own PCB) [R] | **S @1000 (own PCB)** |
|---|---:|---:|---:|---:|
| Electronics | 45.35 (board $39.99 + INMP441 + MAX98357) | **26.09** (board $29.99; mics, codec, speaker header on board) [V price] | 18.67 (2.8″ panel $12 + WROOM $3.46 + parts $5 + PCB $1) | **16.76** (1.75″ panel $10 [E: $9–17 list] + WROOM $3.46 + parts $5 + PCB $0.8) |
| Battery | 3.92 (803450 1500 mAh) | 3.00 (503030 class, S-P0) [E] | 1.83 | 1.31 (603040 750 mAh, $1.5) [E] |
| Front glass 2.5D | 6.96 | 5.22 (Ø52, set-up dominated) [E] | 2.61 | 1.91 (area × 0.49) [E] |
| Speaker + small mech + cable | 7.27 | 5.70 (no extra speaker: kit) [E] | 4.50 | 4.00 [E] |
| Transport + duty | 7.75 | 4.88 | 2.24 | 1.95 |
| Local: OU + packaging + chassis/foot | 34.00 (18 + 10 + 6) | 28.50 (15 + 9 + 4.5) [E] | 21.00 | 17.60 (10 + 5 + 2.6) [E] |
| **BOM delivered (no shell, no labour)** | **105.24** | **73.39** (−31.9) | **50.85** | **43.53** (−7.3) |
| Shell, external (CNC + blast + anodise, delivered) | 109.30 | **71.0** (× 0.65) [E] | 47.46 | **30.85** (× 0.65) [E] |
| **Hardware per unit** | **214.5** | **≈ 144.4 (−70, −33 %)** | **98.3** | **≈ 74.4 (−24, −24 %)** |

- The shell factor × 0.65 is [E]. The geometry gives surface × 0.50 and billet × 0.40 vs M (§3.2). External prices keep a fixed set-up and handling share. The model already used × 0.75 for S+ (70 × 79 mm), and S is ≈ 0.81 of S+'s face area.
- The model also adds 21 % non-deductible VAT at 100 units, and PCBA €4 at 1,000. Both are unchanged by the size.
- docs/01's S tables (P0 and Founders 00 @25, ≈ €190 hardware per unit) remain the per-part reference for small S batches. The only change is the battery line: 750 mAh in the product, ≈ 450 mAh (503030 class) in S-P0.

### 3.2 CNC and material

| | M (v9, 31.5 deep) | **S (23.0 deep)** | S / M |
|---|---:|---:|---:|
| Outer volume | 159.5 cm³ | 57.5 cm³ | 0.36 |
| Outer surface (machined + blasted + anodised) | 195.8 cm² | 97.2 cm² | 0.50 |
| Shell at 1.4 mm uniform wall | 27.4 cm³ · 74 g | 13.6 cm³ · 37 g (≈ 46 g with seat, bosses, ribs) | 0.50 |
| Billet, two plates (front + back halves, +2 mm stock, +3 mm hold) | 0.90 kg (model: 1.0) | **0.36 kg → 0.40 kg** with the model's +11 % | 0.40 |
| Removed material | 307.5 cm³ | 119.6 cm³ | 0.39 |
| CNC cycle per set | 45 min [R: model `ct_M`, E] | **≈ 24 min** [E] (20–30) | 0.53 |
| Sets per machine per shift (408 productive min) | 9.1 | **≈ 17.0** | 1.9 |
| Sets per machine per year (1 shift, 220 days) | 1,995 | ≈ 3,740 | 1.9 |

- **How the cycle time was scaled** (shares [E]): 40 % roughing scales with removed volume (× 0.39), 45 % finishing scales with surface (× 0.50), 15 % fixed (probing, tool changes, flips) does not scale → 45 × 0.53 ≈ 24 min.
- Check it with a CAM simulation on the S STEP. That STEP does not exist yet; the next CAD job is the production body at 23.0 mm.
- **Inputs to add to the model** (sheet *Ipoteze*): `ct_S = 24`, `mat_kg_S = 0.40`, external shell factor 0.65.
- What these do: an S cell machine pays back at roughly half M's volume per machine. One machine on one shift covers ~3,700 S sets a year.

Per unit, the anodise and blast cost scales with surface (× 0.5); the lot fees do not. Laser marking on the foot is unchanged.

---

## 4 · Risks and next steps

1. **Antenna in aluminium.** The S body is half the M's surface, and the WROOM's antenna must look out through polymer.
   - Place the module with its antenna toward the polymer base plate. The S base is ≈ 38 × 16 mm [E: v9 M base 54 × 23 ÷ K].
   - Or use the seam band (`alu_band`, 3 mm).
   - Run the RSSI test with the 2 × AMOLED-1.75C aluminium-case boards (docs/01 B-01) before the EVT layout.
2. **Battery corner margin 0.93 mm.** Verify it in the production CAD with the cell's real drawing, including the PCM and lead exit. If it fails, fall back to 603035 (≈ 600 mAh → ≈ 22 h), or cut the custom pouch's top corners to the back curve.
3. **Single-source panel.** Qualify two of the §1.2 panels. The CO5300 + CST9217 pair (NoseDisplay) needs no touch-driver change.
4. **Power numbers are estimates.**
   - Run BRINGUP §5d on the AMOLED-1.75: awake with eyes, asleep glow, screen off, deep sleep.
   - Run a white-screen test.
   - Put the measured values into §2.5 and `size-s.json`.
5. **Firmware for S.** Done in 1.9.1: the 466 px Alive layout and the ES8311 speaker. Still to do: the ES7210 microphones and light sleep between frames.
6. **Stability.** The base narrows to ≈ 38 × 16 mm at S [E]. research/09 and the v9 README already flag tip-over. Test it on the S-P0 at 85–90 g.
7. **CAD.**
   - Production S body at **23.0 mm**: s_back 0.807 in `marg_geo.MargaritarV9(s_back=0.807)`, plus a chassis for the custom stack.
   - S-P0 at **25.65 mm**: done (22 Oct 2026). `prototip/cad/soul_p0_s.py` ports `prototip/legacy-S/cad/soul_p0.py` from HOPA to `marg_geo` at s_back 1.0, with a 503030-class cell (§2.3); plastic variant exported (`prototip/stl/s/`, `prototip/step/s/`).

Unchanged by this document: the 5 anodised colours, the living eyes (120 designs, rarities), the SoulOS Alive design (`os/DESIGN-ALIVE.md`), the owner's own AI (never included), no camera, no CE yet, from €249. The M prototype (2.8C, SoulOS 1.9.1, `release/SOUL-2.8C-install.bin`) stays the test and PoC TRL 3 device.

---

## Sources (checked 20 Oct 2026)

- [V] Waveshare product page: https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm (spec list, variants, $29.99–39.99, Add to Cart)
- [V] Waveshare wiki: https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-1.75 and its resources page (schematic, `ESP32-S3-Touch-AMOLED-1.75-3D.zip` with the dimension drawing PDF + STEP, ES8311 / AXP2101 / QMI8658 / PCF85063 datasheets)
- [V] The Pi Hut: https://thepihut.com/products/esp32-s3-1-75-amoled-round-touch-display-dev-board-466x466 (Standard £28.80, +Case £32.70, +GPS £38.40, sold out)
- [V-s] openelab ESP32-S3-Touch-AMOLED-1.75-B €39.85 (sold out): https://openelab.io/a/s/products/waveshare-esp32-s3-1-75inch-amoled-round-touch-display-with-case
- [V-s] Waveshare AMOLED-2.06 power reports: https://github.com/waveshareteam/ESP32-S3-Touch-AMOLED-2.06/issues/6 · https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-2.06 (FAQ: 400 mAh ≈ 1 h full light, 3–4 h screen off)
- [V] Tailor-Pixels TOH175XRT-02CG: https://tailorpixels.com/product/1-75-inch-amoled-round-on-cell-touch-466x466-mipi-qspi/
- [V-s] NoseDisplay ND018ECG466466-A02: https://www.nosedisplay.com/products/amoled-1-75-inch-round-display-466x466-resolution-700nits-qspi-interface/
- [V-s] Lianxun LX175A3101CTP01: https://www.lxdisplay.com/Product_details/1349774513965064192.html · Eurocoin: https://eurocoincomponents.com/products/ART212341/
- [V-s] Alibaba, Visionox 1.75″ CO5300, MOQ 10: https://electronics.alibaba.com/product/smart-watch-spare-parts-display
- [V-s] Cells: LP503035 sheet https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/LP503035-500mAh-with-JST-PHR_2D00_2.pdf · BerryBase https://www.berrybase.de/en/lp-503035-lithium-polymer-lipo-battery-3.7v-500mah-with-2-pin-jst-connector · Welectron https://www.welectron.com/LiPo-Pouch-Battery-503035-37V-500mAh · A&S Power 603040 https://www.hktdc.com/event/hkelectronicsfairae/en/product/1X24UT0L
- [R] `renders/v9/src/marg_geo.py`, `renders/v5/src/alt_geo.py`, `prototip/legacy-S/cad/soul_p0.py`, `prototip/README.md`, `firmware/PERF.md`, `firmware/BRINGUP.md`, `docs/09-EVERYWHERE.md` §3, `docs/01-BOM.md`, `docs/02-MANUFACTURING.md` §11, `docs/factory/SOUL-fabrica-model.xlsx`
