# Firmware „Suflet” v0 — sufletul companionului

Ochii vii, dispoziția, cele 24 de reacții, personalitatea născută din cip și legătura
„works with Claude”. Rulează pe plăcile Waveshare cu AMOLED rotund 466×466.

| Placă | Mediu PlatformIO | Ce are |
|---|---|---|
| ESP32-S3-Touch-AMOLED-1.43 | `amoled143` | ecran, touch FT3168, IMU, RTC — fără sunet |
| ESP32-S3-Touch-AMOLED-1.75 | `amoled175` | + 2 microfoane, difuzor, PMU AXP2101, buton de pornire |

```bash
pio run -e amoled143 -t upload      # sau amoled175
pio device monitor -b 115200        # tastezi ? pentru comenzi
pio test -e native                  # 24 de teste pe PC
pio run -e sim && .pio/build/sim/program /tmp/out all   # simulatorul (cadre brute)
python3 tools/frames_to_media.py /tmp/out ../media --mp4 --gif --sheet
```

## Structura
- `lib/Suflet/src/` — **sufletul, fără hardware** (C++17): `Canvas` (randare SDF anti-aliased),
  `Face` (ochi parametrici), `Brain` (dispoziție, atenție, reacții, moduri), `Personality`
  (semința din cip → nuanță, rarități, temperament), `Gestures` (tap/ținere/mângâiere, ridicare,
  scuturare, cădere, ciocănit, orientare), `ClaudeLink` (protocolul Hardware Buddy al Claude Desktop).
- `src/` — placa: `main.cpp` (bucla, ecran cu randare parțială, touch, IMU, ceas, baterie, memorie
  NVS, comenzi seriale, bucla demo), `board.h` (pini), `ble_link.cpp` (Bluetooth securizat, adaptat
  din anthropics/claude-desktop-buddy, MIT).
- `sim/` — simulatorul pe PC: aceleași fișiere din `lib/Suflet`, evenimente scriptate → cadre.
- `test/` — teste Unity pe PC.

## Legarea cu Claude
Claude Desktop → Help → Troubleshooting → **Enable Developer Mode** → Developer → **Open Hardware
Buddy…** → Connect → „Claude-Suflet-XXXX” → codul de 6 cifre de pe ecran.
Ține degetul 1,2 s = aprobă · dublu-tap = refuză · tap simplu = doar boop.

## De calibrat pe placa reală (5 minute)
- Panou SH8601 în loc de CO5300 → `-DSUFLET_PANEL_SH8601`.
- Imagine rotită → `-DSUFLET_ROTATION=90|180|270`.
- Touch oglindit → `TOUCH_MIRROR_X/Y` în `board.h`.
- Axele IMU → `IMU_MAP` în `board.h` (comanda serială `i`: fața în sus ≈ (0,0,+1)).

## Neverificat încă pe hardware
Codul compilează pentru ambele plăci și logica e testată pe PC, dar placa fizică n-a fost încă în
mână: orientarea ecranului, sensul touch-ului/IMU, luminozitatea și împerecherea BLE cu Claude
Desktop se confirmă la primul flash.
