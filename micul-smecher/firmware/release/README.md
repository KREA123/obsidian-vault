# SOUL M install image

`SOUL-2.8C-install.bin` — SoulOS firmware 1.8.0 for the **Waveshare ESP32-S3-Touch-LCD-2.8C**
(ESP32-S3R8, 16 MB flash, 8 MB PSRAM). One merged image: bootloader at 0x0, partition table
(`partitions.csv`: Arduino's `default_16MB` with the unused `spiffs` split into `soulmem` (128 KB, SOUL Memory) and `model` (3.2 MB, the optional speech models), + a 64 KB `soulid` NVS partition for the device key) at 0x8000, `boot_app0` at 0xe000, the app at 0x10000. Flash it at **0x0**.

- built 2026-10-04 from `pio run -e lcd28` (Arduino-ESP32 3.3 / ESP-IDF 5.5, pioarduino), zero compiler warnings,
  `pio check -e lcd28` clean; app 2,394,603 B of 6.25 MB (4.2 MB headroom), static RAM 113,172 B of 320 KB
- size 2,465,024 B · sha256 `1248f38eeaef5e2e936dc7dc557672350842acba33bf0a6ccec9af9cde8b8120`
- 1.8.0: **performance** ([`../PERF.md`](../PERF.md)), the same look (31,455 simulator frames hashed: identical
  to 1.7 but for 68 frames / 266 pixels where 1.7's partial repaint had differed from a full redraw, now fixed).
  Estimated on the S3 from instruction counts: standby −30 % CPU per frame (the worst of the 120 designs −29 %),
  typing −49 % and 55 % fewer pixels pushed (only the key that changed is repainted), maps −48 % and games −41 %
  (both now at 30 fps instead of ~21), every screen −14 … −27 %; a question with 200 facts in SOUL Memory 54 → 16 ms.
  The eyes are on the glass ~1 s sooner after power-on (the panel's init beside the app's, the aura built over the
  first frames, touch / BLE / Wi-Fi after the first frame). Screen off: 80 MHz and the gyro asleep (est. −10 mA);
  BLE adverts every 152–211 ms. Serial `m`: tasks' stack head-room and CPU, heaps; the `[perf]` line adds the
  present's copy / wait times. The app is 68 KB smaller (`-fno-exceptions`). Same partition table as 1.6 / 1.7 (no
  reflash at 0x0 needed over 1.6+). Not yet run on the board: measure with [`../BRINGUP.md`](../BRINGUP.md) §5.
- 1.7.0: **SoulOS apps** (`../../os/APPS.md`), all in the glass design, the eyes always on black. **Maps**
  (`../../docs/11-MAPS.md`): SOUL has no GPS, so the owner's phone tells it where it is (`/me/where` › *Share my
  location*, or a pasted Google / Apple / OSM link), or, opt-in, a Wi-Fi scan located by the cloud (beaconDB by
  default; Google's Geolocation API for production); SOUL Cloud cuts the map into a small vector bundle (≤ 24 KB, from
  a self-hosted Protomaps file; never `tile.openstreetmap.org`) that SOUL draws dark on glass; drag = pan, along the
  rim = zoom; *Where to?* / "take me to…" (AI action `navigate`, Claude connector `navigate_on_soul`) → route preview
  (km, min, arrival), then a step card whose arrow is relative to the route (no compass: tap the card at each turn),
  *Send to phone* (QR of a Google Maps link); the last map stays on SOUL until a restart (the last place survives one). Also: **Control** (rim dials for brightness
  and volume, Quiet, Large text, Find phone, Sleep), the **Today** stack, **Weather** (Open-Meteo via the cloud),
  **Calendar** (an ICS link), **Music** = focus sounds made on SOUL (rain, brown noise, ocean, fire), **Games** (tilt
  ball on the gyro, rhythm, eye memory), **Focus** (Pomodoro), **Breathe** (the eyes breathe), **Habits**,
  **Stopwatch**, **World clock**, **Convert** (units offline, ECB currency rates), **Find my phone**, **Device**,
  **Quick replies**, Settings › **Apps** (order and hide the orbit). Same partition table as 1.6.0 (no reflash at 0x0
  needed over 1.6; from ≤ 1.5 flash this image at 0x0). Checks: [`../BRINGUP.md`](../BRINGUP.md) §4e.
- 1.6.0: **SOUL Memory** (`../../docs/10-SOUL-MEMORY.md`): what SOUL knows about its owner lives **on SOUL** (the new
  `soulmem` partition, two CRC-checked copies, batched writes that wait for a quiet moment and resync the panel) and
  goes with every question to whichever AI is connected (Claude / ChatGPT with your key, SOUL Cloud, your Claude Code
  through SOUL Bridge): "the AI changes, the soul stays". Up to 512 typed facts; never passwords, PINs or card
  numbers. The AI may propose `memory.remember` / `memory.forget`; you can say "remember that…" / "ține minte că…" /
  "forget…"; offline, SOUL keeps birthdays, names and who is who by itself and answers "când e ziua Anei?".
  *Remembered: … · tap to undo* on the rim. *Settings › Memory* (page 3): the facts on glass, search, hold to forget,
  forget all, and the optional **encrypted backup** to your SOUL Cloud account (off by default; `/me` shows, exports and
  deletes it). **Offline replies**: 222 hand-written lines (hello, thanks, jokes, "I'm sad"…) when there is no AI or
  no internet. **Offline voice commands** are a separate build (`pio run -e lcd28_voice`, INMP441, ESP-SR MultiNet7,
  39 English commands, push-to-talk; flash `srmodels.bin` at `0xcb0000` once): not in this image. Also in 1.6.0: the
  **SoulOS apps** of the same day (Control, Today stack, Maps, Weather, Calendar, Music, Games, Focus, Breathe,
  Habits, Stopwatch, World clock, Convert, Find phone, Device). 1.6.0 changes the partition table (flash this image at
  0x0): NVS, the apps and the device key do not move, settings survive. Not yet run on the board:
  [`../BRINGUP.md`](../BRINGUP.md) §4d.
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
`spiffs`; 1.3.0 changes no partition, its paired computers live in NVS `soulbridge`; 1.5.0 keeps the saved networks in NVS `soulkey` `wifis`; 1.6.0 takes the unused `spiffs` for `soulmem` + `model`); *Settings › Start over* re-runs
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

Offline voice commands (1.6, optional): `pio run -e lcd28_voice -t upload`, then the speech models once:

```bash
esptool --chip esp32s3 write-flash 0xcb0000 ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/esp_sr/srmodels.bin
```
