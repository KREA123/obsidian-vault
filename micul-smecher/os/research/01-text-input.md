# SoulOS: text input on a small round touch screen (01)

*24 Sep 2026 · scope: how people type on watch-sized and round screens, what the research measured, what our hardware allows, and 3 keyboard directions for SOUL (EN + RO, diacritics required).*
Tags: **[V#]** fetched this session (list in §9, all fetched 2026-09-24) · **[V local]** checked in our repo · **[K]** prior knowledge, not re-checked · **[E]** estimate or my own calculation.

## 0. Short version
- **The language model matters more than the layout.** A plain QWERTY with 2.9 mm keys and no language model: 13.7 WPM with **21% total errors** [V15]. A mini QWERTY of the same class with a statistical decoder (WatchWriter): **22–24 WPM** [V14, V18]. Apple Watch (Series 7+) and Gboard on Wear OS both ship QWERTY + tap/swipe + prediction [V1, V2, V8].
- **SOUL's screen is larger than an Apple Watch screen.** The active area is Ø43.76 mm (1504 mm²), against 30.9×37.7 mm on a 45 mm Apple Watch [E]. A round QWERTY fits with **4.3–4.5 mm keys (46–48 px)**, about 40% wider than Apple's ~3.1 mm [E]. That is Apple's watchOS *minimum* (28 pt ≈ 4.4 mm) [V3, E], so it only works with a decoder.
- **Ring keyboards keep the middle free** (36–43% of the screen); the best reach 12–17 WPM. SwipeRing does 16.7 mean, 33 peak [V14]. For SOUL a ring keeps the eyes visible while the user types.
- **Voice is about 3× faster** (161 vs 53 WPM on phones) [V21], but the ESP32-S3 can't dictate on-device: ESP-SR recognises only ≤200 fixed EN/CN commands [V29]. **In offline / no-AI mode the keyboard is the only way to enter text.**
- **Romanian:** 25% of running words carry ă/â/î/ș/ț. The most common collisions are function words (să/sa, că/ca, și/si, a/ă/â). Picking each word's most frequent form gives ~94% word accuracy; small neural models reach 97.4–98.6% [E computed, V24]. So: **auto-diacritics in the suggestions, plus long-press as the manual fallback.**
- **Dictionaries cost almost nothing.** Top-20k words per language is ~85 KB front-coded or ~90 KB as a DAWG [E computed]. EN+RO with bigrams stays under 1 MB of a 16 MB flash.

## 1. Our canvas (hardware facts → input consequences)
| Item | Fact | Consequence for typing |
|---|---|---|
| Panel | 466×466 round AMOLED. Active area Ø43.76 mm → **10.65 px/mm**, 1504 mm² [V local brief, E] | About 1.3× the area of a 45 mm Apple Watch screen (396×484 px @326 ppi = 1165 mm²) [E]. The corners are missing, so the width available to each row depends on its height |
| Touch | 1.75: CST9217, INT GPIO11. 1.43: FT3168 at 0x38, **no INT/RST** [V local board.h, hw note 02] | Single touch: no chord-shift and no two-thumb typing. Everything has to be a tap, a long-press, a swipe or a single-finger path. Gesture typing needs ≥60 Hz sampling (poll the 1.43) [E] |
| Button | One side button: press = home, hold = talk, double = back [V local brief] | Inside a text field, **hold = dictate into the field**. That is the same gesture as talking, so nothing new to learn. Press = home keeps the draft; double = close the keyboard |
| Compute | ESP32-S3, 240 MHz ×2, 512 KB SRAM, 8 MB PSRAM, 16 MB flash; partitions 2×6.25 MB app + 3.375 MB SPIFFS [V local platformio.ini, default_16MB.csv] | A tap decoder is <1 ms per keystroke. A gesture decoder is ~5–20 ms [E]. Dictionaries are mmap'd from flash |
| Audio | 1.75 has 2 mics + AEC + speaker. 1.43 has none [V hw note 02] | Dictation is possible on the 1.75 only, and it needs the cloud |

Geometry on SOUL's circle [E, computed]:
| Layout | Key / zone size | Free for text + eyes |
|---|---|---|
| 3-row QWERTY in the widest band (rows 6 mm tall, top row at y=+4 mm) | row 1: 10 keys × **4.30 mm** (46 px) · row 2: 9 × **4.53 mm** (48 px) · row 3: 7 letters + ⇧ + ⌫ × 3.74 mm (40 px) · bottom cap chord ~18 mm → space / mic / done | Top cap ~18 mm tall, ~41 mm wide: about 2 lines of text plus a suggestion strip. The eyes are hidden |
| T9 3×4 in the inscribed square (30.9 mm) | **10.3 × 7.7 mm** keys: meets the 7 mm watch guideline | The square covers ~64% of the disc. Rim slivers are left for chips |
| Ring 7 mm wide (r 14.9–21.9 mm) | 26 letters → 4.4 mm of arc each (47 px). **7 zones → 16.5 mm arc**. 8 zones → 14.4 mm | **Inner disc Ø29.8 mm (317 px) stays free**: eyes, text and suggestions |
| Reference: Apple Watch QWERTY | 45 mm: ~3.1 mm key pitch · 41 mm: ~2.7 mm [E from px/ppi] | Works only because of the decoder and prediction |

## 2. What shipping products do
**Apple Watch** [V1, V2]
- The Series 7 (2021) brought "a new QWERTY keyboard that can be tapped or swiped with QuickPath", with "on-device machine learning to anticipate the next word" [V2].
- The keyboard is **not on Apple Watch SE 3** and not in every language [V1].
- Other input methods [V1]:
  - Scribble: finger handwriting of letters, numbers and punctuation.
  - Dictation. Correct a word by tapping it, "then say a different word".
  - Emoji picker. A nearby paired iPhone can also type into the watch.
- Suggestions show while typing. The Digital Crown moves the cursor and scrolls through the suggestions. You change language by swiping up [V1].
- Lesson: Apple ships a **5-way input menu** (keyboard / Scribble / voice / emoji / phone), not one perfect keyboard.

**Samsung (Tizen → Wear OS)** [V4–V7, V18]
- The Gear S2's system keyboard (1.2" round, Tizen) was **T9** [V18].
- On the Galaxy Watch4 the default stayed "a traditional T9 style of keyboard". QWERTY with swipe came in One UI Watch 4.5 (2022); users switched to Gboard earlier because it is "much faster than the default T9" [V5].
- The current support page lists voice (the "fastest", needs network), handwriting, keyboard "QWERTY or 3x4", and up to 2 input languages [V4].
- Design guidance [V6]:
  - The text field moves up so the cursor stays visible.
  - Long phrases overflow to the left, and the user swipes the field to review them.
  - The input delegator offers app-provided suggestions, voice, emoji and handwriting.
- Bezel rules [V7]:
  - "Rotating the bezel by one detent moves it by 15 degrees".
  - "each screen should have only one element controlled by the rotary action".
  - On Tizen, rotating the bezel switched the keyboard between T9, numbers, symbols and emoji [K].

**Wear OS Gboard (2021)** [V8]
- Full QWERTY with tap, glide typing and autocorrect, plus scrollable suggestions.
- Voice is built into the keyboard, so there is no mode choice. Emoji and number pads are included.
- "spacing between keys should be dynamic depending on the size of your Wear OS watch display".

**Pebble watch (third-party, 2013–16; now Rebble / Core Devices [K])** [V9–V11]
- No touchscreen.
- Replies were:
  - Voice: "up to 6 seconds of speech", transcribed through the phone.
  - Canned replies: "create up to 10 completely customized replies".
  - Emoji [V9].
- The Dictation API shows a **confirmation screen**: Select accepts, Back re-dictates, and the user can retry automatically after an error [V10].
- Community keyboards:
  - Tertiary Text: 3 buttons, 27→9→3→1, so **3 presses per letter** [V11].
  - T3 Keyboard: configurable layouts [K].
- Lesson: **voice + canned replies cover most short replies**. A button keyboard is the fallback for when voice is not possible.

**iPod click wheel** [V12, V13]
- Search: "navigate the alphabet" with the wheel, Center enters each character, Next = space, Previous = delete. Results update after the first letter [V12].
- Fast scroll shows a big letter overlay [V12].
- A similar wheel-through-the-alphabet method (LetterScroll) measured **2.9 WPM**, or 4.4 with vowel shortcuts [V13].
- Lesson: rotary letter-picking is fine for **search/filter and names**, not for sentences.

## 3. Research keyboards (measured)
| Technique | Mechanism | Device | WPM | Errors | Screen used | Src |
|---|---|---|---|---|---|---|
| Yi et al. tiny QWERTY | decoder, 30–35 mm keyboard, **no out-of-vocabulary (OOV) entry** | 1.56" | 33.6 | – | 50% | V14 |
| WatchWriter (Google) | mini QWERTY, tap + gesture, statistical decoder | 1.30" | 22–24 | near-zero [K] | 85% | V14, V18 |
| VelociTap / VelociWatch | decoder; lock letters to stop autocorrect | watch-size | 41 | – | – | V18, V14 |
| DualKey | 2 letters/key, picked by which finger (external sensor) | LG G Watch 29.6 mm, keys 5.6×6.5 mm | 12.3 novice → 19.6 @90 min → 22.4 @15 days (max 24.7) | total error rate (TER) 7.5→5.3%, uncorrected 1–2% | 80% | V15 |
| SplitBoard | half-QWERTY, flick to the other half | Galaxy Gear 29.3 mm | 15.3 (15 min) | TER 7.35% | 75% | V15, V17 |
| Plain QWERTY, no language model | 2.9×2.9 mm keys | Galaxy Gear | 13.7 | **TER 21.2%** | – | V15, V17 |
| ZoomBoard | tap to zoom 1.5→4.4 mm, then tap the key | 16.5×6.1 mm keyboard | 7.6 → 9.3 (9.8 on a watch) | TER 7.1%. Without zoom: 4.5 WPM, 14% wrong | 50% | V16, V15 |
| SwipeBoard | 2 swipes per letter (region, then key) | tablet sim | 9.1 → 19.6 (trained) | ~17.5% | 45% | V15 |
| **SwipeRing** | QWERTY-ordered ring, **7 zones**, gesture through the centre + decoder, multi-stroke for OOV | LG Watch Style, round 30.5 mm | **16.7** mean, max 33.2 | TER 5.6% | **36%** | V14 |
| C-QWERTY | ring with one key per letter | 1.39" round | 11.2 | TER 12.5% | 43% | V14 |
| WrisText | wrist-whirl, 6 directions, alphabetical ring | 1.4" | 15.2 | – | 43% | V14 |
| COMPASS | rotate the bezel, 3 cursors that move after each letter, press a button | Gear S2 1.2" round | 9.3 → 12.5 @90 min, expert 15.4 | accuracy held | 36% | V18 |
| BubbleFlick / InclineType / Cirrin | kana ring + flick / tilt + tap / pen path through a ring | watch / watch / PC | 8.0 / 5.9 / 6.4 | – | 52 / 39 / 61% | V14 |
| 1Line (Minuum-like) | 8 ambiguous keys in one row + decoder | iPad | 30.7 after 5×20 min | final 1.7% | 40% of iPad kb | V19 |
| Legacy, for scale | Multitap 11.0 · Graffiti 11.4 · Unistroke 15.8 · EdgeWrite 16.9 · H4-Writer 20.4 | phones / stylus | | | | V16 |

Takeaways:
1. Decoder-backed keyboards (WatchWriter, VelociTap, Apple, Gboard) reach 20–40 WPM on screens smaller than ours. Multi-step methods that need no decoder (zoom, split, 2-swipe) sit at 9–15 WPM for novices.
2. On eyes-free bezel swipes, ring layouts with **6–8 segments** were the most accurate (cited in V14). SwipeRing's 7 zones are 9–18 mm long, above the 7 mm watch guideline [V14].
3. Minuum shrank QWERTY to one line with a decoder. It was demoed on the round Moto 360 in 2014 [V20]. The same idea as an arc on the lower rim is worth a prototype [E].
4. Every high-speed method struggles with OOV words (names, slang, Romanian words typed without diacritics). Each design needs a letter-exact fallback: zoom, multi-stroke or long-press [V14, V15].

## 4. Voice, phone, canned replies
- **Speed.** Speech 161.2 WPM vs 53.5 WPM for the iOS keyboard (EN), with total errors 2.93% vs 3.68% [V21]. For notes and Claude prompts, voice is the main path whenever there is a network.
- **On-device.** ESP-SR MultiNet handles "up to 200 speech commands", Chinese and English only, and **no open dictation** [V29]. So:
  - With AI, dictation runs through the SOUL voice service or the user's own STT key. Romanian needs a cloud STT such as Whisper or Deepgram [K].
  - Without AI, we could have EN command words at most, and no RO.
- **Correction UI:**
  - Show the transcript as word chips. Tap a word to see its alternatives (N-best) or to re-say just that word, as Apple Watch does [V1].
  - Keep the Pebble-style confirm step: accept, or hold again to redo [V10].
  - Keep **"edit with keyboard"** as the last resort.
- **Phone as keyboard.**
  - Apple Watch already lets the paired iPhone type [V1].
  - SOUL: the companion app gets a text field that writes over a BLE GATT characteristic. The ClaudeLink BLE service is the Claude Desktop buddy protocol and should stay separate [E].
  - **BLE HID host:** ESP-IDF's `esp_hid_host` example supports ESP32-S3, so any Bluetooth keyboard could pair with SOUL for desk use [V30]. The stock Arduino core may not expose `esp_hid` [E].
- **Canned and smart replies.**
  - Pebble allowed 10 custom replies [V9]. Samsung lists app-provided suggestions first in its input delegator [V6].
  - SOUL: 3 context chips per prompt. Offline they are fixed. With AI, the LLM proposes them.

## 5. Touch targets and fat finger on a 44 mm circle
- **Finger size.** Index-finger contact area is 28.5–33.5 mm² (~6 mm across) [V14]. The fingertip is 16–20 mm wide (MIT Touch Lab via NN/g) [V23].
- **Target size guidelines:**
  - 9.2 mm (discrete) and 9.6 mm (serial) for thumbs on phones [V22]. NN/g rounds this to 1×1 cm [V23].
  - About 7 mm for smartwatches (Dunlop, cited in V14).
  - watchOS: **44×44 pt by default, 28×28 pt minimum** [V3]. At 2 px/pt @326 ppi that is ≈6.9 / 4.4 mm [E].
- **What fits on Ø43.76 mm:**
  - ~20 targets of 9 mm each [E].
  - A 12-key T9 at 10.3×7.7 mm meets the watch guideline.
  - QWERTY keys at 4.3–4.5 mm sit at Apple's minimum and need a decoder.
- **Fat-finger techniques:**
  - A probabilistic hit model: the drawn key is not the hit area; use a 2D Gaussian around each key × the language model.
  - Commit on **lift-off**, not touch-down, so the user can slide to correct. Show a key callout above the finger against occlusion (ZShift-style methods measured 9.1 WPM as standalone [V18]).
  - Learn a per-user touch offset, since users land below the target centre [K].
  - Enlarge edge-clipped keys inward, and hide keys that the decoder rules out.

## 6. Romanian diacritics (ă â î ș ț)
- **Encoding and fonts:**
  - Use **comma-below ș ț (U+0219/U+021B)**, not the cedilla ş ţ (U+015F/0163). Normalise every input: the phone, Claude output and corpora mix the two. Our corpus did [E].
  - The UI font must cover U+0102/0103, 00C2/00E2, 00CE/00EE and 0218–021B. Fredoka lacks some of these, so Nunito is the fallback [V local SPEC].
- **Numbers from the OpenSubtitles RO top-10k list** [V28, E computed]:
  - 31% of word types and **25% of tokens** carry a diacritic.
  - 1,038 ASCII-folded spellings map to more than one word. They cover 33% of tokens.
  - Picking each word's most frequent form restores **94.1%** of tokens. That is a lower bound, because the corpus contains diacritic-less misspellings such as "daca" and "cand".
  - Most frequent collisions: să/sa, că/ca, și/si, în/in, a/ă/â, asta/ăsta, mai/măi, da/dă, mă/ma, va/vă. These need **bigram context**.
- **Published results:**
  - A char-only BiLSTM gets 97.4% of words right; char+word+sentence gets **98.57%** (50M-word parliament corpus) [V24].
  - The hardest cases are definite vs indefinite (politică/politica) and pairs like fată/față [V24].
  - A larger CNN+LSTM plus a dictionary check reaches 99.86% character accuracy [V25].
  - Only 81% of online RO text uses diacritics [V25].
- **SOUL design:**
  1. **Auto-diacritics.** The user types plain letters. The top suggestion is the diacritic form, applied automatically at space when the bigram model is confident. Otherwise it is offered as a chip.
  2. **Long-press a/i/s/t** opens ă â / î / ș / ț (the iOS/Gboard convention [K]). On a ring layout, long-press the zone.
  3. **Tap a committed word** to cycle its variants (a→ă→â).
  4. Keep a user dictionary of learned names and words in NVS/LittleFS [E].

## 7. Dictionaries and decoder on ESP32-S3
Sizes computed from the OpenSubtitles2018 frequency lists (letters only; RO cedilla folded into the comma forms) [V28, E]:
| List | Token coverage | Raw | gzip | Front-coded | DAWG edges → @4 B/edge |
|---|---|---|---|---|---|
| EN 5k / 10k / 20k | 93.8 / 96.6 / 98.6% | 34 / 71 / 150 KB | 16 / 34 / 72 KB | 22 / 43 / 85 KB | 6.6k / 12.3k / 23.4k → 26 / 48 / 91 KB |
| RO 5k / 10k / 20k | 88.7 / 93.2 / 96.9% | 36 / 77 / 161 KB | 17 / 35 / 73 KB | 21 / 42 / 83 KB | 6.4k / 11.8k / 21.5k → 25 / 46 / 84 KB |

- **Frequencies.** Add 1 B of log-frequency per word (+10–20 KB). A minimised DAWG shares suffixes, so frequencies need word numbering or a perfect hash [K]. A plain trie with frequencies at the terminal nodes is simpler: 21–24k nodes for 10k words ≈ 130–145 KB [E].
- **Published figures:**
  - TWL06, 178,691 words → 113,735 nodes ≈ 341–455 KB at 3–4 B/node [V27].
  - 7M words, 63 MB raw → ~24 MB as a DAWG [V26].
- **Budget [E]:**
  - EN+RO at 20k words each: ~200 KB.
  - Bigrams (~50k per language × ~5 B): ~500 KB.
  - User dictionary: <64 KB.
  - Total **<1 MB of flash**, and a working set under 100 KB of SRAM/PSRAM.
- **Compute [E]:**
  - Tap decoding is a beam search over the trie (beam ~200 × 26 children) with Gaussian key likelihoods and unigram+bigram scores: **<1 ms per tap**.
  - Gesture decoding is SHARK²-style: resample to 32 points, prune by start key, end key and length to ~200–500 candidates, compare shapes: **~5–20 ms**. Templates are built from key centres at runtime, so none need storing.
- **Licence.** The FrequencyWords content is **CC-BY-SA-4.0** [V28], so we must give attribution and share alike. Use it for prototyping. Choose the shipping sources deliberately, for example our own corpus plus permissive lists [E].

## 8. Structured input: alarms and reminders don't need a keyboard
- **Time picker:** a circular drag on the outer ring of the touch area works as a virtual crown or click wheel: hours, then minutes, with a haptic or audio tick every 15° [V7, V12, E]. The Gear S2 bezel had 24 levels per 360° [V18]. Samsung's rule of "one rotary element per screen" applies [V7].
- **Natural language:**
  - "Amintește-mi la 5 să sun la bancă" or "remind me at 5 to call the bank" goes through a small local EN/RO grammar for time expressions, so the common patterns work offline. The LLM handles the rest when online [E].
  - The keyboard only fills the label.

## 9. Sources (all fetched 2026-09-24)
V1 Apple Watch User Guide, Enter text: https://support.apple.com/guide/watch/enter-text-apdaf7837856/watchos
V2 Apple Newsroom, Series 7 (2021): https://www.apple.com/newsroom/2021/09/apple-reveals-apple-watch-series-7-featuring-the-largest-most-advanced-display/
V3 Apple HIG, Accessibility (control sizes table): https://developer.apple.com/design/human-interface-guidelines/accessibility
V4 Samsung support, input text on Galaxy Watch: https://www.samsung.com/ae/support/mobile-devices/how-to-input-text-on-your-samsung-watch/
V5 9to5Google, QWERTY on Galaxy Watch (2022): https://9to5google.com/2022/07/12/qwerty-keyboard-on-galaxy-watch/
V6 Samsung Developer, Galaxy Watch input pattern: https://developer.samsung.com/galaxy-watch/design/patterns/input
V7 Samsung Developer, bezel: https://developer.samsung.com/galaxy-watch-design/interaction/bezel.html
V8 9to5Google, Gboard for Wear OS hands-on: https://9to5google.com/2021/05/10/gboard-for-wear-os-hands-on-tiny-touchscreen-typing-done-right-video/
V9 Pebble legacy help (Rebble mirror), sending texts: https://pebble-help-legacy.rebble.io/help.getpebble.com/customer/en/portal/articles/2424927-sending-texts-from-your-pebble.html
V10 Rebble dev docs, Dictation: https://developer.repebble.com/guides/events-and-services/dictation/
V11 Tertiary Text: https://github.com/vgmoose/tertiary_text
V12 iPod classic User Guide (PDF): https://cdsassets.apple.com/live/6GJYWVAV/user/ma630_ipod_classic_120gb_en.pdf
V13 LetterScroll, CHI 2008: https://www.yorku.ca/mack/chi2008-tinwala.html
V14 SwipeRing, GI 2021 (includes Tables 1–3 comparing watch keyboards): http://www.asarif.com/pub/Rakhmetulla_GI2021_SwipeRing.pdf
V15 DualKey, CHI 2016: https://www.cs.toronto.edu/~aakar/Publications/DualKey-CHI16.pdf
V16 ZoomBoard, CHI 2013: https://chrisharrison.net/projects/zoomboard/zoomboard.pdf
V17 SplitBoard, CHI 2015: https://jonggi.github.io/papers/CHI2015-SplitBoard.pdf
V18 COMPASS, CHI 2017: https://pi.cs.tsinghua.edu.cn/lab/papers/COMPASS_Xin%20Yi_CHI2017.pdf
V19 1Line keyboard, UIST 2011: https://iis-lab.org/paper/UIST2011.pdf
V20 Minuum on Moto 360 (2014): https://tiap.ca/2014/06/whirlscape-releases-demo-of-minuum-keyboard-on-the-moto-360-circular-smartwatch/
V21 Ruan et al., Speech is 3x faster than typing: https://arxiv.org/html/1608.07323v1
V22 Parhi et al., target size study (MSR): https://www.microsoft.com/en-us/research/publication/target-size-study-for-one-handed-thumb-use-on-small-touchscreen-devices/
V23 NN/g, touch target size: https://www.nngroup.com/articles/touch-target-size/
V24 Ruseti et al., Romanian diacritics restoration with RNNs: https://arxiv.org/pdf/2009.02743
V25 romanian-diacritic-restoration: https://github.com/horiacristescu/romanian-diacritic-restoration
V26 Hanov, Compressing dictionaries with a DAWG: https://stevehanov.ca/blog/?id=115
V27 dawg-gen: https://github.com/AndrasKovacs/dawg-gen
V28 FrequencyWords (OpenSubtitles2018, CC-BY-SA-4.0): https://github.com/hermitdave/FrequencyWords (lists en_50k, ro_50k downloaded and analysed)
V29 ESP-SR command word recognition (ESP32-S3): https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/speech_command_recognition/README.html
V30 ESP-IDF esp_hid_host example: https://github.com/espressif/esp-idf/tree/master/examples/bluetooth/esp_hid_host
Local: firmware/platformio.ini, firmware/src/board.h, research/02-hardware, os/SPEC.md.

## 10. Three keyboard directions for SOUL
All three share one **TextInput system service**:
- the same EN/RO decoder with auto-diacritics;
- hold-button dictation into the focused field;
- 3 quick-reply chips;
- a "type on phone" hand-off over BLE.

Only the on-screen layout differs.

**A. "Halo": a ring keyboard around the rim, derived from SwipeRing.**
- **Layout:** letters sit in QWERTY order in 7 arc zones (~16 mm each, 7 mm deep) around the edge. The inner Ø30 mm disc keeps SOUL's eyes, the text line and the suggestion chips.
- **Typing:** the user draws word paths from zone to zone through the middle, or taps zones in a T9-like way. The decoder resolves the word.
- **Exact letters:** for names and OOV words, long-pressing a zone fans its 3–5 letters out large (a ZoomBoard-style second step). Long-press there also gives ă/â/î/ș/ț.
- **Evidence:** it is the only published method designed for round watches that combines a free centre (36% of the screen) with watch-grade targets (zones of 9–18 mm vs the 7 mm guideline), 16.7 WPM mean and 5.6% TER. QWERTY-shaped paths transfer to gesture typing on phones [V14].
- **Brand fit:** the eyes can follow the finger around the ring while you write, which makes this the most "SOUL" of the three.
- **Risks:** users have to learn something new; typing depends on the decoder; tapping one letter at a time is slow.

**B. "Round QWERTY", the familiar path (Apple Watch / Gboard style).**
- **Layout:** 3 rows fitted to the widest band of the circle, with 4.3–4.5 mm keys (46–48 px, ~40% wider than on a 45 mm Apple Watch). Space, mic and done sit in the bottom cap. Text and 3 suggestion chips sit in the top cap.
- **Typing:** tap, with a probabilistic hit model and commit on lift-off. QuickPath-style swipe comes in phase 2 with the same decoder. Long-press a/i/s/t for diacritics and long-press q–p for digits.
- **Evidence:** there is zero learning, which suits a first-time, non-technical buyer. Decoder-backed mini QWERTYs are measured at 22–24 WPM on smaller screens [V14, V18]. Apple and Samsung both converged on it after T9 [V2, V5].
- **Cost:** while typing it covers ~55–60% of the screen, so the face shrinks to a small pair of eyes in the text strip. It is the weakest option for older users' fingers.
- **Assessment:** lowest risk, least distinctive.

**C. "Say it, fix it": voice-first, with big-key T9 as the offline keyboard.**
- **Voice:** hold the button and speak. The transcript appears as tap-to-fix word chips with N-best alternatives [V1, V10]. Voice is 3× faster than any keyboard [V21], and Pebble and Samsung both call it the primary path [V4, V9].
- **Alarms and reminders:** handled by the rim-drag time picker and local EN/RO time grammar (§8), not by typing.
- **Offline / no-AI keyboard:** a 3×4 predictive T9 in the inscribed square, with **10.3×7.7 mm keys** (above every watch guideline and near the 9.2 mm phone guideline) and EN/RO word disambiguation with diacritics.
- **Longer text:** "Type on phone" over BLE, or a paired Bluetooth keyboard via HID host [V30].
- **Evidence:** it matches how people actually use tiny devices, best serves users with less dexterity, and stays usable offline. The honest cost is T9's familiarity gap (Samsung users left T9 for QWERTY [V5]) and ~11–15 WPM on-device.

**Suggested path [E]:**
- **Ship C's service layer first**: voice, chips, phone hand-off and the time picker.
- **Build A and B side by side** in the web prototype on one decoder and test 5–8 people (RO + EN phrases, WPM/TER) before committing firmware.
- **Keep T9 as the "large keys" accessibility option** whichever wins.
