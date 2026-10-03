# SOUL M bring-up: the first 15 minutes on a real 2.8C

*Waveshare ESP32-S3-Touch-LCD-2.8C, firmware 1.1.0. Nothing below has run on a board yet: every line
is either "verified on the PC" (native tests, the simulator) or "expected, check it". This page is the
checklist that turns the second kind into the first. Write the numbers you measure into the table at
the end and commit them.*

## What you need

- the board, a USB-C data cable, a Li-ion cell on the MX1.25 connector (optional for the first run)
- Chrome or Edge on a computer (for the web flasher), or PlatformIO
- a phone on the same Wi-Fi you want SOUL on
- optional: an Anthropic or OpenAI API key with a monthly spend limit; a SOUL Cloud address if one is running
- optional: a USB power meter (for the mA lines)

## 0 · Flash (2 min)

**Without tools:** open <https://espressif.github.io/esptool-js/>, *Connect* (pick the USB JTAG/serial
port), set **Flash Address `0x0`**, choose `release/SOUL-2.8C-install.bin`, *Program*. It is one merged
image (bootloader, partition table, app); erase is not needed. Then press **RESET**.

**With PlatformIO:** `pio run -e lcd28 -t upload && pio device monitor -b 115200`.

If the port does not show up: hold **BOOT**, tap **RESET**, release BOOT, try again.

## 1 · Boot log (1 min) — expected lines on the serial monitor

```text
[board] LCD-2.8C 480x480  [imu] ok  [rtc] ok  psram ~7xxx KB free
[lcd] ST7701 480x480 RGB565, 2 PSRAM frame buffers, 10-line bounce buffers, pclk 18.0 MHz
[touch] ok
[soul] chip XX:XX:XX:XX:XX:XX: design #nnn <Name> (<rarity>, 1 in N)
[store] 0 alarms, 0 notes, 0 reminders
```

- [ ] `[touch] NOT FOUND` → GT911 address select timing; see `touchInit()` (vendor 150/150/50 ms).
- [ ] `[exio] TCA9554 NOT FOUND` → nothing else will work; check I2C SDA15/SCL7.
- [ ] The design is the one `eyes.js` `rollFromChipId()` gives for this chip id (the roll is unit-tested
      against `eyes.js`; `node -e "const E=require('../eyes/eyes.js');console.log(E.rollFromChipId(require('../eyes/designs.json').designs,'XXXXXXXXXXXX'))"`).

## 2 · The picture (2 min)

- [ ] First boot: the chip id types out on the top rim, the eyes open, the design name appears.
- [ ] **Orientation**: the rim text reads upright with the USB port at the bottom. If not, rebuild with
      `-DSUFLET_ROTATION=180` (or 90/270).
- [ ] **No drift / tearing**: the eyes stay put for a minute. A picture that is shifted sideways or rolls
      means the bounce-buffer timing: raise `-DLCD_BOUNCE_LINES=20`, or lower `LCD_PCLK_HZ` to 16 MHz.
- [ ] **NVS write glitch** (known risk): in Settings, change Brightness 5 times quickly. Each change writes
      NVS; with the RGB panel the bounce-buffer DMA starves while flash is written. Expected: at most a
      one-frame flicker, no lasting shift (the firmware restarts the panel at the next VSYNC after every
      write: `soulFlashWritten()`). A lasting shift → note it; the real fix is
      `CONFIG_SPIRAM_XIP_FROM_PSRAM` + `CONFIG_LCD_RGB_ISR_IRAM_SAFE` via `custom_sdkconfig` (docs/07 §6.5).

## 3 · Touch and gestures (2 min)

- [ ] Tap the birth screen → name suggestions; tap one → "Who helps me think?". Taps land on the word you
      touched (if mirrored: `TOUCH_MIRROR_X/Y` in `board.h`).
- [ ] Pick **No AI** → Next → "Hold the glass": hold a finger 1 s → home.
- [ ] Home: tap = boop, double tap = laugh, stroke = purr, swipe ←/→ = the app orbit, swipe up = Today,
      swipe down or **BOOT** = back one level, hold BOOT 1.5 s = home.
- [ ] **Alarm in 3 touches**: orbit → Alarms → `+ New` → drag the hour ring → let go → ✓.
- [ ] Pick the board up → the eyes wake (IMU pick-up); shake → dizzy. If they react to the wrong
      tilt, fix `IMU_MAP` in `board.h` (next section).

## 3b · IMU axes and the eyes' motion (3 min)

The eyes keep level, roll their pupils, get dizzy and read nods from the QMI8658 (accel ±4 g at 125 Hz,
gyro ±1024 dps at 112 Hz, both read at 100 Hz in the loop; `lib/Suflet/src/EyeMotion.*`, the same math
as `eyes.js` Motion, unit-tested against it). It all hangs on one thing: the axes. The device frame is
**+X right, +Y up (to the ring), +Z out of the glass**, as you look at the screen with the USB port at
the bottom. Type `i` on the serial monitor in each pose:

| Pose | accel (g) should read | gyro while you do it |
|---|---|---|
| Lying face up on the table | `0.00 0.00 +1.00` | ~0 (a few dps of offset is normal: it is learned at rest) |
| Standing on its bottom edge (USB down) | `0.00 +1.00 0.00` | |
| Standing on its right edge | `-1.00 0.00 0.00` | getting there from upright (turning it **clockwise** as you look at it): `gz` < 0 |
| Tipping the top edge toward you | `ay` falls, `az` goes negative | `gx` > 0 |
| Turning it to its right (yaw, like shaking your head) | | `gy` > 0 |

- [ ] If an axis is swapped or flipped, set `IMU_MAP` in `board.h` (it maps accel **and** gyro, so
      one fix covers both), e.g. `#define IMU_MAP(ax, ay, az, X, Y, Z) do { X = -(ay); Y = (ax); Z = (az); } while (0)`.
      `[imu] ok` with `(NO GYRO)` in the `i` line = the gyro did not start; everything but nods and the
      gyro part of dizzy still works from the accelerometer.
- [ ] **Level keeping**: stand it up and turn it slowly in the glass plane: the eyes counter-rotate
      and stay level with the floor (a little lag and overshoot). Past ~120° they ease to a stop at
      150°; on its head → shocked. The `i` line shows `level NN deg`.
- [ ] **Marble pupils**: tip it back and forth, left and right: the pupils roll to the low side and
      drift back to the middle in ~2 s.
- [ ] **Spin**: turn round on an office chair holding it (or spin it on the table): wobble, then
      spiral pupils; stop → "ufff" (droopy lids, slow double blink).
- [ ] **On its back** → it looks up at you; **face down** → a grumble, dim, then sleep (as before);
      **in a hand, held still** → calmer lids (`calm` in the `i` line).
- [ ] **Double tap** the back or the side of the case → the approve tick. If ordinary handling
      triggers it, raise `TapDetector::tapG` (0.25 g); if firm taps do not, lower it to 0.18.
- [ ] **Nod / shake** with a Claude request open (amber rim): nod = approve, tilt left-right = deny
      (each needs three quick swings, so handling does not answer by accident).
- [ ] `M` toggles the eyes' motion off/on if you need to compare.

## 4 · Performance and power (3 min)

Type `F` on the serial monitor for the on-screen overlay; every 5 s the log prints:

```text
[perf] 30.0 fps (asked 30), frame 9.8 ms (draw 7.1, push 1.9), loop cpu 29%, view home, mode awake, heap 1xx K (min 1xx K), psram 6xxx K
```

Targets (estimates from callgrind instruction counts on the PC, **not measured on a board**):

| Situation | fps asked | frame ms expected | loop CPU expected |
|---|---|---|---|
| Home, calm, round pupils | 24 | 5–9 | 15–25 % |
| Home, "Lollipop"-type spiral design, reacting | 30 | 8–13 | 25–40 % |
| Claude prompt (rim rings at 12 Hz) | 30 | 10–15 | 30–45 % |
| Keyboard open | 30 | 6–10 | 20–30 % |
| Drowsy / asleep | 15 / 10 | 3–6 | < 10 % |
| Screen off (face down, night) | 4 | < 1 | < 2 % |

If frames cost more, the adaptive cap lowers the rate on its own (never below 12 fps) — the log
shows `asked 30` with a lower actual fps. Note the numbers below.

Current (USB meter, 5 V in; estimates for the whole board, backlight dominates):

| State | Expected |
|---|---|
| Awake, backlight 100 %, Wi-Fi idle (modem sleep) | 180–230 mA |
| Awake, backlight 35 % (night) | 110–150 mA |
| Asleep (eyes closed, backlight glow 6–18 %, 10 fps) | 70–100 mA |
| Screen off (Mode Off, PWM 0, panel sleep-in, 6 MHz pclk, 4 fps) | 45–70 mA |
| Deep sleep (night, docked or off ≥ 10 min, 23:00–06:00) | < 1 mA board logic; the ETA6098 and the LDO add their own quiescent current |
| Wi-Fi TLS turn (peak, < 3 s) | +80–120 mA |

- [ ] **Deep sleep wake**: at night with `Screen off at night` on, face down 10 min → the log says
      `[power] deep sleep for N s`. Press **BOOT** → it wakes. A touch wakes it only if the GT911 INT
      line idles high (the firmware checks before arming it) — note whether touch-wake works.

## 5 · Wi-Fi and the AI (4 min)

1. Settings → Wi-Fi → **Set up from a phone**. SOUL scans the networks first, then opens the access
   point `SOUL-XXXX` with a random 8-digit WPA2 password and shows a **QR code**.
2. Point the phone camera at the QR → "Join SOUL-XXXX" (iOS 11+, Android 10+). The setup page opens
   (captive portal); if it closed, open `http://192.168.4.1`.
3. Pick your Wi-Fi, type its password, pick who helps SOUL think:
   - **SOUL Cloud (recommended)**: fill in "SOUL Cloud address" (`https://…`); keys live on the
     cloud's account page, never here.
   - **Your Anthropic key / Your OpenAI key (advanced)**: paste the key under *Advanced*. It is stored
     in NVS (`soulkey`), sent only to that provider, never printed, never shown back (only `sk-ant-…a1B2`).
   - **No AI**: alarms, timers, reminders and notes still work, in Romanian and English, offline.
4. Save → "Wi-Fi connected" toast on SOUL; the clock sets itself from NTP (time zone from the page,
   default `EET-2EEST,M3.5.0/3,M10.5.0/4`).

Checks:
- [ ] Hold the glass (or type with `a<text>` on serial): "wake me at 7 on weekdays" → thinking eyes →
      the answer, an alarm chip, and the alarm appears in Alarms. Log: `[ai] claude direct -> 200 none in N ms`
      (write N down: time to answer over home Wi-Fi).
- [ ] Wrong key → amber line "key rejected…", confused eyes, the on-device rules still set alarms/timers.
- [ ] Unplug the router → "You're offline" answer; `set a timer for 5 minutes` still starts a timer.
- [ ] **TLS**: the first request completes (certificate bundle; never `setInsecure`).
- [ ] Nothing secret on serial: search the log for `sk-`, `sdt_`, `Bearer` → no hits.

**SOUL Cloud** (when a server is running, docs/07):
- [ ] Log: `[cloud] device token ok, not paired yet` → `[cloud] socket open, hello sent` → `[cloud] welcome`.
- [ ] Settings → AI → SOUL Cloud → the **pairing code** (6 digits, big) + a QR of the pair link. Scan it,
      sign in, confirm → SOUL says "Hi, <name>!" with heart eyes and returns.
- [ ] In Claude (web or phone app) with the SOUL connector: "remind me tomorrow at 18:00 to call the bank
      on my SOUL" → within ~1 s SOUL shows surprised → happy eyes and the toast; the reminder rings at 18:00.
- [ ] Claude app → Ask my Claude: type a question → "Left for your Claude" → in Claude: "check my SOUL".
- [ ] Pull the Ethernet of the router for 2 min, plug it back → `[cloud] socket open` again within 60 s.

**Claude Desktop Hardware Buddy** (BLE): Claude Desktop → Help → Troubleshooting → Enable Developer
Mode → Developer → Open Hardware Buddy… → Connect → type the 6-digit code SOUL shows. Ask Claude Code to
run a command → SOUL's eyes go wide with an amber rim → hold the glass = approve.
- [ ] One approval → exactly one decision on the desktop (the duplicate-prompt bug is fixed and tested).

## 6 · Write down

| Measured on (date, unit MAC) | |
|---|---|
| fps / frame ms home | |
| fps / frame ms Claude prompt | |
| min free internal heap after a cloud turn + BLE | |
| mA awake 100 % / night / asleep / off | |
| AI answer time (direct key) | |
| NVS write: flicker only, or lasting shift? | |
| Touch wakes from deep sleep? | |
| Orientation / mirror flags needed | |
| IMU_MAP needed? tap threshold that works | |

## What is verified where

| | Verified on the PC | Needs the board |
|---|---|---|
| Eyes: designs, 31 expressions, spring rig, birth roll | native tests vs a node fixture from `eyes.js`; pixel parity vs the web engine (mean ≤ 0.96/255) | colours on the IPS panel |
| SoulOS flows, gestures, alarms, notes, keyboard, pairing, pushes | 112 native tests, simulator stills (`sim/shots/`) | finger feel, touch calibration |
| Eyes' motion (level keeping, marble pupils, dizzy, orientation, double tap, nods) | filter / detector unit tests, a parity trace vs `eyes.js` Motion (`tools/gen_motion_fixture.js`), the simulator (`program out motion`, `program out keys`) | the IMU axes (§3b), tap threshold on the real case |
| AI protocol (Claude / OpenAI / relay), offline rules | recorded API bodies, strict action validation | real TLS, real latency |
| SOUL Cloud protocol v1 | frames in/out, push mapping, dedupe, close codes, backoff, auth | the WebSocket against a real server; TLS memory with BLE on |
| QR codes (pairing, Wi-Fi join) | decoded from simulator frames with zxing | phone cameras at arm's length |
| Rendering cost | callgrind instruction counts, PC timings | real fps / CPU on the S3 |
| Display driver, touch, IMU, RTC, buzzer, deep sleep | compiles warning-free | everything in this checklist |
