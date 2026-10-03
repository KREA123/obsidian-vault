# SOUL M bring-up: the first 15 minutes on a real 2.8C

*Waveshare ESP32-S3-Touch-LCD-2.8C, firmware 1.1.0 (§4b: 1.4.x, §4c: 1.5.0). Nothing below has run on a board yet: every line
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

## 4b · SoulOS 5 Glass (firmware 1.4.x, 3 min)

What should happen (pictures: `sim/shots/glass/soulos-glass-sheet-device.png`; design: `../os/DESIGN-GLASS.md`):

- [ ] **Standby = the eyes alone.** After boot, and whenever nobody touches it, the glass is pure black with the
      two eyes on it: no clock, no rings, no hint words. Check the black is really black on this IPS panel (no
      grey wash outside the eyes; if there is, note the backlight level).
- [ ] **A touch peeks.** Tap the face: a glass capsule with the time and battery sits on the top rim, a hint on
      the bottom, all **on black** (behind the eyes it is always black, 1.4.1); 4 s later they fade out.
- [ ] **Never an aura behind the eyes.** Notifications, Claude's ask, listening / thinking / the answer, ringing:
      glass capsules and sheets on pure black. The aura only appears on OS screens, ~0.2 s after the eyes step back.
- [ ] **Screens are glass.** Swipe to the launcher, open Alarms, Settings, the keyboard: words on frosted panels
      over the aura, a lighter rim at the top-left of each panel. Look for **banding** in the dark aura (it is
      dithered; if you see steps, note where) and for panels that look grey-flat instead of frosted.
- [ ] **Idle goes back.** Leave Settings open: after 15 s it returns to the eyes alone (not while typing, on the
      dial, while ringing, with a running timer on screen or a pairing code shown).
- [ ] **Tone.** On an OS screen the aura's top glow follows the state (built in the background in ~11 frames,
      then swapped in); a Claude request in standby: an amber capsule on black for 5 s, the eyes stay wide.
- [ ] **Drift / tilt.** On a screen, tilt it slowly: the aura leans a few px (repaints at most 4×/s); the frame
      rate must not drop under the cap (`F` overlay).
- [ ] The log prints `psram` ~2 MB lower than with 1.3.0 (the four Glass buffers). If `GlassLayer::begin` could not
      get the memory, the screens fall back to black (the old look) and nothing else changes.

Frame cost, callgrind instructions per composed frame on the PC (`--toggle-collect='suflet::FrameComposer::compose*'`,
the sim's `bench_*` scenarios; the same counts were taken for 1.3.0 from the same scenarios):

| Scenario | 1.3.0 | 1.4.0 | |
|---|---|---|---|
| Standby, nobody touches it (`bench_standby`) | 5.07 M | 5.06 M | same: standby draws no UI, the aura is off |
| A screen open, idle (`bench_screen`, Settings) | 1.74 M | 2.45 M | +41 %: the drift/tilt repaint (≤ 4/s, full glass) |
| Typing (`bench_typing`) | 3.53 M | 6.33 M | +79 %: 35 glass keycaps instead of flat caps |
| Opening/closing screens every second (`bench_nav`) | 3.60 M | 5.56 M | +55 %: full repaints + the 0.3 s aura fades |
| `home` (boop, laugh, look) | 2.72 M | 3.09 M | +14 %: the peek after the touch |
| `launcher` (swipe, open Alarms, set one) | 3.61 M | 5.59 M | +55 % |
| `talk` (keyboard, thinking, answer) | 4.09 M | 6.23 M | +52 % |
| `claude` (working, asks, approve) | 4.61 M | 6.99 M | +52 % |

A new tone (aura) costs ~50 M instructions in all, spread over 11 frames (3 low-res phases of ≤ 7 M, then 8
slices of 64 rows of ~4.2 M); the old tone stays on screen until the swap. Scaling 1.3.0's estimates
(§4) by these ratios: keyboard frames ~11–18 ms, screens ~8–14 ms at 30 fps, standby unchanged; the adaptive
cap lowers the rate if a frame costs more. **Measure** on the board with `F` and note real numbers here.


## 4c · On the go: several networks, the phone's hotspot, hotel Wi-Fi (firmware 1.5.0, 10 min)

What should happen (pictures: `sim/shots/everywhere/`; design and numbers: `../docs/09-EVERYWHERE.md`). Keep the
serial monitor open: every step logs a `[net]` line.

- [ ] **Upgrade keeps the old network.** Flash 1.5.0 over 1.4.x: SOUL joins the same Wi-Fi without asking;
      *Settings › Wi-Fi* shows "Connected" and the setup page lists it as *Home*. Log: `[net] joining "…" (Home, priority 8)`
      then `[net] internet check on "…": 204 (0 B) -> online`.
- [ ] **Add the phone's hotspot on SOUL.** *Settings › Wi-Fi › Add my phone's hotspot › Type it on SOUL*: the name, then
      the password. The first letter must **not** turn into a capital. iPhone: Personal Hotspot › Allow Others to Join,
      **Maximize Compatibility on** (SOUL is 2.4 GHz only). Type the name with a plain ' (the iPhone uses ’): it must still join.
- [ ] **Walk out.** Switch the home router off (or walk out of range). Expected: `link lost`, then scans every ~4 s;
      with the hotspot on, SOUL joins it in **< 10 s** (write the time below); toast "On your phone's hotspot".
      Note how long it takes when the iPhone's hotspot screen is **closed** (iPhone stops showing the hotspot to new
      devices after a while; opening Settings › Personal Hotspot shows it again).
- [ ] **Come home.** Router back on: within ~2 min SOUL leaves the hotspot for home (`[net] joining "home"`).
- [ ] **Phone without data.** Turn mobile data off on the phone while SOUL is on its hotspot: "The phone has no data"
      in *Settings › Wi-Fi* within ~30 s; SOUL Cloud closes, the rules still answer.
- [ ] **Hotel / captive Wi-Fi.** Join a guest network with a login page (or a router with a captive-portal test page)
      from the setup page: the check logs `302` or `200 (… B) -> captive`; toast "Wi-Fi needs a login: use the hotspot";
      if the hotspot is saved and on, SOUL moves to it within ~30 s.
- [ ] **Wrong password.** Save a network with a wrong password: "Wrong password" + its name on the Wi-Fi page; SOUL
      does not retry it until the network is saved again (or 30 min pass).
- [ ] **Questions kept offline.** With no network, hold the glass / type "what is the capital of Peru?": "No internet
      right now. I'll ask as soon as I'm back online (1 waiting)". "Wake me at 7" still sets the alarm at once.
      Turn the hotspot on: ~3 s after "Online again" the answer comes by itself ("You asked earlier").
- [ ] **Offline eyes.** 20 s without internet on the home face: slightly heavier lids and a glance left-right about
      every 9 s; back online they open again. Not in *No AI* mode.
- [ ] **Battery.** With the hotspot gone for 10 min, the scans slow down to once a minute (the log shows the gap). Note
      the current with the USB meter while it searches fast (expected +40–80 mA average for the first 3 min).

| 1.5.0 measurement | Value |
|---|---|
| Hotspot appears → SOUL online (s) | |
| … with the iPhone hotspot screen closed (s) | |
| Home back → SOUL leaves the hotspot (s) | |
| Current while searching fast / slow (mA) | |

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
- [ ] Serial `K` prints `SOULKEY PUB <87 chars>` once Wi-Fi is up (the device key was made; never the private key).
- [ ] Log: `[cloud] device key made (P-256)` (first time) → `[cloud] signed in (not paired yet)`; no
      `[cloud] auth: HTTP 401 bad_signature` (that would mean the host SOUL signs for ≠ the cloud's SOUL_PUBLIC_HOST).
- [ ] Settings → AI → SOUL Cloud → the **pairing code** (`XXXX-XXXX`, big) + a QR of `https://{BASE}/pair#c=…`.
      Scan it, sign in with the email code, type/confirm the code → SOUL asks "Pair with <name>?" → tap
      *Yes, pair* → SOUL says "Hi, <name>!" with heart eyes; the phone shows the brain choices.
- [ ] In Claude (web or phone app) with the SOUL connector: "remind me tomorrow at 18:00 to call the bank
      on my SOUL" → within ~1 s SOUL shows surprised → happy eyes and the toast; the reminder rings at 18:00.
- [ ] Claude app → Ask my Claude: type a question → "Left for your Claude" → in Claude: "check my SOUL".
- [ ] Pull the Ethernet of the router for 2 min, plug it back → `[cloud] socket open` again within 60 s.
- [ ] Long-poll (only if a network blocks WebSockets, e.g. a guest/corporate proxy): `[cloud] the socket will not
      open: long-poll` → pairing, pushes and turns still work (a little slower); every 10 min
      `[cloud] long-poll: trying the socket again`.
- [ ] Wake-polls (night, paired, `nightOff` on): after 10 min dark at night `[power] deep sleep for 900 s (then a
      SOUL Cloud wake-poll)`; 15 min later the screen stays **off**, `[power] wake-poll: screen off, one poll, back
      to sleep`, and within ~12 s it sleeps again. Send a connector reminder while it sleeps → it is on SOUL after the
      next wake (≤ 15 min). Write down the awake time and the current of one wake-poll (§6).

**Factory key** (the provisioning station, `../ai/tools/factory_enrol.py`; also fine on a dev unit):
- [ ] Serial `SOULKEY GEN` (type it, Enter) → `SOULKEY PUB soul-<12 hex> <87 chars> new` the first time, the same
      line without `new` afterwards; it works before Wi-Fi is set up (bootloader entropy source). `SOULKEY PUB` alone
      prints it again. Never anything that looks like a private key.
- [ ] `python tools/factory_enrol.py --port /dev/ttyACM0 --csv /tmp/keys.csv` (from `ai/`, `pip install pyserial`)
      → `ENROLLED  SOUL  XXXX-XXXX  (soul-…)`; again → `ALREADY LISTED`.

**My Claude on my computer** (SOUL Bridge, `../docs/08-OWN-CLAUDE.md`; needs Claude Code signed in on a computer):
- [ ] On the computer: `npm install -g soul-bridge` (or the `.tgz`), `soul-bridge doctor`.
- [ ] On SOUL: Settings → AI → *My Claude on my computer*. Paired with an account: SOUL shows
      `soul-bridge pair XXXX-XXXX --cloud <host>`; not paired: a 6-digit code and `--soul <IP>`, and the log
      `[bridge] listening: ws://soul-xxxx.local:8765/bridge`. Type the command on the computer → "Paired with …".
- [ ] `soul-bridge discover` on the same Wi-Fi lists `soul-xxxx.local` (mDNS works on this router).
- [ ] `soul-bridge setup`, double-click **Start SOUL**, accept Claude Code's three dialogs → the status page
      (http://127.0.0.1:8766) turns green; SOUL's AI screen says "connected · <computer>".
- [ ] Ask on SOUL "wake me at 7" → eyes wait, then think → the answer "Claude · your computer" and the alarm.
      Write down the time to answer.
- [ ] Close the Start SOUL window → SOUL: "Your computer is offline: open Start SOUL", and "set a timer for 5
      minutes" still starts a timer (offline rules). *Forget* on SOUL → the computer must pair again.
- [ ] Free internal heap with the bridge server on + TLS + BLE (`p` perf line): write it down.

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
| SOUL Bridge answer time (LAN / through the cloud) | |
| wake-poll: seconds awake, mA | |
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
| SOUL Cloud protocol v1 | frames in/out, push mapping, dedupe, close codes, backoff, auth; long-poll and wake-polls against a scripted cloud; the simulator over long-poll against a real cloud | the WebSocket against a real server; TLS memory with BLE on; a wake-poll's time and current |
| SOUL Bridge (docs/08) | the LAN server, the cloud frames, the Os screen and eyes (native); simulator → cloud → `soul-bridge` → mocked Claude Code, and on the LAN | `esp_http_server` + mDNS on a real router; a signed-in Claude Code |
| QR codes (pairing, Wi-Fi join) | decoded from simulator frames with zxing | phone cameras at arm's length |
| Rendering cost | callgrind instruction counts, PC timings | real fps / CPU on the S3 |
| Display driver, touch, IMU, RTC, buzzer, deep sleep | compiles warning-free | everything in this checklist |
