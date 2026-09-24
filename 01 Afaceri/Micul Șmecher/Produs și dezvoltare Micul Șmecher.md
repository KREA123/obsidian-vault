---
tip: produs
afacere: Micul Șmecher
status: activ
actualizat: 2026-09-24
---
# Produs și dezvoltare — Micul Șmecher

## Ce cumperi azi (kitul de prototip, ~€120)
| Piesă | De ce | Preț | Link |
|---|---|---|---|
| **Waveshare ESP32-S3-Touch-AMOLED-1.43** (fără carcasă) | ediția Founders „works with Claude”; firmware-ul merge pe ea azi | ~$27 | waveshare.com/esp32-s3-touch-amoled-1.43.htm (sau Eckstein DE ~€32) |
| **Waveshare ESP32-S3-Touch-AMOLED-1.75** | prototipul de voce: 2 microfoane cu anulare de ecou, difuzor inclus, IMU, PMU, buton de pornire | $30–40 | waveshare.com/esp32-s3-touch-amoled-1.75.htm |
| LiPo 400–500 mAh cu protecție (ex. Adafruit #3898, 36×17×7,8 mm) | doar pentru 1.75 / variantele de geantă | ~$7 | adafruit.com |
| Comutator mini (MSK-12C02) + cablu cu mufă 1,25 mm | 1.43 nu are buton de oprire | ~€2 | orice magazin de componente |
| Cablu USB-C de date | flash + alimentare | — | — |
| (opțional) DRV2605L + motor LRA | vibrații „tors” | ~$10 | adafruit.com #2305 |

⚠️ **Placa 1.43 încarcă bateria cu ~2 A** (rezistența R23 = 82 kΩ) — periculos pentru o baterie mică. Pentru Founders folosim **doar USB, fără baterie**. Dacă pui baterie: R23 → 820 kΩ (0,2 A) sau o baterie mai mare. Pe 1.75, firmware-ul nostru setează încărcarea la 200 mA.

## Firmware — cum îl pui pe placă (Windows)
1. Instalezi VS Code + extensia PlatformIO.
2. Deschizi folderul `micul-smecher/firmware`.
3. Conectezi placa → `pio run -e amoled143 -t upload` (sau `amoled175`).
4. Serial Monitor la 115200 → tastezi `?` pentru comenzi (`b` boop, `d` amețit, `v` inimioare, `r` zi de naștere, `D` bucla demo pentru filmat…).
5. Dacă imaginea e deplasată cu 6 pixeli sau „zgomot”: panoul e SH8601 → adaugi `-DSUFLET_PANEL_SH8601` în `platformio.ini`.
6. Dacă touch-ul e oglindit: `TOUCH_MIRROR_X/Y` în `src/board.h`. Dacă ochii „se rostogolesc” invers la înclinare: `IMU_MAP` (comanda `i` arată valorile brute).

### Legarea cu Claude (Founders Desk Edition)
Claude Desktop (Windows/Mac) → **Help → Troubleshooting → Enable Developer Mode** → **Developer → Open Hardware Buddy…** → **Connect** → alegi „Claude-Suflet-XXXX” → introduci codul de 6 cifre afișat pe ecran. De atunci se reconectează singur. Când Claude cere aprobare: **ții degetul 1,2 s = aprobi**, **dublu-tap = refuzi**; un simplu tap e doar boop (nu aprobă niciodată nimic din greșeală).

## Ce face firmware-ul azi (v0)
- Ochi randați anti-aliased cu strălucire, pleoapa „șmecheră”, privire cu arc elastic, clipit, respirație.
- **24 de reacții**: boop, râs, rușine, tors, amețit (apoi bosumflat 10 s), speriat la cădere, confuz cu capul în jos, căscat, strănut, sughiț, ochi-inimioare, zi de naștere, „mi-a fost dor”, singurătate, tresărit la ciocănit, noapte bună, ascultă/gândește/vorbește (AI), salut/sărbătoare/„nu-nu” (Claude).
- Moduri: treaz → somnoros → adormit (Zzz, lumină de veghe noaptea) → oprit cu fața în jos. Noaptea ochii devin chihlimbarii.
- **Personalitate unică din cip**: nuanța ochilor cu rarități (Cream 58%, Ice 16%, Mint 10%, Peach 9%, Lilac 6%, **Gold 1%**), timiditate, curiozitate, somnolență, ritmul clipitului, micro-variații ale feței.
- Memorie persistentă (boop-uri, zile), „mi-a fost dor” după ≥ 4 h, zi de naștere anuală, momente rare o dată pe zi (strănut 1/50, sughiț 1/500, inimioare 1/5000; al 20-lea boop al zilei = inimioare).
- Ecranul se trimite doar pe zona care s-a schimbat (rapid, economic). 30 fps treaz, 12 adormit, 2 oprit.

## Arhitectura (de ce e solidă)
- `lib/Suflet` = sufletul, **fără hardware**: rulează identic pe placă, în simulatorul de pe PC și în teste (24 teste automate).
- `src/` = stratul de placă: ecran, touch, IMU, ceas, baterie, Bluetooth, memorie.
- `ai/` = creierul din cloud (Claude): personaj, conversație, memorie, mementouri, jurnal.
- Simulatorul produce clipurile de marketing **din codul real** (`media/`).

## Prototipul în 14 zile
| Zi | Ce |
|---|---|
| 1 | comanzi plăcile (livrare 5–10 zile din UE) |
| 1–7 | între timp: pagina de așteptare, marca, domeniul; carcasa se printează (JLC3DP/PCBWay, rășină transparentă) |
| 8 | flash + pairing cu Claude; calibrezi touch/IMU (5 minute) |
| 9–10 | asamblezi în carcasă, șlefuiești mat (400→1500 + lac mat) |
| 11–13 | filmezi: gestul-semnătură, boop, somn, Claude cere aprobare — lumină naturală, fundal neutru, telefon pe stativ |
| 14 | publici primul clip + deschizi rezervările |

## Drumul spre producție (după Poarta B)
EVT (10–50 bucăți, PCB propriu cu **ESP32-S3-WROOM-1**, contract cu un inginer EE) → DVT (matriță aluminiu, 50–200 bucăți, începe certificarea) → PVT (300 bucăți la EMS: Seeed Fusion / PCBWay, sau asamblare finală în România: Kimball, Helbako, Etron) → producție. Total 16–30 săptămâni, $65–210k (reper industrie).
Reguli: preț ≥ 2,5× costul livrat; baterii testate la îmbătrânire; **fără bani de pre-comandă pentru un produs care n-a trecut DVT** (lecția Coolest Cooler / Pebble).

### Lista de piese la producție (fără cameră și ToF în v1)
AMOLED rotund 1,2–1,43″ €8–15 · ESP32-S3-WROOM-1 ~€3 · 2 microfoane + difuzor + amplificator ~€3 · baterie 500 mAh + încărcare ~€5 · IMU + haptic ~€2 · carcasă (PC mat / ceramică / aluminiu) €5–25 · lentilă bombată ~€1–3 · cutie €3–10 · asamblare + test ~€5. **Total ~€35–55 la 1.000 bucăți**, ~€25–38 la 10.000 (estimări).

## Legat de
[[Micul Șmecher]] · [[Conformitate și riscuri Micul Șmecher]] · [[Planul de bani Micul Șmecher]]
