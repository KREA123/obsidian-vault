# SoulOS Keys: Round QWERTY (familiar keyboard) + Rim-Dial time picker

est_wpm=20 min_target_mm=4.13

Risks:
- Letter keys are 44 px = 4.13 mm wide (row 2: 4.41 mm) by 4.88 mm tall. That is below the watchOS 28 pt ≈ 4.4 mm minimum and near the geometric ceiling for a 10-key row on a Ø43.76 mm disc, so accuracy depends on the decoder. Older users and people with large fingers may struggle; mitigations are the 'Taste mari' T9 mode, voice and the phone hand-off.
- On the 1.43" dev board the touch view is Ø36.75 mm (12.68 px/mm), so the same layout gives 3.5 mm keys. Judge typing only on the 1.75.
- Swipe typing needs timestamped touch at 60–100 Hz. The firmware today polls touch once per frame (30 Hz). The CST9217 report rate is unverified, and the FT3168 on the 1.43 has no INT, so it must be polled over I2C shared with the IMU.
- Side button hold = dictate conflicts with the AXP2101 PWR-key setup in src/main.cpp pmuInit (reg 0x27 = 0x10, 'hold 4 s to power off'). If the product side button is the PMU PWR key, dictating for more than 4 s would power the device off. Either raise the off-level to 10 s or move the side button to a GPIO.
- Auto-diacritics will still get about 3–6% of ambiguous words wrong (fată/față, politica/politică, a/ă/â, asta/ăsta). Wrong automatic changes annoy users, so the ⌫-revert, the lock after revert, the mint underline and tap-to-cycle must feel instant. Tune the confidence threshold on real user logs.
- Dictionary licensing: the prototype word lists (FrequencyWords, CC-BY-SA-4.0) are share-alike, so shipping lexicons and bigrams need permissively licensed or self-built EN/RO corpora that include clitic forms (s-a, într-o, n-am).
- The keyboard covers about 67% of the disc and the eyes shrink to a 28×36 px header pair. The character is less present during long typing, which works against the product's 'character first' principle.
- Rendering: there is no DMA or double buffer yet (blocking pushRect at 40 MHz QSPI). A full keyboard draw is about 12 ms of push plus render, so the opening, dictation and review transitions may drop frames until DMA lands. User-dictionary flash writes stall the cache and must be batched.
- Gesture conflicts: swipe typing and callouts vs the global swipes, boop and hold-to-talk (the Shell must route every touch over the keys to the IME). Shake-to-undo can fire by accident while walking, so it only ever offers a pill and never acts. The 350/380/400/500 ms timing constants in the firmware and the prototype must be unified.
- The 24 h sundial hour ring (0 at the bottom, 12 at the top) is new to users even though the minutes dial is a normal clock face. The live 'sună în X h Y min' line and the live digits are the safeguard; confirm in user tests or fall back to a Material-style two-ring 12/24 dial.
- Fonts: Fredoka lacks ă ș ț, so the keyboard uses Nunito while the digits use Fredoka. This is a visual mismatch, and the icons (⌫ ⇧ ↑ ✓ mic) must be drawn as SDF shapes because neither font has those glyphs.
- Dictation needs a network plus the SOUL voice service or the user's own STT key, because Romanian cannot be dictated on-device (ESP-SR is EN/CN commands only). Offline, typing is the only way to enter text, so the keyboard quality is critical in 'no AI' mode.
- WPM estimates are extrapolated from published watch keyboards (WatchWriter 22–24 WPM, plain QWERTY without a language model 13.7 WPM with 21% errors), not measured on SOUL. Validate with 5–8 users before committing firmware.

# SoulOS Keys: Round QWERTY + Rim-Dial

*Direction B from os/research/01 §10, worked out in full. The goal is the familiar path: a phone/Apple-Watch-style QWERTY fitted to the circle, with tap and swipe typing, EN+RO prediction, auto-diacritics and one-tap dictation. There is nothing new to learn.*

**Mock renders (verified geometry, 466 px screen):** `/tmp/claude-0/-home-user-obsidian-vault/ed786c2e-2b4e-5bb0-b0e8-a62c849e07d8/scratchpad/soulos/kb/`
- `s00.png`–`s11.png`: one PNG per state (list in §17).
- `sheet.png`: all states on one page.
- `mock.html` and `gen.mjs`: the SVG generator.
- `geom.py`: the fit checks.

## 0. Principles
1. **Same as your phone.** QWERTY rows, ⇧ left of Z, ⌫ right of M, `?123` / space / done along the bottom, a 3-slot suggestion bar, long-press for accents and long-press on space to move the cursor. Every gesture is one people already know from iOS or Gboard.
2. **The decoder does the precision.** The drawn key is not the hit area. A Gaussian touch model is combined with the EN+RO language model. This is how Apple Watch and WatchWriter make tiny keys work (22–24 WPM measured, research 01 §3).
3. **Romanian needs no extra keys.** You type plain letters. `sa` becomes `să`, `intro` becomes `într-o`, and ⌫ undoes any automatic change.
4. **Voice is one tap away.** There is a mic key, and holding the side button dictates into the field.
5. **SOUL stays present.** The eyes sit in the header and watch your finger.
6. **The keyboard is a system service.** Apps call `text.request()` and get back committed text only (research 02 §6, D5).

## 1. Geometry (1.75″: 466×466 px, Ø43.76 mm, 10.65 px/mm; centre 233,233)
Key caps stay inside r ≤ 229 px. Hit areas run to the rim.
```
 y px      layout (checked in geom.py / renders)                        width used / chord
  18– 62   eyes: 2×(28×36 px), gap 50, centre (233,40)                   ~110 / 190
  64– 96   text line n-1  (26 px Nunito, 32 px line height)              ≤300 px
  96–128   text line n (caret line; text is bottom-aligned)              ≤359 px
 134–180   [ "zi" ] │ [  zilei  ] │ [ ziua ]   suggestion bar            118+150+118 (+12) / 413
 184–236   q  w  e  r  t  y  u  i  o  p      10 × 44 px              440 (x 13–453) / 447
 236–288    a  s  d  f  g  h  j  k  l        9 × 47 px (½-key stagger) 423 (x 22–444) / 445
 288–340   ⇧  z  x  c  v  b  n  m  ⌫         46 + 7×44 + 46           400 (x 33–433) / 405
 346–398      ?123 | 🎤 | ␣ RO·EN  | ↑/✓     62 | 54 | 128 | 68         312 (x 77–389) / 318
 398–466   black: no page dots while the keyboard is open
```
- **Key centres.**
  - Row 1, y=210: x = 35, 79, 123, 167, 211, 255, 299, 343, 387, 431.
  - Row 2, y=262: x = 45, 92, 139, 186, 233, 280, 327, 374, 421.
  - Row 3, y=314: ⇧ 56, z 101, x 145, c 189, v 233, b 277, n 321, m 365, ⌫ 410.
  - Action row, y=372: ?123 108, mic 166, space 257, done 355.
- **Worst cap corners** are at r = 225.4 (row 1), 226.8 (row 3) and 227.1 (action row), all inside 229.
- **Physical sizes.**
  - Letter hit areas: 44 px = **4.13 mm** wide (row 2: 47 px = 4.41 mm), 52 px = **4.88 mm** tall.
  - Visible caps: pitch − 4 px by row − 6 px, radius 9.
  - Function keys: ⇧/⌫ 4.3 mm, ?123 5.8 mm, mic 5.1 mm, **space 12.0 mm, done 6.4×4.9 mm**.
  - Suggestion chips are 11–14 × 4.3 mm.
  - About 45 px (4.2 mm) is the geometric ceiling for a 10-key row on this disc. A 45 mm Apple Watch has ~3.1 mm keys.
- **Screen share.** Header and text take 23% of the disc, the suggestion bar 12%, the keys 41.5% and the action row 11%. The keyboard covers **67%** in total.
- **Edge rules.**
  - The first and last keys of each row own the hit area out to the rim.
  - The action row owns everything below it down to y=466.
  - The text field owns y 56–130.
  - The suggestion bar owns 130–182.
- **1.43″ dev board:** its touch view is Ø36.75 mm (12.68 px/mm), so keys shrink to **3.5 mm**. Treat it as a dev board only (see risks).
- **Numeric fields** (`kind:number`) use a 3×4 pad inside the inscribed square instead: 96×62 px keys (9.0×5.8 mm).

## 2. Layers and keys
- **Letters.** Keys show lowercase and switch to uppercase while shift is on, so the state is always visible.
  - Auto-capitals at the start of the field and after `. ? !` plus a space.
  - ⇧ tap = one capital. A second ⇧ tap within 300 ms = caps lock (the ⇧ icon is filled and underlined).
- **`?123` layer.**
  - Row 1: `1 2 3 4 5 6 7 8 9 0`.
  - Row 2: `- / : ; ( ) € & @ "` (10 keys × 44 px, fits a 445 px chord).
  - Row 3: `#+=` 58, `. , ? ! '` at 56 each, ⌫ 58.
  - Action row: `ABC` in place of `?123`.
- **`#+=` layer:** `[ ] { } # % ^ * + =` / `_ \ | ~ < > $ £ „ ”` / `… · ° ⏎` (⏎ = newline, notes only).
- **Long-press, 380 ms still (≤12 px).** A variant tray opens toward the screen centre. The **RO letter is pre-selected under the finger**, so press-hold-lift gives it. Slide to pick another, lift outside the tray to cancel.

| Key | Variants (tray order) |
|---|---|
| a | **ă** â à á ä |
| i | **î** 8 í ï |
| s | **ș** š ß |
| t | **ț** 5 |
| e | 3 é è ê ë |
| o | 9 ö ó ô |
| u | 7 ü ú |
| c | ç č ć |
| n | ñ |
| q w r y p | 1 2 4 6 0 (top-row digits, Gboard convention) |
| . | … |
| - | – |
| " | „ ” « » |
| ' | ’ |

- **Punctuation without a layer switch:**
  - Two spaces within 450 ms insert `. ` and auto-shift (iOS convention).
  - The language model also offers `?` or `.` in the suggestion bar when it predicts the end of a sentence (for example after `ce faci`).
  - **Long-press `?123`** opens a tray `. , ? ! ' -`; slide and lift to insert.
- **No emoji in v1** (no font cost). There are no Unicode symbol glyphs either: ⇧ ⌫ ↑ ✓ mic ■ and the clock icon are SDF shapes, because Nunito lacks them.

## 3. States (Keyboard state machine, one owner: the TextInput service)
`CLOSED → OPENING(260 ms) → IDLE{layer: abc|123|sym, shift: off|once|lock}`

From IDLE:
- `KEYDOWN(k)`, then:
  - lift within 380 ms → `COMMIT(k)`;
  - still for 380 ms → `VARIANTS`, lift → commit;
  - moved >24 px → `PATH`, lift → `DECODE` (the word plus an automatic space).
- `SPACEDOWN`, then 380 ms still → `TRACKPAD`, lift → IDLE.
- `BKSPDOWN` → `REPEAT`.
- mic tap or side-button hold → `DICTATE{listen → final | error}`.
- Swipe down that starts in the text or suggestion zone → `REVIEW`.
- done → `SENDING → CLOSED` (Ev::TextCommit).
- Side double-press → `CANCEL`: the draft is kept, then `CLOSED` (Ev::TextCancel).
- Side press → HOME: the draft is kept.

Visual states rendered:
- 0: empty field with context chips.
- 1: key callout.
- 2: auto-diacritic suggestion.
- 3: variant tray.
- 4: `?123` with a time detected in the text.
- 5: swipe trail.
- 6: dictation.
- 7: review.
- 11: cursor trackpad.
- Not rendered: shift, caps lock, `#+=`, word-tapped alternatives, no-network mic, secure field.

## 4. Interactions (unified timings; the firmware today uses hold 0.5 s and double-tap 0.40 s, which must be aligned)

| Input (while the keyboard is open) | Result |
|---|---|
| Tap a key | Highlights on touch-down within ≤1 frame. The callout (58×66 px, 36 px glyph) appears above the finger, clamped inside the circle. The character **commits on lift-off**, so you can slide to fix a key. The system's double-tap merge is off (`doubleTapS=0`) |
| Drag across keys (>24 px) | Swipe typing, QuickPath-style. An ice trail is drawn; the word is decoded on lift (5–20 ms) and inserted with an automatic space. The suggestion bar shows alternatives. **App swipes (← → ↓) and boop/hold-to-talk are disabled over the keys** |
| Long-press a key | Variant tray (§2) |
| Long-press space | **Trackpad.** Key labels fade to 12% and the space bar shows ◂ ▸. 16 px of horizontal drag = 1 character; 40 px of vertical drag = 1 line. Lift to place the caret |
| Tap a word in the text | The caret jumps to that word's end (iOS). Tap the same word again within 1.5 s to select it: it gets a cream 25% highlight and the suggestion bar shows its variants (`sa/să/șa/s-a`), the decoder's alternatives and `↶ original`. Typing replaces the selection; ⌫ deletes it |
| ⌫ tap / hold | Deletes one character. **Right after an automatic change it reverts that change instead.** Hold: repeat starts at 450 ms at 12/s, and after 1.2 s it deletes whole words at 6/s. Clearing ≥1 word puts a `↶ Anulează` chip in the suggestion bar for 5 s |
| Swipe ↓ starting in the text or suggestion zone | REVIEW: the keys slide away and the full draft fills the disc. Tap a word to edit there. `✓` finishes |
| Shake (IMU) | The eyes do the dizzy reaction, and a pill asks `Anulezi ultima modificare? [Anulează]` (the iOS shake-to-undo pattern). The pill is never applied without a tap |
| Side button: press | Home. The keyboard closes and the draft is kept |
| Side button: hold | **Dictate into the field at the caret** (push-to-talk). This is the same gesture as talking everywhere else |
| Side button: double | Back/cancel. The draft is kept and a pill says `Ciornă păstrată · atinge = șterge` for 3 s |
| Done (↑/✓) | Commits the text to the calling app (§9) |

Undo covers 32 edit operations (insert, delete, replace plus caret position) in RAM. Redo is offered as `↷ Refă` on the undo pill.

## 5. Romanian diacritics
- **Folded index.** Each lexicon is keyed on a folded form: lowercase, diacritics removed (ă/â→a, î→i, ș→s, ț→t, é→e…), hyphens and apostrophes dropped. One folded key lists all its surface forms:
  - `sa` → {să, s-a, sa, șa}
  - `intro` → {într-o, intro}
  - `nam` → {n-am}
  - `dont` → {don't}
  - `im` → {I'm, îm-}

  Romanian clitics (s-a, n-am, mi-a, l-am, într-un, dă-mi, spune-mi) and English contractions are ordinary entries, so nobody ever needs the hyphen or apostrophe key.
- **Auto-diacritics.** At space or punctuation, a folded word is replaced by its best surface form P(w | prev, lang) when **P ≥ 0.80 and the form is at least 2× more likely than the runner-up**. Otherwise the plain letters stay and the diacritic form becomes the bold middle suggestion, with its diacritic letters drawn in **mint** (render s02).
  - Expected accuracy: 94% word-level from the unigram model alone, ~96–97% with bigrams (research 01 §6).
  - Hard pairs such as fată/față and politica/politică are handled by the next rule.
- **Every automatic change** gets a 2 px mint underline that fades over 600 ms, and the eyes glance at the word. **⌫ right after it restores exactly what you typed**, and that word is not auto-changed again for the rest of the session (VelociTap-style lock).
- **Manual paths:**
  - Long-press a/i/s/t: the RO variant is pre-selected (§2).
  - Tap a committed word to cycle its variants.
  - Swipe-typed words get diacritics the same way.
- **Encoding.**
  - Only **comma-below ș ț (U+0218–021B)** are ever emitted.
  - Incoming cedilla ş ţ (U+015E/F, U+0162/3) from the phone, AI replies or the clipboard are normalised.
  - Text is stored as NFC UTF-8. The caret moves by code point.
- **Language mixing.** Both lexicons are always live. A language posterior is taken over the last 6 words. In an EN-dominant sentence, no RO diacritics are applied (so `a`/`sa` stay as typed).
  - The space bar shows `RO · EN`.
  - Settings can turn one language off.
  - The `🌐` key on the `#+=` layer flips the preferred language for tie-breaks.

## 6. Prediction and correction (on-device, offline, no network)
- **Tap decoder.**
  - Each touch gets a 2D Gaussian likelihood over the nearest 6 keys (σx = 0.45 × pitch ≈ 20 px, σy = 0.5 × row ≈ 26 px).
  - A per-user offset (dx, dy per row) is learned from committed words (EWMA over 200 samples, 12 B in NVS). People tend to land low.
  - Beam search, width 64, over the folded trie; score = Σ log P(touch|key) + λ·log P(w|w₋₁) + a completion bonus.
  - The literal string is always kept as a candidate. Cost is **<1 ms per tap**.
- **Swipe decoder**, SHARK²-style.
  - The path is resampled to 32 points.
  - Candidates are pruned by start key and neighbours, end key and path length (≤500 left).
  - A shape channel and a location channel are combined with the language-model prior. Templates are generated from the key centres at runtime.
  - Runs in **5–20 ms** in a worker on core 0; the result shows on the next frame. The top 4 go to the suggestion bar.
- **Suggestion bar rules.**
  - While typing:
    - **left** = the literal (in quotes if it is not a word);
    - **middle, bold** = what space will insert;
    - **right** = the next best.
  - After a space: 3 next-word predictions, plus `?` or `.` when the end-of-sentence probability is high.
  - Empty field: 3 context chips supplied by the app (render s00). Offline they are fixed; with AI linked the app may pass LLM-generated chips. The IME itself never goes online.
  - `▭ Telefon` chip: hands off to the phone keyboard over SoulOS Link, and the text streams in live.
- **Autocorrect guard rails.** A word is replaced only if the literal is not in the lexicon or the user dictionary, the best candidate is ≥2× more likely than the literal, and the edit is ≤2 key-neighbour edits. Autocorrect never touches:
  - words typed through the variant tray or reverted once;
  - numbers, URLs and e-mail addresses;
  - words with capitals in the middle;
  - secure fields.
- **Learning.**
  - User unigrams (2k) and bigrams (4k), stored in LittleFS `store/ime/`.
  - A literal typed and kept twice becomes a word.
  - Phone contacts' first names can be added, opt-in.
  - Nothing is learned in secure fields. `Setări › Tastatură › Uită cuvintele` erases it all.
  - Writes are **batched when the keyboard closes or after 60 s idle**, to avoid flash stalls.
- **Local time grammar (EN/RO, ~8 KB).** It spots expressions such as `la 7`, `mâine la 9:30`, `în 10 min`, `diseară`, `at 7pm`, `tomorrow 9am`, and offers a mint action chip `⏰ Alarmă 17:30` / `Memento mâine 9:00` (render s04). The chip calls the `alarm.set` or `reminder.create` intent, with the rest of the text as the label. It works with no AI.

## 7. Cursor, text field, review
- **Text field.**
  - Bottom-aligned, 2 visible lines on the round chords (≤300 / ≤359 px ≈ 24 / 29 characters).
  - The caret line is always the lower line; earlier lines scroll up.
  - Caret: 3 px ice `#9FC6FF` bar, blinking at 1 Hz.
  - Placeholder in cream at 38% (`Scrie-i lui Claude…` / `Notiță nouă…` / `Numele alarmei…`).
  - Maximum length: Claude 1000, note 2000, reminder 120, alarm label 48 characters. Above 90% a counter appears at the right end of the suggestion bar.
- **Review** (render s07): up to 7 lines of 26 px on round-aware lines, eyes at k≈0.18, `[⌨ Editează] [✓ Salvează/Trimite]`.
- **Secure field** (`secure:true`, for example a Wi-Fi password if one is ever typed on the device): no prediction and no learning. Each character shows for 1 s, then becomes a dot.

## 8. Voice dictation (fast switch)
- **Start:** tap the mic key (toggle), or hold the side button (push-to-talk).
- **Listening** (render s06):
  - Keys fade out over 150 ms, and the eyes grow into the key area (k≈0.5, centre y 262) in listening pose.
  - The **ice ring is drawn on the rim by the OS whenever the mic is on** (SPEC §7.2).
  - The label reads `ASCULT…`. Provisional words stream in ice and turn cream when final.
  - The key area becomes one ice pill `■ Gata`.
- **Stop:** tap anywhere, release the button, or 1.5 s of silence (VAD). Then the keyboard returns.
- **Correcting:** tap a dictated word to see its N-best alternatives plus a `🎤 spune din nou` chip that re-dictates just that word (Apple Watch pattern).
- **Transcription** goes to the cloud through the Voice service: the SOUL voice service or the user's own STT key. Cloud STT returns proper RO diacritics, and the text still passes through the ș/ț normaliser.
- **No network or no AI:** the mic key is dimmed with a slash. Tapping it shows an amber pill `Dictarea are nevoie de conexiune`, the eyes make "?", and typing keeps working 100% offline.
- **1.43 board (no mic):** the mic slot becomes a `,` key and the side-button hold does nothing inside fields.

## 9. Done / send / cancel and the API
`text.request({kind: text|number|time|date, context: claude|note|reminder|alarm_label|reply|search, action: send|save|ok, placeholder, initial, lang: auto|ro|en, suggestions[], maxLen, secure})` → `Ev::TextCommit{utf8}` | `Ev::TextCancel{draft}`.

| Context | Done key | After done |
|---|---|---|
| Claude / Talk / reply | **amber #FFB347 pill with a black ↑** (send). Disabled (FN cap, glyph at 30%) while empty | The text line shrinks and **flies into the eyes** (300 ms), the eyes blink and "gulp", then the Claude *think* state. Offline, it is queued in `outbox` and a pill says `Trimit când am conexiune` |
| Note | **mint #C9F2E4 pill with ✓** (save) | The text drops into a mint pill `Notiță salvată ✓`; the eyes do Celebrate |
| Alarm / reminder label | mint ✓ | Back to the alarm summary (§13) |
- Cancel is always the side double-press or the calling card's own back. Drafts are keyed by (app, field): kept in RAM, flushed to `store/drafts` when the keyboard closes, and kept for 24 h. The draft comes back when the field is reopened.
- Apps never see keystrokes, only committed text. The IME has no network capability.

## 10. Eyes and face while typing
- **Layout.** Header: `FaceLayout{k≈0.14, cy=−0.83}`, eyes 28×36 px, gap 50, centre y 40. This is the same "face shrinks to the header" rule as for cards (SPEC §2), one step smaller.
- **Gaze follows the finger:**
  - gx = (x − 233)/233 × 0.6, with an 80 ms lag;
  - gy looks down at the keys;
  - during a swipe the eyes track the path;
  - after 3 s idle they look at the caret ("reading");
  - on each auto-change they glance at the word for 250 ms.
- **Micro-life:**
  - they blink every 3–6 s;
  - a 2 px nod on each committed word;
  - they squint while ⌫ is held;
  - half-lids ("focused") during a fast streak;
  - after 20 s idle they get sleepy, but the keyboard never closes by itself while text exists.
- **Dictation:** the eyes grow into the key area and use the listening pose. **Review:** k≈0.18. **Time picker:** inside the ring, looking at the knob.
- Brain rules: keyboard touches never cause boop or laugh reactions, because the Shell consumes them before the Brain. Shake still plays the dizzy reaction and adds the undo offer.
- Cost: the eyes' dirty rect is about 120×50 px, so 30 fps is essentially free.

## 11. Look (SoulOS language)
- **Colours.**
  - Background `#000`.
  - Letter caps `#1A1813`; function caps `#26231B`; pressed cap `#4A4434`.
  - Callout and tray `#2E2A20` with a 1.5 px cream border at 35%.
  - Labels cream `#FFF0C8`: letters 95%, function keys 80%, space label 38%.
- **Suggestion bar.** The best chip has a `#1D1B16` fill with 700-weight text; the side chips are 72%, weight 500; separators are cream at 18%. Diacritic letters in suggestions are mint.
- **Colour meanings.**
  - Ice = caret, dictation and the swipe trail.
  - Amber = Claude send; also warnings.
  - Mint = saved/set and time action chips.
- **Fonts.** **Nunito**: keys 25 px/600, callout 36/700, variant tray 30/700, text 26/500, suggestion bar 23 (at least 22 everywhere, per SPEC). Fredoka lacks ă ș ț, so the whole keyboard uses Nunito. Fredoka stays for the time digits (104/64 px) and ring numerals (22 px).
- Colour never carries meaning alone: the done key is ↑ or ✓, and every auto-change has an underline.

## 12. Animation and timing
- **Opening:** the rows rise 24 px and fade in, staggered 40 ms per row (row-level dirty rects, cheaper than a full slide). The eyes spring to the header (9/s spring, SPEC). About 260 ms in total.
- **Key press:** the callout scales 0.8→1 in 60 ms and fades out over 80 ms after lift. The variant tray grows in 90 ms. Layer labels cross-fade in 100 ms.
- **Changes:** an auto-change cross-fades in 120 ms. The swipe trail (5 px ice + 16 px glow) fades 250 ms after lift.
- **Sending:** the fly-into-eyes animation takes 300 ms, ease-in. Cancelling sinks the keyboard in 200 ms.
- **Reduced motion:** everything is instant; callouts are static.
- **Haptics (LRA):**
  - 8 ms tick per committed key;
  - double tick on an auto-change;
  - 15 ms tick when the tray opens;
  - ticks on dial steps (§13).
- **Latency targets:** key highlight ≤40 ms; character on screen ≤50 ms after lift; swipe word ≤80 ms after lift.

## 13. Time picker: "Rim-Dial" (alarms and reminders need no typing)
```
            ·  ·  12 ·  ·            ring r 190–220 (track #1A1813), ticks r 222–230
        ·      ALARMĂ      ·         label y 66 (22 px, cream 60%)
      ·         ◖ ◗          ·       eyes y 108 (26×34) looking at the knob
   (07)                        ·     knob Ø54 px (5.1 mm) cream, value inside, glow
     6       07 : 30         18      digits Fredoka 104 px, centre y 212; active part 100%,
      ·      ▔▔▔              ·        inactive 38%, cream underline under the active part
        ·  sună în 9 h 12 min ·      relative time y 300 (22 px, 55%)
          ·     [ ✓ ]      ·         mint pill 120×52 at y 324–376
               ·  0  ·               ring numerals sit on the track (22 px Fredoka)
```
- **Hours:** a 24 h "day ring" drawn like a sundial.
  - 0 at the bottom, 6 on the left, 12 at the top, 18 on the right, clockwise, θ = 90° + 15°·h.
  - The top half (06–18) is tinted cream at 16% (day); the bottom half is ice at 16% (night).
  - One hour is 15° = 53.7 px of arc = **5.0 mm**. Haptic tick per hour, stronger at 0/6/12/18.
- **Minutes:** a normal clock face, 00 at the top, θ = −90° + 6°·m. A cream sweep arc (22%) runs from 00 to the knob. Labels read 00/15/30/45.
  - **Snapping depends on speed:** above 90°/s it snaps to 5 minutes (30° = 10.1 mm); slower, to 1 minute (6° = 2.0 mm).
  - Ticks per step, stronger every 5 minutes.
- **Touch.**
  - A touch at r ≥ 150 px sets the value by **absolute angle**, and the drag is captured, so drifting inward keeps working.
  - Lifting in hours mode **advances to minutes after 400 ms**.
  - Tap `07` or `30` to switch mode.
  - ✓ confirms. Side double = back without setting; press = home.
  - Side hold = say `șapte și jumătate` and the value is filled in.
- **Starting value:** the next whole hour, or 07:00 for the first alarm.
- **The live relative-time line** (`sună în 9 h 12 min`) is the guard against mixing up the two halves of the day.
- **Alarm summary** (render s10), stacked in the centre:
  - `ALARMĂ` label (y 56) and eyes (y 92);
  - `07:30` at 64 px (y 148), which opens the dial again when tapped;
  - `Mâine · în 9 h 12 min` (y 196);
  - `✎ Trezirea` chip (y 218–270), which opens the keyboard with `context: alarm_label` and chips [Trezirea][Pastile][Sală];
  - mint `✓ Setează` (y 282–334).
  - **Weekday ring on the lower rim:** 7 dots, Ø46 px, at r=180, θ from 144° down to 36° in 18° steps (56 px apart), `L Ma Mi J V S D` / `M T W T F S S`. Tap to toggle.
- **Flows.**
  - Offline alarm: `+` → drag the hour → drag the minutes → ✓ → ✓ Setează. That is **5 actions** with no letters. It ends with a mint pill `Alarmă 07:30 ✓ · în 9 h 12 min` and happy eyes.
  - Reminders use the same dial plus a day chip `Azi / Mâine / Alege`. `Alege` puts the dial in 7-day mode, one dot per upcoming day.
  - Focus can reuse the minutes dial as a duration picker.
- **Cost.** It is built from the Canvas `ring/arc/segment/ellipse` SDFs plus the Fredoka 104 px digits (shared with Focus). Dirty area while dragging ≈ 51k px (knob old+new, digits, relative line, eyes) ≈ 5 ms to push, so 30 fps holds.

## 14. Accessibility
- **`Taste mari` (large keys):** a 3×4 predictive T9 in the inscribed square (10.3×7.7 mm keys). It uses the same decoder, since folded keys map to digits. Turn it on in Settings, or long-press `?123` → `Taste mari`.
- **Voice** everywhere, plus the **phone keyboard** hand-off.
- **High contrast:** caps outlined 2 px cream at 40%; labels at 100%.
- **Text size:** the field can go from 26 to 32 px, which shows 1 line fewer.
- **Reduced motion** and haptic feedback, with sound off by default.
- **No time limits;** drafts persist.
- The ice ring always shows when the mic is on.
- Readback of the draft (`citește`) through TTS when online, in phase 2.
- **Target honesty:** letter keys are 4.1 × 4.9 mm, below the watchOS 4.4 mm minimum. Accuracy comes from the decoder, which is why the large-key mode and voice exist.

## 15. Memory, compute, power (ESP32-S3R8, 8 MB PSRAM, 16 MB flash)

| Item | Budget | Where |
|---|---|---|
| IME + decoders + dial + time grammar code | ~55 KB | app image |
| Lexicons EN+RO, 20k words each (folded trie + surface-form patches + 1 B log-frequency) | ~360 KB | flash, memory-mapped |
| Bigrams, 50k per language (4 B each) | ~400–500 KB | flash |
| Nunito 4bpp atlases 22/24/26/30/36 px (~175 glyphs: ASCII, Latin-1, ăâîșț, „”’…–€) | ~140 KB | flash (shared UI) |
| Fredoka digits 104 + 64 px | ~35 KB | flash (shared with Focus) |
| **Flash total** | **≈1.0–1.1 MB** of a 4 MB OTA slot | |
| Keyboard base-layer cache (466×264×2) so callouts and trays restore by memcpy | 246 KB | PSRAM (optional) |
| Draft + undo (32 ops) + review buffer | ~8 KB | PSRAM |
| User dictionary loaded | ≤64 KB | PSRAM |
| Decoder beam + swipe candidates | ~12 KB | PSRAM |
| Touch ring buffer (128 timestamped points) + hot beam | ~5 KB | internal SRAM |
| IME worker stack (swipe decode) | 8 KB | internal, core 0 |
- **CPU.** Tap decode <1 ms; swipe decode 5–20 ms off the UI task.
- **Per keystroke,** the dirty area is key + callout + text line + suggestion bar ≈ 36.6k px = 73 KB: ~3.7 ms to push at today's 40 MHz QSPI, plus ~2–3 ms to render.
- **A full keyboard draw** is 123k px (240 KB): ~12 ms to push. The opening transition needs the planned DMA double buffer to hold 30 fps.
- **Touch** needs a dedicated **100 Hz input task with timestamps** for swipe typing:
  - 1.75: CST9217 on INT GPIO11.
  - 1.43: FT3168 polled.
  - Today touch is polled once per frame at 30 Hz, which is too coarse for paths.
- **Power:** a black background with dark caps (≈25% of the disc at ~10% luminance). The panel dominates power draw, so the keyboard costs little more than the face.

## 16. Implementation map (per os/research/03 §9)
- **New in `lib/Suflet/src`,** hardware-free and testable in `native`/`sim`:
  - `Keyboard.h/.cpp`: layout tables for §1–2, hit model, state machine, rendering.
  - `TextField.h/.cpp`: UTF-8, caret by code point, round wrap, undo.
  - `Predictor.h/.cpp`: folded trie, bigrams, tap beam decoder, auto-diacritics, user model.
  - `SwipeDecoder.h/.cpp`, `TimeGrammar.h/.cpp`, `RimDial.h/.cpp`.
  - Prerequisite: the `Font/Text` module.
- **Events and gestures.**
  - Add `TextCommit/TextCancel/AlarmDue` and `InputEv{Ev,x,y,t}`.
  - While the keyboard is open, set `doubleTapS=0` and route hold to variants, not voice.
  - The Shell consumes the events before the Brain.
- **Tests:**
  - key centres → letters; edge taps outside a cap but inside the rim → the end keys;
  - long-press a → ă; `vreau sa␣` → `vreau să␣`; ⌫ after an auto-change → reverted and locked; `intro` → offers `într-o`;
  - cedilla → comma normalisation; caret across ș; wrap at 300/359 px;
  - dial angle ↔ hour on the sundial, including the 0/24 and 59/0 wraps and 5-minute snapping;
  - `mâine la 7 și jumătate` → 07:30 the next day, across a DST change.
- **Sim scene `keyboard`** types `Salut, ce faci? ășțâî` and writes stills.
- **Prototype (`os/index.html`):** add a `#kb` layer and `S.kb`, as mapped in research 03 §9.

## 17. Renders produced (scratchpad/soulos/kb)
- s00: empty field, Claude
- s01: typing with callout
- s02: auto-diacritics
- s03: variant tray
- s04: `?123` with a time chip
- s05: swipe trail
- s06: dictation
- s07: review
- s08: dial, hours
- s09: dial, minutes
- s10: alarm summary
- s11: trackpad
- `sheet.png`: all of the above

## 18. Validation before firmware
Build this keyboard and the "Halo" ring keyboard on one decoder in the web prototype. Test with 5–8 people (RO and EN phrase sets). Pass bar: **≥15 WPM on first use, total error rate ≤8%, ≥90% of diacritic words correct without manual fixes.** Tune σ, λ and the auto-diacritic threshold on those logs.