# SOUL: YouTube upload sheet

**Version 3 · 2026-10-22 (after the review) · scenario `after_ce`, launch Tue 5 Oct 2027.** Indiegogo takes its gallery and story video only as a **YouTube or Vimeo link** (HC/503), so the campaign video lives on YouTube.

**The founder uploads it himself, signed in to his own channel.** Nobody else handles the channel password or 2-step codes.

| Video | File | When | Visibility |
|---|---|---|---|
| Campaign video (~76 s) | the **final** edit after G2 (real SOUL S footage) and after the CE gate, so line 10a says the tests passed.<br>**Never `rough-cut.mp4`**: it is an internal animatic stamped "not for publishing", with a TTS guide voice. | before submitting for review (by 21 Sep 2027); paste the link into the Indiegogo draft | **Unlisted** until launch, then **Public** on Tue 5 Oct 2027, 09:00 Europe/Bucharest |
| One-take proof (F01, full length) | the untouched F01 file | with the campaign video | **Unlisted**, linked from the story |
| Teaser (0:30, vertical) | `teaser-vertical.mp4` (1080 × 1920, 30.0 s, 1.8 MB, licensed music, captions burned in) | pre-launch list building, after the founder checks it | Public, as a **Short** |

---

## 1. Campaign video

**Title** (≤ 100 characters):
1. `SOUL: Living Eyes for Your Own AI | It Looks Up When Your AI Needs You` (72 characters), **recommended**: the campaign name plus the hero use case.
2. `SOUL: your AI has a brain. Give it a soul.` (41 characters)
3. `SOUL: a palm-sized aluminium stone with living eyes (and your own AI)` (69 characters)

Never put "Claude", "ChatGPT" or "AI-powered" in the title: it would read as if AI were included.

**Description** (fill in the [brackets]; keep the disclosure block; check the CE line against `facts.json` → `gates.CE` on upload day):

```
SOUL is a palm-sized aluminium stone with two living eyes. It blinks, follows your finger and dozes off when it's left alone. It looks up when your AI needs you: Claude asks on the glass, you hold to approve (the Claude connector is being built). It works with your own Claude or your own OpenAI API key (in development), or no AI at all.

Back SOUL on Indiegogo: [Indiegogo campaign link]
Real footage, one take, no edits: [unlisted F01 link]

• Born with one of 120 pairs of eyes, picked by its own chip. Nobody chooses them. The real odds are published on the campaign page, and rarity changes only the eyes.
• Your own AI: your Anthropic API key and the Claude app connector, your own OpenAI key (in development; "Sign in with ChatGPT" is pending OpenAI's approval), or offline.
• No camera. It listens only while your finger is on the glass. SOUL Memory stays on the device. No subscription to us.
• SOUL S: 63 × 71 mm, 23–26 mm deep (being finalised), round 1.75" AMOLED 466 × 466, bead-blasted anodised aluminium in Silver, Graphite and Ember. Charges in its egg, OU.

Chapters
0:00 It looks up when your AI needs you
0:15 Why I built it
0:25 Alive, born with its eyes
0:36 Your own AI, or none
0:51 The object
1:04 Promises, and the ask

Before you back
The batch is made after the campaign. It passed its CE tests at [lab] and the EU Declaration of Conformity is signed ([date]) (the campaign only opens after that; never upload this video before the DoC). Estimated delivery: May 2028 (EU) for batch 1, August 2028 for batch 2. Shots marked "Render (CGI)", "Eyes engine", "SoulOS simulator capture" or "Illustration" are not photos of a finished unit. [If any shot shows the M prototype: Prototype shown at a larger size (M). The product you back is S: 63 × 71 mm with a 1.75" AMOLED.] Read "Risks and challenges" on the campaign page.

SOUL does not include AI. It works with your own Claude (API key, or the Claude app connector) or your own OpenAI API key (in development), or offline. Claude is a trademark of Anthropic; ChatGPT and OpenAI are trademarks of OpenAI. SOUL is independent and not affiliated with or endorsed by either.

Music: [body track] by [author], [licence]. "Sci-Fi Score" by Arulo (Mixkit Stock Music Free License).

Made by ARTEMIS DIGITAL S.R.L., Bucharest, Romania. Designed in Romania.
```

**Chapters.** The times match the rough cut (`build/timeline_rough.json`); re-check them against the final edit. YouTube needs the first chapter at 0:00 and every chapter ≥ 10 s, so the short sections are merged.

**Delivery dates.** They follow `facts.json` (D9 applied as the safe default: May 2028 EU, August 2028 batch 2). If the founder changes D9, change them here and in the pinned comment.

**Tags:** SOUL, SOUL companion, AI companion, desk companion, living eyes, bring your own AI, Claude, OpenAI API, offline AI gadget, privacy, no camera, aluminium gadget, AMOLED, ESP32, design object, Indiegogo, crowdfunding, designed in Romania, ARTEMIS DIGITAL
- "Claude" and "OpenAI" appear only as tags, because people search for them. They never go in the title.

**Thumbnail:** `youtube-thumbnail-1280x720.jpg` (1280 × 720, 73 KB, under the 2 MB limit).
- Made from `crowdfunding/images/gallery_3_hero_1200x630.jpg`: scaled to 1280 × 672, with 24 px of glass black above and below.
- It keeps its "RENDER (CGI)" label.
- After G2, a frame of the real SOUL S from F01 makes a stronger thumbnail. If that frame shows M, it needs the M label.
- Custom thumbnails need a phone-verified channel (YouTube Studio → Settings → Channel → Feature eligibility).

**Captions:** upload `subtitles/soul-campaign-roughcut.en.srt` as **English** and `.ro.srt` as **Romanian**, both retimed to the final edit first. Remove the stage note "(founder)" from both files. Set the video language to English.

**Settings in YouTube Studio:**

| Setting | Value | Why |
|---|---|---|
| Audience | **No, it's not made for kids** | the page says 18+ (the safe default until D4) and it is not a toy |
| Altered or synthetic content | **Yes** | realistic CGI renders of a product that is not finished |
| Paid promotion | No | our own video about our own product |
| Category | Science & Technology | |
| Video language | English | |
| Licence | Standard YouTube Licence | |
| Allow embedding | **On** | Indiegogo embeds the video |
| Publish to subscriptions feed | Off while Unlisted; on at launch | |
| Comments | On, "Hold potentially inappropriate comments for review" | answer with facts from `campaign/05-faq.md` |
| Shorts remixing | Don't allow | keeps the labels attached to the shots |
| Recording date / location | the G2 shoot date; Bucharest, Romania | |
| End screen | the teaser or the one-take proof, plus subscribe | external links in end screens need the YouTube Partner Programme; the Indiegogo link goes in the description and a pinned comment |
| Pinned comment | "Back SOUL on Indiegogo: [link]. Estimated delivery May 2028 (EU, batch 1). Everything that isn't real footage is labelled." | |

**After the upload:**
- Paste the link (`https://youtu.be/…`) into the Indiegogo draft in two places: Basics → video, and the top block of the Story.
- Check that it plays inside the Indiegogo preview, with captions.

## 2. Teaser (Short)

**File:** `teaser-vertical.mp4` (1080 × 1920, 0:30).
- Every shot is labelled: renders, eyes engine and SoulOS simulator captures.
- The 0:14.5–0:18.0 hand shot is the S-scale v10 render with the eyes repainted by the eyes engine, labelled as a render. Swap in the real F10 after G2.
- **Music:** "Sci-Fi Score" by Arulo, Mixkit Stock Music Free License. It allows social media and YouTube use with no attribution. Mixkit states its free music does not trigger Content ID.
- When uploading, do not add another track on top. On Instagram or TikTok, you can mute it and use the platform's **commercial** library (business accounts) instead.

**Title:** `It looks up when your AI needs you. SOUL #shorts`

**Description:**
```
A palm-sized aluminium desk companion with living eyes that looks up when your AI needs you. Or keep it offline. Coming to Indiegogo: [waitlist / Indiegogo "Upcoming" link]

Renders (CGI), eyes-engine animation and SoulOS simulator captures, labelled on screen. Not real footage. SOUL is not CE-certified yet. SOUL does not include AI; it works with your own Claude or your own OpenAI API key (in development), or offline. The Claude connector is being built. Claude is a trademark of Anthropic; ChatGPT and OpenAI are trademarks of OpenAI; SOUL is not affiliated with either. Music: "Sci-Fi Score" by Arulo (Mixkit). ARTEMIS DIGITAL S.R.L., Bucharest, Romania.
```

**Settings:** same as above (not made for kids; altered/synthetic content: Yes).

**Pinned comment:** the waitlist link. The end card says "get told first: link in the description".
