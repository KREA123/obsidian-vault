# 03 · Software

*SOUL package · 25 Sep 2026. Four components: firmware on the device, the AI service in the cloud, the SoulOS web prototype and the landing page. Architecture: [`../os/ARCHITECTURE.md`](../os/ARCHITECTURE.md) (layers, decisions D1–D11, BLE protocol, roadmap 0.1 → 1.0). UX spec: [`../os/SPEC.md`](../os/SPEC.md).*

## Verified on 25 Sep 2026 (in this environment)

| Command | Result |
|---|---|
| `cd firmware && pio test -e native` | **55 test cases: 55 succeeded** (0.57 s) |
| `cd firmware && pio run -e amoled175` | **SUCCESS**, firmware.bin 934,608 B (amoled143: 939,472 B, built 25 Sep) |
| `cd firmware && pio run -e sim` | **SUCCESS**, `.pio/build/sim/program` |
| `cd ai && python -m pytest -q` | **49 passed** (3.4 s), no API key needed (Claude and OpenAI clients mocked) |
| `python -c "import suflet_ai.server, suflet_ai.mcp_server"` | imports OK (FastAPI app) |

**Not verified yet:** anything on real hardware. The board has not been in hand yet. Screen orientation, touch and IMU axes, brightness, and BLE pairing with Claude Desktop get confirmed at the first flash.

---

## 1. Firmware: `firmware/` (the "Suflet" engine + SoulOS v1 modules)

**Stack:**
- Arduino-ESP32 via **pioarduino** (PlatformIO), C++17.
- Libraries: GFX Library for Arduino 1.6.8, ArduinoJson 7, SensorLib 0.4.1.
- `lib/Suflet/src/` has no hardware code. It builds identically for the board, the PC simulator and the tests.

| PlatformIO env | Target | Notes |
|---|---|---|
| `amoled175` | **Waveshare ESP32-S3-Touch-AMOLED-1.75**: the SOUL board (2 mics, speaker, AXP2101 PMU, PWR key) | Use this one |
| `amoled143` | Waveshare ESP32-S3-Touch-AMOLED-1.43 (no audio, no PMU) | Default env, legacy desk edition |
| `sim` | PC simulator that writes raw frames | Marketing clips come from the real code |
| `native` | Unity unit tests on the PC | 55 tests |

**Install (Windows/macOS/Linux):**
1. Install VS Code + the PlatformIO extension, or run `pip install platformio`.
2. Open `firmware/`.

The first build downloads the ESP32 toolchain (~1 GB).

```bash
cd firmware
pio run -e amoled175 -t upload        # build + flash over the board's USB-C (native USB, no UART bridge)
pio device monitor -b 115200          # serial console; type ? for help
pio test -e native                    # 55 unit tests on the PC
pio run -e sim && .pio/build/sim/program /tmp/out all          # simulator: all scenes -> raw frames
python3 tools/frames_to_media.py /tmp/out ../media --mp4 --gif --sheet   # frames -> mp4/gif/contact sheet
python3 tools/gen_font.py && python3 tools/gen_words.py               # regenerate FontData.h / WordListData.h
```
- If the upload does not start: hold BOOT, tap RESET, release BOOT.
- Sim scenes: `idle boop purr dizzy sleep missed_you rare ai_talk claude_buddy keyboard timepicker night`.

**Serial commands (115200 baud):**

| Key | Action |
|---|---|
| `b` | boop |
| `l` | laugh |
| `s` | shy |
| `p` | purr (toggle) |
| `d` | dizzy |
| `f` | scared |
| `c` | confused |
| `y` | yawn |
| `n` | sneeze |
| `h` | hiccup |
| `v` | love (heart eyes) |
| `r` | birthday |
| `m` | missed you |
| `o` | lonely |
| `k` | startle |
| `z` | good night |
| `g` | face-down event |
| `w` | pick-up event |
| `D` | demo loop on/off (for filming) |
| `i` | raw accelerometer (face up ≈ 0,0,+1) |
| `t` | clock / mode / reaction |
| `T<epoch>` | set the clock |
| `P` | personality (tint, rarity, traits) |
| `U` | clear BLE bonds |
| `N` | note field (keyboard) |
| `A` | time picker → new alarm (saved to NVS `alarms`) |
| `L` | list alarms |
| `X` | delete all alarms |
| `?` | help |

**Calibrate on the first flash (5 min):**
- If the panel is an **SH8601** (image shifted 6 px or noisy), add `-DSUFLET_PANEL_SH8601`.
- If the image is rotated, add `-DSUFLET_ROTATION=90|180|270`.
- If touch is mirrored, set `TOUCH_MIRROR_X/Y` in `src/board.h`.
- If the IMU axes are wrong, fix `IMU_MAP` in `src/board.h` and check with `i`.
- On the 1.75, firmware sets the charge current to 200 mA. Raise it to ~500 mA for a 1000 mAh cell only.

**Works with Claude (Hardware Buddy BLE protocol):**
1. In Claude Desktop, go to Help → Troubleshooting → **Enable Developer Mode**.
2. Go to Developer → **Open Hardware Buddy…** → Connect, and choose "Claude-Suflet-XXXX".
3. Enter the 6-digit code shown on the screen.
4. Hold 1.2 s = approve. Double tap = deny. A single tap never approves anything.

`src/ble_link.cpp` is adapted from `anthropics/claude-desktop-buddy` (MIT). See `LICENSE-THIRD-PARTY.md`. The BLE name still says "Suflet"; renaming it to SOUL is on the roadmap.

**Modules:**
- `Canvas`: SDF renderer with dirty rectangles and text.
- `Face`: parametric eyes.
- `Brain`: mood, 24 reactions, sleep.
- `Personality`: seed from the chip, rarities.
- `Gestures` / `TouchGestures`: tap, hold, stroke, text mode.
- `ClaudeLink`.
- `Keyboard` + `TextField` + `Predictor`: round QWERTY, EN+RO, auto-diacritics.
- `TimePicker`: the Rim-Dial.
- `Alarms`: next fire, snooze, NVS blob.
- `Shell`: a minimal router.
- `Font`: Nunito, 85 KB.

Flash use on amoled143 is about 921 KB of 16 MB.

**Gaps vs SoulOS 1.0** (`os/ARCHITECTURE.md` §6, about 10 % exists):
- audio/voice (I2S, Opus), Wi-Fi, OTA, secure boot and flash encryption;
- SoulOS Link BLE, the phone app, LittleFS storage, notifications.

---

## 2. AI service: `ai/` (Python package `suflet_ai`, v0.2)

What it does:
- Companion birth (name, story, voice).
- Conversation turns with structured output that drives the eyes.
- Memory you can read and erase, reminders, notes, the day's diary.
- One **action layer** shared by 3 AI modes.
- Encrypted **bring-your-own key**.
- An **MCP connector** for Claude, reused for a ChatGPT app.

**Setup:**
```bash
cd ai
python -m venv .venv && . .venv/bin/activate      # Python 3.11+
pip install -r requirements.txt                  # anthropic 1.x, openai, mcp 2.x, cryptography, pydantic 2, fastapi, uvicorn, pytest
python -m pytest -q                              # 49 tests, no keys needed
export ANTHROPIC_API_KEY=sk-ant-...              # only for real Claude calls
python -m suflet_ai birth --device demo --seed 0xC0FFEE --owner Andu
python -m suflet_ai chat  --device demo
python -m suflet_ai diary --device demo --events examples/events_day.jsonl
SUFLET_API_TOKEN=change-me uvicorn suflet_ai.server:app --port 8787      # HTTP API
```

**Environment variables:**

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | Server-side Claude key (companion endpoints) |
| `SUFLET_MODEL` | **`claude-opus-5`** | Claude model. Opus 5 costs $5/$25 per 1M tokens in/out; Sonnet 5 $2/$10; Haiku 4.5 $1/$5. **Founder decision after a latency and cost test.** |
| `SUFLET_TURN_EFFORT` / `SUFLET_BIRTH_EFFORT` / `SUFLET_DIARY_EFFORT` | `low` / `high` / `medium` | Effort per task |
| `SUFLET_FALLBACKS` | `1` | Server-side model fallback on refusal |
| `SUFLET_DATA_DIR` | `./data` | SQLite + master key location |
| `SUFLET_TZ` | `Europe/Bucharest` | Local time for reminders |
| `SUFLET_API_TOKEN` | – | Bearer token for every HTTP endpoint (**required**) |
| `SOUL_DB` | `$SUFLET_DATA_DIR/soul.sqlite` | State DB |
| `SOUL_MASTER_SECRET` | random `data/master.key` (0600) | Master secret for BYO-key encryption (≥ 32 bytes; from a KMS in production) |
| `SOUL_OPENAI_MODEL` | `gpt-5` | ChatGPT-mode model (set the one you tested) |
| `SOUL_DEVICE_ID` | – | MCP server: which device receives actions (prototype, single user) |

**Modes** (`GET/POST /v1/mode`):

| Mode | How it works | What the user needs |
|---|---|---|
| **`none`** (default) | A local RO/EN rule parser handles "remind me at 5…", "alarm 7:30", notes, timers, lists. If unsure, it asks back. | nothing (no account, no internet) |
| **`claude`** | Anthropic tool use over the same 8 actions | their own API key, **or** the SOUL MCP connector added in their Claude |
| **`chatgpt`** | OpenAI Responses API + strict function calling | their own OpenAI key, **or** the SOUL app in ChatGPT |

The 8 actions are `note.create`, `reminder.create`, `alarm.set`, `timer.start`, `focus.start`, `message.draft`, `list.add` and `answer.show`. If the AI fails (bad key, offline, refusal), SOUL answers with the local parser and never goes silent.

**Honest limit:** Claude Pro/Max and ChatGPT Plus subscriptions **cannot** be used directly by a third-party device. The legitimate routes are the connector/app (it starts from Claude or ChatGPT) or the user's own API key.

**BYO key encryption** (`keystore.py`):
- Fernet (AES + HMAC), with the key derived by HKDF-SHA256 from `SOUL_MASTER_SECRET` and **bound to the device id and the provider**.
- The key is never logged or returned, and is never stored in clear (tested on the SQLite file).
- `POST /v1/key/test` makes a free models-list call.
- In production, per ARCHITECTURE D5, the key lives on the **phone** (Keychain/Keystore), never on SOUL.

**HTTP endpoints** (all `Authorization: Bearer $SUFLET_API_TOKEN`):
- Companion: `POST /v1/devices/{id}/birth|turn|events|diary`, `GET /v1/devices/{id}/reminders/due`, `GET|DELETE /v1/devices/{id}/memory`.
- Actions: `POST /v1/ask`, `POST /v1/action`, `GET /v1/actions`, `GET|POST /v1/mode`.
- Keys: `POST /v1/key`, `POST /v1/key/test`, `GET|DELETE /v1/key`.
- State: `GET /v1/today`, `GET /v1/sync?since=`, `GET /v1/due`.

**MCP connector for Claude** (`mcp_server.py`, official `mcp` 2.x SDK):
- Tools: `add_note`, `add_reminder`, `set_alarm`, `show_on_soul`, and `list_today` (read-only).

```bash
SOUL_DEVICE_ID=demo python -m suflet_ai.mcp_server                      # stdio: Claude Desktop / Claude Code
SOUL_DEVICE_ID=demo python -m suflet_ai.mcp_server --http --port 8788   # Streamable HTTP at /mcp: claude.ai / ChatGPT
```
Claude Desktop `claude_desktop_config.json`:
```json
{"mcpServers": {"soul": {"command": "python", "args": ["-m", "suflet_ai.mcp_server"],
  "cwd": "/path/to/micul-smecher/ai", "env": {"SOUL_DEVICE_ID": "demo"}}}}
```
In claude.ai, add it under Settings → Connectors → "Add custom connector" → `https://<host>/mcp`. **Before going public, put the HTTP server behind OAuth** (MCP authorization spec), so accounts map to devices.

**ChatGPT app route:**
- ChatGPT Apps (Apps SDK) are built on MCP, so the **same `/mcp` server** is the SOUL app.
- `list_today` carries `readOnlyHint`, so writes need user confirmation in ChatGPT.
- Test it in ChatGPT developer mode. Public listing needs **OpenAI review** (policies, privacy, OAuth), planned for SoulOS 0.6.

**Safety rules baked into the prompts (do not remove):**
- SOUL says it is an AI (AI Act Art. 50, Anthropic policy).
- No romantic or sexual roles, no guilt-tripping, no purchase pressure.
- On crisis signals: point to Telefonul Sufletului 0800 801 200 / 112.
- Nothing sensitive is remembered unless the user explicitly asks.
- The product is for adults.

**Next (v1, voice):**
- `xiaozhi-esp32` (MIT) audio pipeline (Opus over WebSocket) on the 1.75 board.
- This package acts as its LLM provider.
- Target latency: < 1.5 s.

---

## 3. SoulOS web prototype: `os/index.html`

- A single self-contained HTML file (~258 KB). **Open it in any browser**, no server needed. A copy is published as `site/os.html`.
- Controls: tap/swipe, or on the keyboard ← → apps, ↑ Today, ↓ back, Space hold = talk, Enter = tap, D = double tap, Esc = side button.
- Contents:
  - the Home face;
  - Today;
  - Talk (modes none / Claude / ChatGPT);
  - the Keyboard (round QWERTY, RO diacritics, undo);
  - Claude (approve and type);
  - Notes, Reminders, Alarms (Rim-Dial), Focus/Timer, Diary, Weather, Music, Settings, a small game;
  - RO/EN and a scripted tour.
- Screenshots: `os/screenshots/`. Keyboard language mock-ups: `os/lang-mockups/`. Research: `os/research/01–04`.

**How it maps to firmware:**

| Web prototype | Firmware today | Firmware later |
|---|---|---|
| Eye renderer (a JS port of `Face.cpp`) | `Face`, `Brain`, `Personality` ✔ | – |
| Round keyboard, TextField, suggestions | `Keyboard`, `TextField`, `Predictor` ✔ (tested) | swipe, Gaussian decoder, dictation |
| Alarm Rim-Dial | `TimePicker`, `Alarms` ✔ | ringing from any power state (0.2) |
| Cards over the face, the app ring | `Shell` (minimal router) | Card manager / Compositor (0.1) |
| Talk / AI modes | – (the `ai/` service has them) | Voice + AI Service (0.5) |
| Claude approve | `ClaudeLink` ✔ | – |
| Today, Weather, Music, Notes sync | – | SoulOS Link + phone app (0.4) |

The UX spec is `os/SPEC.md`. The architecture and the 0.1 → 1.0 roadmap are in `os/ARCHITECTURE.md` §7: 8–10 months with a team, 14–18 months solo + Claude.

---

## 4. Landing page: `site/`

- `site/index.html`: EN by default, RO toggle (`#ro`). Live canvas eyes, the "Works with Claude" demo, the birth certificate, v6 renders (`media/soul-*.jpg`), simulator clips (`media/*.mp4`) and the waitlist.
- `site/preview.html`: a short RO overview for the founder.
- `site/os.html`: the SoulOS prototype.
- Live preview artifact: https://claude.ai/artifact/BUAPPdP1W5xnCvSVcsQXoX

**Config** (`window.SOUL_CONFIG`, top of `index.html`):
- `WAITLIST_ENDPOINT: ""`
- `CURRENCY: "EUR"`
- `PRICES: { founders: 349, standardFrom: 249 }`
- `FOUNDERS_RANGE: "001–025"`
- `FOUNDERS_COUNT: 25`
- `SHIP: { founders: "spring 2027" (only after CE radio testing), standard: "after Founders 00" }`
- `CONTACT_EMAIL`

**Waitlist:**
- The form POSTs JSON `{email, edition, consent, lang, ts, source}` to `WAITLIST_ENDPOINT`.
- **Empty = demo mode:** sign-ups stay in the visitor's `localStorage` and **you receive nothing**.
- Real options:
  - Formspree / Getform (paste the URL);
  - Brevo / Mailchimp through a small Netlify Function or Cloudflare Worker (the API key never goes in the page);
  - Google Apps Script → Sheet (watch GDPR).
- Use double opt-in. The form has a honeypot field.

**Run and deploy:**
- Run locally: `cd site && python3 -m http.server 8000`.
- Deploy on Netlify drop (simplest), GitHub Pages, or a Shopify page template (see `site/README.md`).
- Before launch, replace the placeholder legal footer (company, CUI, address), write the privacy, terms and cookies pages, add the withdrawal button when taking money, and set real ship dates.

*Note: `site/README.md` still describes the older coin renders and €119. The page itself is already on v6 and €349.*

---

## 5. Architecture summary (from `os/ARCHITECTURE.md`)

**Stack:**
```
SOUL device (ESP32-S3)            Phone app (Flutter + native BLE)       Cloud (EU)
  Apps: Face · Today · Talk ·       pairing (LESC numeric compare)          ai/  (FastAPI, Claude / OpenAI,
  Keyboard · Claude · Notes ·  <--> text.push (phone keyboard)       <-->     actions, memory, BYO-key relay)
  Reminders · Alarms · Focus        store.sync · OTA · ANCS/AMS             MCP server (/mcp, OAuth)
  SoulKit / Shell / Compositor      Keychain: user's API key                 <-- Claude / ChatGPT (connector/app)
  Services: Text Input, Notify,
  Time&Alarms, Store, Energy,       Claude Desktop <--BLE Hardware Buddy--> SOUL (approve / deny)
  AI, Link, Update, Permissions
  FreeRTOS / ESP-IDF 5.5 + BSP
```

**Key decisions:**
- One signed image, one foreground app, the face as the home screen.
- Frames are CBOR over a custom GATT service.
- The system does the heavy lifting (keyboard, alarms, AI routing); apps only ask.
- Third-party apps come in phase 2 (Moddable XS, SES sandbox).
- The user's AI key stays on the phone.
