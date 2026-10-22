# SOUL: campaign video script and shot list

**Version 2 · 2026-10-22 · Indiegogo campaign, scenario `after_ce` (launch Tue 5 Oct 2027; submit for review by 21 Sep 2027)**
Length **2:21** (rough cut `rough-cut.mp4`, 141.1 s). Facts come from `../facts.json` (the single source). The build fills in every size, price, colour and date fact, so a change there (size, D3 ladder, D7 colours, D9 delivery) only needs a rebuild. Plan: `../PLAN.md`.

> **Pe scurt (RO):** filmul de campanie are 2:21 și 10 părți. Rough cut-ul e montat din ce avem deja: randări etichetate, motorul de ochi, capturi SoulOS și ilustrații. Unde lipsește filmare reală apare „[PROTOTYPE SHOT — to film]”: un card întreg (F01, F09) sau o bandă peste înlocuitor (F02–F08). Lista F01–F10 de mai jos spune exact ce filmezi pe SOUL S din aluminiu, după G2 (12 feb 2027). Rough cut-ul are o voce TTS de ghidaj și muzică licențiată doar sub final, și NU se publică. Teaserul vertical de 30 s se poate posta după ce îl verifici.

| File | What it is | Status |
|---|---|---|
| `rough-cut.mp4` | 1920 × 1080, 30 fps, **76 s** (was 2:21; recut after the review of 2026-10-22), 4 MB. Built only from material we HAVE.<br>Missing real shots appear as **[PROTOTYPE SHOT — to film]**: a full card for F09 (the founder, at 0:15), banners over the stand-ins for F01, F07, F11.<br>Voice-over is burned in as captions. Audio is a **guide**: offline TTS voice (Piper `en_US-lessac`) plus the licensed "Sci-Fi Score" under the ask. Stamped "ROUGH CUT · NOT FOR PUBLISHING". | internal animatic, **never post** |
| `teaser-vertical.mp4` | 1080 × 1920, **0:30**, 1.8 MB, for Reels / TikTok / Shorts.<br>Uses only labelled renders, the eyes engine and SoulOS captures, with burned-in captions.<br>Music: "Sci-Fi Score" (Mixkit Free License), cut from the phrase downbeat at 16.68 s. No voice. End card: "coming to Indiegogo · from €249 in the campaign" + the AI line from `labels.ai_short` (own Claude or own OpenAI API key, in development; SOUL does not include AI). | can be posted after the founder's review |
| `subtitles/soul-campaign-roughcut.en.srt`, `.ro.srt` | EN voice-over and RO subtitles, timed to the rough cut | retime after the final edit |
| `build/build.py` + `build/segments.json` | rebuilds both videos: `python3 -I micul-smecher/crowdfunding/video/build/build.py [--only rough\|teaser]`, about 4 min.<br>`segments.json` holds the edit-decision list and the shot briefs. `timeline_*.json` holds the real timecodes. | |
| `youtube-upload.md`, `youtube-thumbnail-1280x720.jpg` | upload sheet for the founder | |

## 0. Rules this video follows

1. **What backers buy is SOUL S:** 63 × 71 mm, 23–26 mm deep (being finalised), round 1.75″ AMOLED 466 × 466, aluminium. The working prototype today is **M** (90 × 101 mm, 2.8″). The video sells S.
2. **The final video needs real footage of a working aluminium SOUL S.** That footage is gate **G2 (12 Feb 2027)**; shoot by 26 Feb 2027. There is no submission for review without it.
3. Real footage of the **M** prototype carries this line, burned in, for the whole shot: *"Prototype shown at a larger size (M). The product you back is S: 63 × 71 mm with a 1.75″ AMOLED."* A G1 bench clip (15 Dec 2026) carries *"Development board, not the final product."*
4. **Anything that shows scale is S only.** Allowed sources: real S footage (F07), `renders/v10/` (used only as `images/story_06b_in_hand.jpg` / `story_06c_on_desk.jpg`, with the old glowing eyes painted over by the eyes engine), or the true-scale graphic `images/gallery_2_size_1200x630.png`.
   - Banned: v9 `hand`, `desk` and `typing`; the trailer at 19.2–22.2 s (M hand); the v9 launch film at 16.0–33.8 s.
5. Every picture that is not real footage carries its label, burned in, top-left:
   - "RENDER (CGI), NOT A PHOTO"
   - "EYES ENGINE: SCREEN ANIMATION FROM THE DEVICE CODE, NOT A PHOTO"
   - "SOULOS SIMULATOR CAPTURE AT S SIZE, 466 × 466. NOT A REAL DEVICE" (firmware 1.9.0 has never run on a real board; "SoulOS (shown on the prototype)" only for real device recordings)
   - "ILLUSTRATION" / "ILLUSTRATION · TRUE SCALE"
6. **No claim that SOUL includes AI.**
   - ChatGPT appears only as "your own OpenAI key, in development". "Sign in with ChatGPT" appears only as "pending OpenAI approval".
   - Voice: the on-screen note says speech-to-text uses your own OpenAI key today. **Never "hold the glass and talk to Claude"** for a Claude-only owner until `product.voice.claude_only_voice_works` is true.
   - No Anthropic or OpenAI logos.
7. **No CE card in the video.** The live campaign exists only after CE (scenario after_ce); the honest status is in the page's status bar, not in the last 20 s of the film. The pre-launch teaser's end card says "Not CE-certified yet" while that is true.
   - Never: backer counts, press, reviews, awards, battery life (not until measured on S), "% off", or "no two are alike" (two SOULs share eyes ~0.9 % of the time).
8. **Rarity changes only the eyes.** Nothing suggests buying, choosing or re-rolling a rarity.

## 1. Structure at a glance

**76 s** (target 75–90 s). A cut every 2–4 s; no still is on screen for more than 3.5 s; the hook question is answered on SOUL's glass by 0:08; the founder speaks at 0:15–0:26; the ask ends on living eyes. No CE card: the honest status lives in the page's status bar (review 2026-10-22).

| # | Section | Time | Picture in the FINAL video | In the rough cut now |
|---|---|---|---|---|
| 01 | Hook | 0:00.0–0:10.0 | **F01** one-take wake → chat box (≤ 1.5 s) → the answer on SOUL's glass → eyes smile | Render (CGI) + F01 banner → Illustration → SoulOS simulator, S 466 → Eyes engine |
| 02 | It looks up when your AI needs you | 0:10.0–0:15.5 | **F04** Claude app → SOUL looks up, hold to allow | SoulOS simulator, S 466 → SoulOS simulator, S 466 |
| 03 | Why I built it (founder) | 0:15.5–0:25.5 | **F09** the founder to camera, 10–15 s | title card → Render (CGI) + F09 continued banner → Eyes engine + F09 continued banner |
| 04 | Alive | 0:25.5–0:31.5 | eyes engine + **F01** follow-the-finger | Eyes engine → Eyes engine |
| 05 | Born with its eyes | 0:31.5–0:36.5 | **F02** birth on 3 units, quick montage | Eyes engine → Eyes engine |
| 06 | Your own AI, or none | 0:36.5–0:45.0 | **F03** hold to talk, **F05** offline | SoulOS simulator, S 466 → SoulOS simulator, S 466 → SoulOS simulator, S 466 |
| 07 | SoulOS | 0:45.0–0:51.0 | **F06** dial on the real S glass | SoulOS web prototype → SoulOS simulator, S 466 |
| 08 | The object | 0:51.0–1:04.5 | **F11** macro finish → true scale → **F07** real palm → colours → OU | Render (CGI) + F11 banner → Illustration · true scale → Render (CGI) · eyes engine + F07 banner → Render (CGI) → Render (CGI) |
| 09 | Promises | 1:04.5–1:07.0 | **F08** finger on/off, no camera | SoulOS simulator, S 466 |
| 10 | The ask | 1:07.0–1:16.0 | **F01** again: price spoken, then the end card with the eyes alive | Render (CGI) + F01 again banner → Eyes engine → – |

## 2. Voice-over (EN) with RO subtitles

Spoken by a human voice in the final edit (the rough cut has a TTS guide voice). Lines marked *(founder)* are the founder's own words, to camera; they are not read by the guide voice.

| ID | In | Out | EN voice-over (= EN caption) | RO subtitle |
|---|---|---|---|---|
| 1a | 0:00.0 | 0:03.0 | It just looked back at you. | Tocmai s-a uitat înapoi la tine. |
| 1b | 0:03.0 | 0:04.5 | All day, you talk to AI in a chat box. | Toată ziua vorbești cu un AI într-o căsuță de chat. |
| 1c | 0:04.5 | 0:07.5 | SOUL gives it a face on your desk, and the answer lands on the glass. | SOUL îi dă o față pe birou, iar răspunsul apare pe sticlă. |
| 1d | 0:07.5 | 0:10.0 | And it smiles back. | Și îți zâmbește. |
| 2a | 0:10.0 | 0:12.5 | Claude works in the Claude app. *(on screen: Claude connector: being built · scripted demo)* | Claude lucrează în aplicația Claude. |
| 2b | 0:12.5 | 0:15.5 | When it needs a yes, SOUL looks up at you. Hold to allow. *(on screen: Claude connector: being built · scripted demo)* | Când are nevoie de un „da”, SOUL se uită la tine. Ții degetul ca să aprobi. |
| 3a | 0:15.5 | 0:18.5 | (founder) I'm [name]. I build SOUL in Bucharest. | (fondatorul) Sunt [nume]. Fac SOUL în București. |
| 3b | 0:18.5 | 0:22.0 | (founder) I wanted the AI I already use to have a face I can hold. | (fondatorul) Am vrut ca AI-ul pe care îl folosesc deja să aibă o față pe care s-o țin în mână. |
| 3c | 0:22.0 | 0:25.5 | (founder) One that never watches you, and never stops working because a server went away. | (fondatorul) Una care nu te urmărește niciodată și nu se oprește pentru că a picat un server. |
| 4a | 0:25.5 | 0:28.5 | It blinks when it wants to. It follows your finger. | Clipește când vrea. Îți urmărește degetul. |
| 4b | 0:28.5 | 0:31.5 | Leave it alone, it dozes off. Shake it, it gets dizzy. | Lasă-l, ațipește. Scutură-l, amețește. |
| 5a | 0:31.5 | 0:34.0 | 120 eyes. One is yours. | 120 de ochi. Unii sunt ai tăi. |
| 5b | 0:34.0 | 0:36.5 | Born from its chip. Nobody picks them. | Născuți din cip. Nu-i alege nimeni. |
| 6a | 0:36.5 | 0:39.5 | Your own Claude, your own OpenAI key, or no AI at all. *(on screen: OpenAI key: in development · SOUL does not include AI)* | Propriul Claude, propria cheie OpenAI sau niciun AI. |
| 6b | 0:39.5 | 0:42.0 | Offline, it's still alive. | Offline, tot e viu. |
| 6c | 0:42.0 | 0:45.0 | Hold the glass to talk. Let go, and it stops listening. *(on screen: voice today: your own OpenAI key · Claude-only voice in development)* | Ții degetul pe sticlă ca să vorbești. Îl ridici și nu mai ascultă. |
| 7a | 0:45.0 | 0:48.0 | The eyes lead the whole OS. | Ochii conduc tot sistemul. |
| 7b | 0:48.0 | 0:51.0 | Notes, alarms, focus. All on the stone. | Notițe, alarme, concentrare. Toate pe piatră. |
| 8a | 0:51.0 | 0:53.5 | Machined aluminium, bead-blasted, anodised. | Aluminiu frezat, sablat, anodizat. |
| 8b | 0:53.5 | 0:56.5 | SOUL S is 63 by 71 millimetres. | SOUL S are 63 pe 71 de milimetri. |
| 8c | 0:56.5 | 0:59.0 | It sits in your palm. | Stă în palmă. |
| 8d | 0:59.0 | 1:02.0 | Three colours, one price. | Trei culori, un singur preț. |
| 8e | 1:02.0 | 1:04.5 | At night it sleeps in its egg, and charges. | Noaptea doarme în oul lui și se încarcă. |
| 9a | 1:04.5 | 1:07.0 | No camera. Its memory stays on the device. | Fără cameră. Memoria stă pe dispozitiv. |
| 10a | 1:07.0 | 1:10.0 | The first 150 are €249. Then €269. | Primii 150 costă €249. Apoi €269. |
| 10b | 1:10.0 | 1:13.0 | All or nothing, on Indiegogo. Estimated delivery May 2028. | Totul sau nimic, pe Indiegogo. Livrare estimată mai 2028. |
| 10c | 1:13.0 | 1:16.0 | Back SOUL on Indiegogo. | Susține SOUL pe Indiegogo. |

## 3. Shot list A: what we HAVE (used in the rough cut)

| ID | Source | Duration | Label (burned in) |
|---|---|---|---|
| 1a | `crowdfunding/video/build/assets/hook_object_wake.mp4` | 3.0 s | Render (CGI) |
| 1b | `generated chat-box illustration (no brand); prompt paid off by the reminder on the glass` | 1.5 s | Illustration |
| 1c | `firmware/sim/shots/alive-s/s-35-voice-answer` | 3.0 s | SoulOS simulator, S 466 |
| 1d | `crowdfunding/images/anim_1_eyes_alive.mp4` | 2.5 s | Eyes engine |
| 2a | `firmware/sim/shots/alive-s/s-12-claude` | 2.5 s | SoulOS simulator, S 466 |
| 2b | `firmware/sim/shots/alive-s/s-13-claude-ask` | 3.0 s | SoulOS simulator, S 466 |
| 3a | `title card F09` | 3.0 s | title card |
| 3b | `crowdfunding/images/story_01_object.jpg` | 3.5 s | Render (CGI) |
| 3c | `crowdfunding/images/anim_1_eyes_alive.mp4` | 3.5 s | Eyes engine |
| 4a | `eyes/soul_eye_v2.mp4` | 3.0 s | Eyes engine |
| 4b | `eyes/soul_eye_motion.mp4` | 3.0 s | Eyes engine |
| 5a | `crowdfunding/images/story_02_eyes.png` | 2.5 s | Eyes engine |
| 5b | `crowdfunding/images/anim_1_eyes_alive.mp4` | 2.5 s | Eyes engine |
| 6a | `firmware/sim/shots/alive-s/s-20-aimode` | 3.0 s | SoulOS simulator, S 466 |
| 6b | `firmware/sim/shots/alive-s/s-01-standby` | 2.5 s | SoulOS simulator, S 466 |
| 6c | `firmware/sim/shots/alive-s/s-33-voice-listen` | 3.0 s | SoulOS simulator, S 466 |
| 7a | `crowdfunding/images/anim_2_dial_turning.mp4` | 3.0 s | SoulOS web prototype |
| 7b | `firmware/sim/shots/alive-s/s-08-notes, firmware/sim/shots/alive-s/s-07-alarms` | 3.0 s | SoulOS simulator, S 466 |
| 8a | `crowdfunding/images/story_05_colours.jpg` | 2.5 s | Render (CGI) |
| 8b | `crowdfunding/images/gallery_2_size_1200x630.png` | 3.0 s | Illustration · true scale |
| 8c | `crowdfunding/images/story_06b_in_hand.jpg` | 2.5 s | Render (CGI) · eyes engine |
| 8d | `crowdfunding/images/anim_3_colour_swap.mp4` | 3.0 s | Render (CGI) |
| 8e | `crowdfunding/images/story_07_ou_night.jpg` | 2.5 s | Render (CGI) |
| 9a | `firmware/sim/shots/alive-s/s-01-standby` | 2.5 s | SoulOS simulator, S 466 |
| 10a | `crowdfunding/video/build/assets/hook_object_wake.mp4` | 3.0 s | Render (CGI) |
| 10b | `crowdfunding/images/anim_1_eyes_alive.mp4` | 3.0 s | Eyes engine |
| 10c | `end card + eyes-engine loop in the circle` | 3.0 s | – |

## 4. Shot list B: what the founder must FILM (on the real SOUL S)

Film everything on an **aluminium SOUL S running SoulOS on the S board**, after G2 (12 Feb 2027).

F03 needs the S board: the M dev board has no microphone. Anything filmed on M carries the M label for the whole shot, and M is never used for F07.

### 4.1 Set-up for every shot

**Phone**
- The best phone available, rear camera. Use the free **Blackmagic Camera** app, or the phone's Pro/Manual mode, so every setting can be locked.
- 3840 × 2160, **25 fps** (Romanian mains are 50 Hz, so lamps don't flicker).
- Shutter **1/50**. ISO as low as possible (≤ 400).
- White balance fixed at **5000–5600 K**. AE/AF lock on the glass.
- **HDR / Dolby Vision OFF** (record SDR Rec.709). Stabilisation off on the tripod. Cinematic/portrait modes off.
- Optical lenses only (1×, 2×/3×), never digital zoom.
- Airplane mode and do-not-disturb on. At least 30 GB free.

**SOUL**
- Fully charged. Brightness fixed (auto-dim off).
- Clean glass before every take (microfibre and blower).
- Wi-Fi on, except in F05.
- AMOLED: expose **0.7 stop under** so the black stays black and the eyes don't clip. If you see banding or flicker, try 1/100.

**Light**
- One big soft light at 45° to the side: a window with a sheer curtain, or a 60–90 cm softbox at 5600 K.
- A white foam board bouncing from the other side.
- A **black card behind the camera**, so the glass reflects black instead of the room.
- Overhead lights off. Move the light until its reflection is off the glass.

**Set:** a light oak desk and a plain warm-white wall. Nothing branded in frame, and no competing gadgets.

**Sound:** a lavalier mic on the founder, 48 kHz. Record 10 s of room tone per location. In F03, record SOUL's own speaker clean.

**Trust clock (every take)**
- A second phone on its lock screen, or a digital clock showing **date and time**, in frame.
- In the one-take shots (F01, F02, F03, F05, F06, F08) the clock stays in frame for the whole take. In the other shots, show it at the start.
- Slate every take: "take N, [date]", and show the clock to the lens.
- **Keep every original file untouched**, metadata included. The full F01 take goes on the page as an unlisted YouTube video, captioned "Real footage. SOUL S, aluminium, running SoulOS. One take, no edits."

### 4.2 The shots

| ID | Used at | Shot | Framing and lens | Light | Must show (proof) | Length |
|---|---|---|---|---|---|---|
| **F01** | 0:00 hook (macro) + 0:13 | **The wake, one take.**<br>1. SOUL S asleep on the desk (standby).<br>2. A finger taps the glass. The eyes open, look around, then look into the lens.<br>3. The finger slides left and right; the eyes follow.<br>4. The hand leaves. After a few seconds the eyes get sleepy and doze.<br>Second take: a macro of the eyes opening. | 3/4 front, lens at glass height, 2×, tripod. Macro: straight on, 2× at ~30 cm | key 45° left, bounce right, black card, −0.7 EV | dated clock in the background for the whole take; ≥ 25 s continuous | 25 s take; 6 s + 4 s used |
| **F02** | 0:36 | **Birth at first power-on.**<br>Three new S units switched on for the first time, one after another, uncut.<br>Each shows its chip ID, then its eyes, then My SOUL (name, rarity, chip ID). | top-down, phone parallel to the glass, 1× at 25–30 cm | even, soft, −0.7 EV | dated clock beside the units; no takes picked for rarity | 40 s take, 3.5 s used |
| **F03** | 0:58 | **Hold the glass, ask your own AI.**<br>1. A finger on the glass: the listening ring appears.<br>2. A real question ("Remind me to call Mum at six").<br>3. Lift the finger: the answer appears and is spoken, and the reminder is created.<br>Insert: Settings → Your AI, keys **hidden**. | medium close-up 3/4, hand and SOUL sharp, face soft; 2× | key 45°, −0.7 EV | dated clock; question and answer in one take; never show a key. If Claude-only voice is not ready, show the speech-to-text key line in Settings and keep the on-screen note | 20 s take, 6.5 s used |
| **F04** | 0:52.5 | **The Claude app puts a plan on SOUL.**<br>In the Claude app (his own account) he types "Put tomorrow's plan on my SOUL." SOUL, next to the laptop, reacts and the plan appears. | wide: laptop and SOUL (1×), then a glass close-up (2×) | laptop brightness down; blur personal data | dated clock (the laptop clock is fine if readable); no logo close-ups | 2 takes, 5.5 s used |
| **F05** | 1:04.5 | **Offline: still alive.**<br>Switch the router off (lights go out) or Wi-Fi off on SOUL. SOUL keeps blinking. Set an alarm, write a note. Settings shows "no AI". | wide with the router (1×), then a glass close-up | room light | clock and router lights in the same frame | 20 s take, 4.5 s used |
| **F06** | 1:09 | **SoulOS on the real S glass.**<br>A thumb turns the dial of pebbles, opens Notes, scrolls a wheel list and closes it. The lids open and close; the eyes come back. | macro straight on, overhead arm, 2× at ~30 cm, focus locked | −0.7 EV, 1/50 (check for flicker) | one continuous take; clock at the frame edge | 30 s take, 7.5 s used; also the source for real S screen recordings |
| **F07** | 1:34 | **In the hand: the real size.**<br>1. An open palm, SOUL S resting in it, a slow turn to show the 63 × 71 × 23–26 mm body.<br>2. On the table next to a bank card and a €2 coin, calipers reading 63 mm. | eye level, 1×, neutral background, an average adult hand | soft side light (bead-blast texture) | **S only, never M**; calipers in take 2 | 2 takes, 4.5 s used |
| **F08** | 1:51.6 | **Privacy in one gesture.**<br>A finger rests on the glass: the ring appears. The finger lifts: the ring goes off and the eyes relax. SOUL is turned around slowly: no camera anywhere. | macro 3/4, focus on the glass edge, dark background, 2× | low-key, one light | one take, dated clock | 15 s take, 4 s used |
| **F09** | 2:01 | **The founder, to camera.**<br>At the bench in Bucharest he says line 9a in his own words (≤ 10 s). On the bench: M and S side by side, with cards "M prototype" / "S". While M is in frame, the M label is on screen. | eye level, 1×, chest-up, SOUL S in focus | soft key 45°, bounce, lavalier | a real person in a real place; no actors, no stock footage | 5–6 takes, best 8 s |
| **F10** | teaser 0:14.5 (replaces the hand render) | **Vertical: SOUL wakes in the hand.**<br>SOUL S in the palm; a thumb touches the glass; the eyes open and look at the lens. | 9:16, 1× | window light | S only; keep the longer take with a clock | 3.5 s used |

**Extra B-roll** (2-day shoot, from the marketing budget in `PLAN.md`):
- CNC and anodising at the partner, only with their written OK to be shown.
- The launch colours on the bench.
- OU charging, showing the gold contacts.
- Packaging.
- An unboxing by the founder.

## 5. Music

**Licensed track:** "Sci-Fi Score" by Arulo, under the **Mixkit Stock Music Free License**. It allows commercial use, including ads and YouTube, with no attribution. The file itself may not be redistributed, so the build downloads it (`https://assets.mixkit.co/music/464/464.mp3`) and it is never committed. Details: `trailer/MUSIC-LICENSE.md`.

**Where it is used now:**
- In the rough cut, only under the ask (from 1:07.0), starting at the track's 58.71 s drop.
- In the teaser, from 0:00, starting at the phrase downbeat at 16.68 s, with a 1.5 s fade out.

**The body of the final film (0:03–1:07.0) needs a new, calmer track:**
- Warm electronic or ambient, with piano or plucks, 80–95 BPM, no vocals.
- From Mixkit (same licence) or a paid library on the founder's own subscription (Artlist, Epidemic Sound, Musicbed).
- **Before upload:** record the track, author, licence and download date in a new `video/MUSIC-LICENSE.md`. Check that the track is not registered with Content ID, or whitelist the channel in the library's dashboard.

**Cue sheet:**

| Time | Cue |
|---|---|
| 0:00–0:03 | no music: room tone and the real sound of the finger on the glass |
| 0:03 | the body track fades in low |
| 0:16 | a low bed under the founder |
| 0:40 | the track lifts for "your own AI" |
| 1:07.0 | crossfade into "Sci-Fi Score" from 58.71 s; hit on the end card at 1:13.0; ring out by 1:16.0 |

**Mix:** voice at −14 LUFS integrated, true peak −1 dBTP, music ducked 8–10 dB under the voice. Sound effects only from licensed packs or our own recordings.

## 6. Captions and on-screen text

- **YouTube master:** do **not** burn the voice-over in. Upload the EN and RO `.srt` files as closed captions, retimed to the final edit.
- **Burned into the master, only:**
  - the honesty labels: top-left, Martian Mono, ≥ 22 px at 1080p, on screen for the whole shot;
  - the on-screen facts: the Claude-connector note (2a/2b), the OpenAI-key note (6a), the voice note (6c), the dimensions (8b);
  - disclaimer pills and captions sit in a band outside the round screen: the circle is never covered (review 2026-10-22);
  - the end card.
- **Social versions:** captions burned in, Bricolage Grotesque Medium, inside the 9:16 safe area (top 14 % and bottom 20 % kept clear).
- **Brand:** Bricolage Grotesque (lowercase headlines) and Martian Mono (labels). Colours: Glass `#0B0B0C`, Warm White `#F6F3EC`, Ember `#D2622C`.

## 7. Final delivery specs

- **Master:** 3840 × 2160 or 1920 × 1080, 25 fps, ProRes 422 HQ or H.264 High.
- **YouTube upload:** H.264 at 20–40 Mbps. Audio AAC 48 kHz stereo 320 kbps, −14 LUFS.
- **Indiegogo:** the gallery and story video is a YouTube or Vimeo link, with embedding allowed.
- **Versions:**
  - the 76 s main film (75–90 s target);
  - the unlisted full F01 one-take (proof);
  - the 30 s vertical teaser;
  - three 15 s cut-downs (birth, hold-to-talk, privacy) for ads after G2.

## 8. Before anything is published (checklist)

- [ ] G2 passed: F01–F09 filmed on an aluminium SOUL S running SoulOS on the S board.
- [ ] No M footage without the M label. No v9 hand/desk/typing render. No trailer hand range.
- [ ] Every render, eyes-engine, SoulOS and illustration shot carries its label for its whole length.
- [ ] No CE card in the film; the end card has no "not CE-certified" line. No battery-life claim. No backers, press, reviews or awards.
- [ ] OpenAI appears only as "your own OpenAI API key, in development"; never "ChatGPT account". The voice note is on screen while `claude_only_voice_works` is false. No AI logos. The trademark line is in the description.
- [ ] Founder's name and lines 3a–3c filled in (`campaign/06-team.txt`), filmed as F09 at 0:15. Age rule (D4) in the description.
- [ ] The end card's reward line matches the published rewards (ladder from `facts.json`).
- [ ] Body music licence filed in `video/MUSIC-LICENSE.md`. Human voice recorded (not the guide TTS).
- [ ] The raw F01 one-take file kept and uploaded unlisted.

## 9. Open items

- **Founder:**
  - name and lines 3a–3c (F09, the founder to camera, at 0:15);
  - film F01–F11 after G2 (F11 = macro of the finish, for the price);
  - choose a human voice;
  - choose the body music track and file its licence;
  - review the teaser before it is posted.
- **Renders:** swap in `soul_v10_ou_night.png` (8e) when it is rendered, with the flat eyes. `soul_v10_vs_m.png` is not needed in the film.
- **Trailer before campaign use:**
  - cut the M-scale hand at 19.2–22.2 s;
  - change "Join the waitlist" to "Back SOUL on Indiegogo";
  - re-word "Always on".
- **Rebuild** after any change to `facts.json` (S depth, ladder, colours, delivery, CE gate): `python3 -I micul-smecher/crowdfunding/video/build/build.py`. The cards, captions and SRTs update; re-check the chapter times in `youtube-upload.md` if durations change.
