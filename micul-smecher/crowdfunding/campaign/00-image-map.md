# Image and video map (v3, after the review of 2026-10-22)

**One system:** every `{{img:…}}` / `{{video:…}}` in the copy is exactly one file in `../images/` (or a YouTube link), listed below with the caption that **must** sit under it on the page. `tools/build_copy.py` reads this table to write the `[IMAGE: file]` slots in `story-paste.html`. The images carry **no paragraphs, tables or bullets**: those are in the text (Indiegogo's text and table blocks), so nothing appears twice and nothing is unreadable on a phone. Text that stays inside an image is at least 44 px on a 1200 px canvas (≈ 13 px on a 375 px phone); render labels are a small corner pill (≥ 22 px on 700 px images) or live in the caption under the image.

Captions (copy them exactly; they come from `facts.json → labels`):
- **R** = "Render (CGI), not a photo."
- **RE** = "Render (CGI), not a photo. Eyes drawn by the SOUL eyes engine." (v10 renders whose old glowing eyes were painted over with the flat SoulOS eyes)
- **P** = "Prototype shown at a larger size (M). The product you back is S: 63 × 71 mm with a 1.75″ AMOLED."
- **OS-S** = "SoulOS simulator capture at the S screen size (466 × 466). Not a recording of a real device."
- **OS-W** = "SoulOS web prototype capture, 480 × 480; on S it runs on a 466 × 466 AMOLED."
- **E** = "The SOUL eyes engine, recorded from the same code that runs on the device. Screen animation, not a photo."
- **G** = "Illustration."
- "SoulOS (shown on the prototype)." is used **only** for real recordings of a real board. Firmware 1.9.1 hasn't run on one yet, so no image in this kit uses it.

## Story (each placeholder = one file)

| Placeholder | File | Caption | What it is |
|---|---|---|---|
| `{{video:main}}` | YouTube link of the G2 one-take video | "Real footage. SOUL S, aluminium, running SoulOS. One take, no edits." (only if exactly true) | does not exist yet; **never launch without it** (DECIZII-FONDATOR.md F1) |
| `{{img:eyes-alive}}` | `anim_1_eyes_alive.mp4` | E | the hero loop right under the video: the eyes look around, follow, blink, smile. 1200 × 900 |
| `{{img:object}}` | `story_01_object.jpg` | R | SOUL S, Silver, eyes open, on black. No text |
| `{{img:approve}}` | `story_03b_approve.png` | OS-S + "The request is a scripted demo." | the hero use case: "Claude asks" on the S screen, big, with a one-line caption outside the circle |
| `{{img:eyes-grid}}` | `story_02_eyes.png` | "The SOUL eyes engine, drawn from the same code that runs on the device. Screen images, not photos." | 24 eye pairs, no names (the odds table is text) |
| `{{img:ai-modes}}` | `story_03_your_ai.png` | G | three faces, three big labels: your Claude · your OpenAI key (in development) · offline |
| `{{img:soulos-dial}}` | `anim_2_dial_turning.mp4` | OS-W | the home dial turning, captured from the SoulOS web prototype. 1200 × 900 |
| `{{img:soulos-screens}}` | `story_04_soulos.png` | OS-S + "Answers on these screens are a scripted demo, not a live AI." | two S screens at 2× size, a one-line caption outside each circle |
| `{{img:colours}}` | `story_05_colours.jpg` | R | the launch colours, names in big type |
| `{{img:colour-swap}}` | `anim_3_colour_swap.mp4` | R | the launch colours, one after another. 1200 × 900 |
| `{{img:size}}` | `story_06_size.png` | "Illustration. True scale: SOUL S next to a bank card (85.6 × 54 mm) and a €2 coin, with its 52 mm glass and the round screen inside it. The dashed outline is our larger M prototype." | vector, true scale from `facts.json → size_graphics` + `size_S.glass_mm` + `screen.active_area_mm` |
| `{{img:in-hand}}` | `story_06b_in_hand.jpg` | RE + " Size S, in an adult hand." | `renders/v10/soul_v10_hand.png`, eyes repainted (warm, looking up). The CGI hand looks synthetic: replace with a real hand holding an S-size model (F3) |
| `{{img:on-desk}}` | `story_06c_on_desk.jpg` | RE + " Size S, next to a phone." | `renders/v10/soul_v10_desk.png`, eyes repainted |
| `{{img:prototype-m}}` | founder's real photo of the M prototype (`prototype-m.jpg`) | **P** | only if such a photo exists; otherwise delete the placeholder (F2) |
| `{{img:ou-night}}` | `story_07_ou_night.jpg` | R | object in the egg, scale-neutral |
| `{{img:in-the-box}}` | `story_08_box.jpg` | "Render (CGI), not a photo (SOUL and OU). Cable and guide are drawings." | four tiles, one big word each |
| `{{img:privacy}}` | `story_09_privacy.png` | G | six faces, two or three big words each; the promise wording is in the text |
| `{{img:budget}}` | `story_10_budget.png` | "Illustration. The same numbers as the table below." | **draft until D2** (VAT); bars with € amounts, generated from `tools/goal_model.py` |
| `{{img:timeline}}` | `story_11_timeline.png` | G | a track from launch to delivery (batch 1 and batch 2); before-launch items show ✓ only when `facts.json → gates` says passed |
| `{{img:stretch-goals}}` | `story_12_stretch.png` | G | three amounts, big |
| `{{img:team}}` | founder's real photo (`team.jpg`) | – | [de completat]; `story_13_team_PLACEHOLDER.png` is a layout guide, never published (F4) |

## Emails

| Placeholder | File | Caption | What it is |
|---|---|---|---|
| `{{img:launch-700}}` | `05_launch_email_700x700.jpg` | "Render (CGI)" is on the image | the launch email image |

## Page-level images (General setup, HC/485)

| Use | File | Notes |
|---|---|---|
| Thumbnail / card | `01_card_thumbnail_700x700.jpg` | the hero use case: SOUL S on a desk at an angle, eyes looking out, next to a phone for scale, one line "it looks up when your AI needs you"; small corner pill "Render (CGI)" |
| Cover | `02_cover_1743x498.jpg` | no text (Indiegogo darkens it); eyes engine discs only, so no render label needed |
| Social share | `03_social_share_1200x630.jpg` | headline + object; label pill |
| Avatar | `04_avatar_700x700.png` | the SOUL symbol |
| Launch email / update header | `05_launch_email_700x700.jpg`, `06_update_header_700x700.jpg` | |

## Gallery (top of the page, in this order)

1. the real one-take video (YouTube link, G2). Until it exists, the founder's labelled footage of the M prototype (caption **P**) is the only acceptable stand-in on a pre-launch page; the campaign never launches without G2.
2. `gallery_1_approve_1200x630.png` (OS-S): the hero use case, "it looks up when your AI needs you"
3. `gallery_2_size_1200x630.png`: true scale, S next to a card and a coin, glass and screen drawn to scale
4. `gallery_3_hero_1200x630.jpg` (R)
5. `gallery_4_eyes_1200x630.png` (E)
6. `gallery_5_colours_1200x630.jpg` (R)
7. `gallery_6_in_hand_1200x630.jpg` (RE + " Size S.")

## Rewards (700 × 700, HC/478)

| Reward | File |
|---|---|
| Soul Supporter | `reward_1_soul_supporter_700x700.png` |
| First Light | `reward_2_first_light_700x700.jpg` |
| Campaign Price (batch 1) | `reward_3_campaign_price_700x700.jpg` |
| Campaign Price · batch 2 | `reward_3b_campaign_batch2_700x700.jpg` |
| Two Souls | `reward_4_two_souls_700x700.jpg` |
| Add-on: extra OU | `reward_5_addon_extra_ou_700x700.jpg` |
| Late Pledge (after the campaign) | `reward_6_late_pledge_700x700.jpg` |

The badge on device rewards reads "planned retail €… after the campaign", "campaign price" or the batch: **never** a percentage, "off" or a struck-through price. "Render (CGI), not a photo." is the last line of each description (in `perks.csv`).

## Stretch goals (700 × 700)
`stretch_1_languages_700x700.png`, `stretch_2_felt_pouch_700x700.png`, `stretch_3_birth_card_700x700.png` (amounts from the goal model). US/Canada is not a stretch goal (D14).

## Animations for email only
`anim_*.gif`: smaller GIF versions for the email platform. On Indiegogo always use the MP4.

## Finishes and eyes
Stills, GIFs and the video use the same graded finishes (`images/src/regrade.py` → `images/src/cuts/`): Silver = cool light grey with a fine bead-blast grain, Graphite = cool dark grey, Ember = warm orange (and, outside this campaign, Midnight = deep blue, Champagne = clearly warmer gold). The front cut-outs are scale-neutral (S is the same shape at a smaller size). **One eye style across the campaign: the flat SoulOS eyes from the eyes engine.** The v10 hand and desk renders are used only with their old glowing eyes painted over and the engine's flat eyes drawn on the glass (`templates.js → v10eyes`), captioned **RE**. `soul_v10_hero.png` is not used.

## Banned on this campaign

- `renders/v9/soul_v9_hand.png`, `renders/v9/soul_v9_desk.png`, `soul_v9_typing.png`, the hand and desk shots in `renders/v9/film/soul_launch*.mp4`, any older hand/desk render: wrong size.
- The old soft glowing-pill eyes (`eyes/soul_eye_v1.mp4`, the v9 launch film, the trailer's peach-gradient scenes, the unedited v10 renders): one eye style across the campaign.
- Any M photo or video without caption **P**. Any simulator or web capture captioned as if it ran on a device.
- Any Claude, Anthropic, ChatGPT or OpenAI logo.
- Screens that show a feature the story doesn't promise.
