# SOUL M install image

`SOUL-2.8C-install.bin` — SoulOS firmware 1.2.0 for the **Waveshare ESP32-S3-Touch-LCD-2.8C**
(ESP32-S3R8, 16 MB flash, 8 MB PSRAM). One merged image: bootloader at 0x0, partition table
(`partitions.csv`: Arduino's `default_16MB` + a 64 KB `soulid` NVS partition for the device key) at 0x8000, `boot_app0` at 0xe000, the app at 0x10000. Flash it at **0x0**.

- built 2026-10-03 from `pio run -e lcd28` (Arduino-ESP32 3.3 / ESP-IDF 5.5, pioarduino), zero compiler warnings
- size 2,137,904 B · sha256 `bda9aa6775a2c54e5dfebd1c4a6ac228dbbab90ac5739e74f8db64b9a78c1d29`
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
re-flashing this image (`nvs` did not move; 1.2.0 only adds `soulid` at the end of flash, taken from the unused
`spiffs`); *Settings › Start over* re-runs the first boot and keeps the device key.

## Rebuild this image

```bash
pio run -e lcd28
esptool --chip esp32s3 merge-bin -o release/SOUL-2.8C-install.bin --flash-mode dio --flash-freq 80m --flash-size 16MB \
  0x0 .pio/build/lcd28/bootloader.bin 0x8000 .pio/build/lcd28/partitions.bin \
  0xe000 ~/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin \
  0x10000 .pio/build/lcd28/firmware.bin
```
