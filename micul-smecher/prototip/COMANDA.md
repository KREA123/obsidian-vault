# Ce comanzi azi: SOUL-P0 mărimea M

Aceasta e lista minimă pentru SOUL-P0 M (placa Waveshare 2.8C, corp de 112 × 128 × 34 mm, aspect v6), în varianta cea mai rapidă: **carcasa printată online în România**. Detaliile sunt în [README.md](README.md).

Prețurile sunt aproximative (septembrie 2026) și includ TVA. Am folosit 1 € ≈ 5,1 lei și 1 $ ≈ 4,4 lei.

## 1. Electronica (AliExpress + magazine RO)

| # | Ce comanzi | Unde | 1 buc. | 3 buc. |
|---|---|---|---|---|
| 1 | **Waveshare ESP32-S3-Touch-LCD-2.8C** (varianta **cu touch**, rotundă, 480×480) | [waveshare.com](https://www.waveshare.com/esp32-s3-touch-lcd-2.8c.htm) sau [AliExpress](https://www.aliexpress.com/item/1005009311521684.html) | 190 | 570 |
| 2 | **LiPo 605060**, ~2000 mAh, 3,7 V, PCM, mufă **MX1.25** (sau PH2.0 + adaptor). Ia **una în plus** | AliExpress: „605060 2000mAh MX1.25” | 35 | 140 (4 buc.) |
| 3 | **Difuzor 2030**, 8 Ω, 1 W (cutie de 20 × 30 × 5) | AliExpress / eMAG | 12 | 36 |
| 4 | **MAX98357A**, amplificator I2S | [ArduShop](https://ardushop.ro/en/modules/1549-max98357-i2s-3w-class-d-amplifier-6427854022967.html) / [Optimus](https://www.optimusdigital.ro/ro/audio-amplificatoare-audio/1656-modul-cu-amplificator-adafruit-i2s-de-3-w-in-clasa-d-max98357a.html) | 25 | 75 |
| 5 | **INMP441**, microfon I2S | [eMAG](https://www.emag.ro/modul-microfon-inmp441-omnidirectional-i2s-24-biti-mems-12-x-14-x-3-mm-negru-s9/pd/D83G1QYBM/) / [ArduShop](https://ardushop.ro/ro/home/2092-omnidirectional-microphone-module-i2s-interface-inmp441-mems-high-precision-low-power-ultra-small-volume-for-esp32.html) | 20 | 60 |
| 6 | **Prelungitor USB-C**, tată la 90° → mamă de montaj pe panou, 10–20 cm | AliExpress / eMAG | 25 | 75 |
| | **Subtotal electronica** | | **≈ 307 lei** | **≈ 956 lei** |

## 2. Mărunțișuri (un set, ajunge și pentru 3 bucăți)

| Ce | Preț |
|---|---|
| Inserții M2 la cald ([set eMAG](https://www.emag.ro/set-300-insertii-filetate-jormftte-m2-m2-5-m3-m4-m5-m6-alama-auriu-mc-1017-017/pd/DFGRH7YBM/)) | 40 |
| Șuruburi M2 inox. **Pe bucată:** 2 × M2×16, 2 × M2×8, 2 × M2×6 cu cap înecat. Un set mixt | 35 |
| 3M VHB, spumă EVA de 0,5–1 mm, bandă Kapton | 60 |
| Fire siliconice de 26–28 AWG, tub termocontractabil | 25 |
| **Subtotal** | **≈ 160 lei** |

## 3. Carcasa: print online (România)

Comanzi de la [printeaza3d.ro](https://printeaza3d.ro/) sau [capib.ro](https://capib.ro/3dprint/en/3d-printing-romania/). Urci fișierele din `stl/plastic/`: față, spate, placa de bază, șasiu și 2 știfturi.

| Variantă | 1 set | 3 seturi |
|---|---|---|
| **FDM PETG** (probă de potrivire, recomandat primul) | ≈ 180 lei | ≈ 480 lei |
| SLA rășină (netedă, gata de vopsit), în loc de FDM | ≈ 450 lei | ≈ 1 200 lei |

## 4. Scule (o singură dată, dacă nu le ai)

| Ce | Preț |
|---|---|
| Letcon reglabil (Pinecil / TS101 sau 60 W) + vârf pentru inserții | 150–350 |
| Șubler digital | 70 |
| Șurubelnițe de precizie | 60 |
| Hârtie abrazivă 400–2000, grund de umplere, vopsea, lac | 150 |
| Multimetru (polaritatea bateriei!) | 70 |
| **Subtotal** | **≈ 500–700 lei** |

## Total

| | **1 bucată** | **3 bucăți** |
|---|---|---|
| Electronica | 307 | 956 |
| Mărunțișuri | 160 | 160 |
| Carcasă FDM (online) | 180 | 480 |
| Scule | 500–700 | 500–700 |
| **TOTAL cu FDM** | **≈ 1 150–1 350 lei (≈ 225–265 €)** | **≈ 2 100–2 300 lei (≈ 410–450 €)** |
| TOTAL cu SLA în loc de FDM | ≈ 1 420–1 620 lei | ≈ 2 820–3 020 lei |
| *Fără scule (dacă le ai)* | *≈ 650 lei* | *≈ 1 600 lei* |

## Opțional, mai târziu

- **Imprimanta ta:** Bambu Lab A1 mini, ≈ 1 400–1 600 lei (Combo ≈ 2 800), + 1 kg PLA Matte, ≈ 120 lei. Merită dacă faci mai mult de 3–4 iterații.
- **Aluminiu CNC**, după ce potrivirea în plastic e OK. Urci `step/alu/*.step.gz` (dezarhivat) pe JLCCNC sau PCBWay: 6061-T6, sablare + anodizare, filet M2 în cele 4 găuri Ø1,6.
  - estimat **$180–350 / set** la 1 set;
  - **$120–250 / set** la 3 seturi;
  - plus transport și vamă.
  - Placa de bază și șasiul rămân printate.

## Ordinea (ce faci azi și săptămâna asta)

1. **Azi:**
   - comanzi electronica (1) și mărunțișurile (2);
   - trimiți STL-urile de **șasiu + placă de bază** la print FDM (e ieftin: ~40 lei).
2. **Când vine placa:**
   - verifici cotele cu șublerul (README §E1);
   - apoi comanzi carcasele față + spate (FDM sau SLA).
3. **După prima potrivire bună:** vopsești (README §F) sau comanzi aluminiul (README §C).
