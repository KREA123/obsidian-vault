# Trailer music licence

**Track:** "Electro Dreams"
**Author:** Arulo
**Source:** Mixkit, House genre listing https://mixkit.co/free-stock-music/house/ (the audio file is https://assets.mixkit.co/music/190/190.mp3; the listing's metadata names the licence as `https://mixkit.co/license/#musicFree`)
**Licence:** Mixkit Stock Music Free License, https://mixkit.co/license/#musicFree (text checked on 2026-10-02 from https://mixkit.co/license/modal/musicFree/):
- Allowed: commercial and non-commercial projects, for free. "Online marketing ads", "Social Media video posts", "YouTube videos", podcasts. You may "download, copy, modify, distribute and publicly perform the Music Items on any web or social media platform, including internet-based video on demand services, podcasts and advertisements". No attribution required.
- Not allowed: CDs and DVDs, **TV and radio broadcasts**, video games. You also may not remix the track into a music-only work, claim it as your own, or register it with any rights-management service (Content ID and similar).
- If a platform raises a claim, forward the details to team@mixkit.co.

**Downloaded:** 2026-10-02

**What this means for Expedo:** the Shopify App Store listing video, the website, YouTube, Instagram/TikTok/Facebook posts and paid social ads are all covered. **TV or radio use is not**: license a different track for that.

**How it is used:** `audio.py` downloads the mp3 at build time into a scratch folder. It is not committed, because the licence does not allow redistributing it as a standalone file. The track is 120 BPM (1 beat = 0.5 s, beat grid at 0.047 s + 0.5 k) and is edited to picture on its own grid:
- video 0–40 s ← track 8–48 s: the filtered intro build sits under the "pain" scene; the drop lands on the Expedo logo at 8 s
- video 40–44 s ← track 60–64 s: the last two bars of the breakdown, under the "safety" scene
- video 44–50 s ← track 64–70 s: the second drop on tracking and cash on delivery
- video 50–56 s ← track 108–114 s: the track's own last two bars under the end card; the music stops by itself on the downbeat at 54 s, with its natural tail

The bed sits about 3.5 dB under the voice and ducks a further ~7 dB while the voice speaks; the mix is normalized to -14 LUFS with the true peak of the encoded AAC kept at or under -2 dBTP.

An original trailer layer synthesized in `audio.py` sits on top: braams, impacts, sub drops, risers, reversed cymbals, glitches, packing-tape rips, and UI sounds (clicks, key taps, pops, ticks, chimes, whooshes).

**Voice-over:** Microsoft neural TTS through edge-tts: RO `ro-RO-EmilNeural`, EN `en-US-AndrewMultilingualNeural`. Before you run paid media, check that Microsoft's terms for neural TTS output cover commercial advertising. Recording a human or licensed AI voice to `voiceover_script.md` avoids the question; see the `VOICE_FILE_RO` / `VOICE_FILE_EN` hook in `audio.py`.
