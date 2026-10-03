# SOUL M install image

`SOUL-2.8C-install.bin` — SoulOS firmware 1.5.0 for the **Waveshare ESP32-S3-Touch-LCD-2.8C**
(ESP32-S3R8, 16 MB flash, 8 MB PSRAM). One merged image: bootloader at 0x0, partition table
(`partitions.csv`: Arduino's `default_16MB` + a 64 KB `soulid` NVS partition for the device key) at 0x8000, `boot_app0` at 0xe000, the app at 0x10000. Flash it at **0x0**.

- built 2026-10-03 from `pio run -e lcd28` (Arduino-ESP32 3.3 / ESP-IDF 5.5, pioarduino), zero compiler warnings,
  `pio check -e lcd28` clean
- size 2,275,392 B · sha256 `ca7317b9b47aff3291efb01281aa4386103aed6d4c58b8c700be25dc8a7ed4a4`
- 1.5.0: **SOUL on the go** (`../../docs/09-EVERYWHERE.md`). SOUL keeps up to **8 Wi-Fi networks** (home, work, the
  phone's hotspot, other) with a priority and roams by itself: it joins the best one in reach, moves back home from the
  hotspot (a look-around every 2 min on a second-choice or weak network), and when the link drops it searches fast
  (every 4 s for 3 min, then every 20 s, then once a minute); picking SOUL up or asking something offline searches fast
  again. At boot it tries the network that last worked before any scan (wake-polls). **Add my phone's hotspot**: in
  *Settings › Wi-Fi* (iPhone: Personal Hotspot › Allow Others to Join + Maximize Compatibility; Android: hotspot name,
  password, 2.4 GHz), typed on the round keyboard (names and passwords are typed verbatim: no auto-capital,
  diacritics or ". "; an iPhone's ’ matches a typed '), or on the setup page (`/hotspot`), which now lists the saved
  networks with first / normal / last and *forget*. After every join SOUL checks the internet
  (`http://connectivitycheck.gstatic.com/generate_204`): a **hotel / train login page** (captive portal) or a hotspot
  **without mobile data** is told apart from "online", said on the screen ("Wi-Fi needs a login: use the hotspot"),
  and SOUL Cloud waits for real internet. **Offline**: after 20 s without internet the eyes get slightly heavier lids
  and glance around now and then; the on-device rules still answer at once, and other questions are **kept (5 at
  most, 6 h at most)** and sent one at a time once SOUL is back online ("You asked earlier"); a turn lost on the way
  goes back in the queue (twice at most). The questions are kept in RAM: a restart or deep sleep loses them. 1.4's
  single network moves into the new list as *Home* on first boot. 153 native tests (12 new), the simulator scene
  `everywhere` (`../sim/shots/everywhere/`). Not yet run on the board: [`../BRINGUP.md`](../BRINGUP.md) §4c.
- 1.4.1: behind the eyes it is **always pure black**, like the renders. The aura rises only on OS screens
  (launcher, Today, Alarms, dial, timer, notes, settings, keyboard…), 0.2 s after the eyes step back; never on a
  face moment (standby, the touch peek, a notification or Claude's ask over the eyes, listening / thinking /
  answering, ringing, the first-boot hello, asleep), where the glass capsules sit on black.
- 1.4.0: **SoulOS 5 · Glass** (`../../os/DESIGN-GLASS.md`). Standby is the eyes alone on true black: no clock,
  no rim rings, no hints (a pending Claude request shows as a 5 s amber capsule, then only in the eyes). A touch on
  the face peeks for 4 s (time · battery in a glass capsule on the rim); any screen left alone for 15 s goes back
  to the eyes. Screens sit on a slow aura (ember, night blue, lilac + a state glow: ice listening, amber needs you,
  mint done) and their words on frosted glass: rim capsules, glass pills instead of underlines, row slabs,
  sheets, glass keycaps, a glass dial, notification capsules. Built from two PSRAM buffers (aura + frosted,
  ~1 MB, + ~1 MB to build a new tone in the background), rendered at 1/4 resolution, blurred, dithered; the
  drift and the IMU tilt only move the read window. Pictures: `../sim/shots/glass/soulos-glass-sheet-device.png`.
  Frame cost and what to check on the board: [`../BRINGUP.md`](../BRINGUP.md) §4b. Not yet seen on the board.
- 1.3.0: **My Claude on my computer** (SOUL Bridge, `../../docs/08-OWN-CLAUDE.md` §4) in *Settings › AI*: the owner's
  own Claude Code on a computer answers what is asked on SOUL — through SOUL Cloud (`soul-bridge pair XXXX-XXXX
  --cloud …`, any network) or on the home Wi-Fi (SOUL serves `ws://soul-xxxx.local:8765/bridge`, mDNS, a 6-digit
  code); the eyes wait, then think; computer off → the offline rules and "Your computer is offline: open Start
  SOUL". SOUL Cloud over **long-poll** when the socket will not open (3 refusals; the socket is tried again every
  10 min). **Wake-polls**: a paired SOUL in deep sleep wakes every ≤ 15 min, screen off, polls once, acks, sleeps
  again. **Factory**: serial `SOULKEY GEN` / `SOULKEY PUB` (`../../ai/tools/factory_enrol.py`). None of this has run
  on the board yet: the code is unit-tested on the PC (131 native tests) and runs end to end in the simulator
  against a local cloud and the real `soul-bridge` with a mocked Claude Code.
- 1.2.0: SOUL Cloud protocol rev. 2, exactly what `ai/` implements (docs/07 §6): an ECDSA P-256 device key made
  on the device (kept in the new `soulid` partition, never erased by *Start over*; serial `K` prints the public
  key), challenge/signature sign-in with a RAM-only token, 8-character pairing codes shown `XXXX-XXXX` + QR,
  "Pair with Ana?" answered only by a touch, pushes with origin badges, night alarms that wait for *Accept*,
  private cards, *Settings › AI › Connect Claude* (the pairing code, then a QR to this SOUL's phone page where the
  owner pastes the key of their Claude account), *Settings › Claude & ChatGPT on me* (pause connectors), the offline queue with `added` /
  `too_big` / `invalid` handling, the cloud's time zone. The same protocol code is unit-tested on the PC against
  frames recorded from the running cloud and runs end to end in the simulator against a local cloud
  (`ai/tools/e2e_sim.py`). Not yet tried on the board against a deployed cloud.
- 1.1.0: the eyes feel the IMU (gyro + accel): level keeping, marble pupils, spin → dizzy → ufff,
  on its back / face down / upside down / calm in a hand, double tap on the case, nod yes / shake no
  (answers a Claude request). Check the IMU axes first: [`../BRINGUP.md`](../BRINGUP.md) §3b
- byte-identical to PlatformIO's own `firmware.factory.bin` for the same build
- no key, token or cloud address is compiled in: SOUL Cloud is off until you set its address

## Flash from the browser (no tools)

1. Chrome or Edge on a computer → <https://espressif.github.io/esptool-js/>
2. Plug the board in with a USB-C **data** cable → **Connect** → pick the USB JTAG/serial port
   (if none appears: hold **BOOT**, tap **RESET**, release BOOT, try again)
3. **Flash Address** `0x0`, **File** `SOUL-2.8C-install.bin` → **Program** (about 1 minute)
4. Press **RESET**. The chip id types out on the rim and the eyes open.

## Flash from a terminal

```bash
esptool --chip esp32s3 write-flash 0x0 SOUL-2.8C-install.bin
```

## After flashing

Wi-Fi, the AI (SOUL Cloud with your account / your own Anthropic or OpenAI key / No AI) and the first checks:
[`../BRINGUP.md`](../BRINGUP.md). The settings, alarms, notes and keys live in NVS and survive
re-flashing this image (`nvs` did not move; 1.2.0 only added `soulid` at the end of flash, taken from the unused
`spiffs`; 1.3.0 changes no partition, its paired computers live in NVS `soulbridge`; 1.5.0 keeps the saved networks in NVS `soulkey` `wifis`); *Settings › Start over* re-runs
the first boot and keeps the device key.

## Rebuild this image

```bash
pio run -e lcd28
cp .pio/build/lcd28/firmware.factory.bin release/SOUL-2.8C-install.bin   # the same bytes as the merge below
esptool --chip esp32s3 merge-bin -o release/SOUL-2.8C-install.bin --flash-mode dio --flash-freq 80m --flash-size 16MB \
  0x0 .pio/build/lcd28/bootloader.bin 0x8000 .pio/build/lcd28/partitions.bin \
  0xe000 ~/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin \
  0x10000 .pio/build/lcd28/firmware.bin
```
