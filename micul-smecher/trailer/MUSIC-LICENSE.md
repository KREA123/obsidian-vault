# Trailer music licence

**Track:** "Sci-Fi Score"
**Author:** Arulo
**Source page:** https://mixkit.co/free-stock-music/tag/technology/ (track listing; the audio file is https://assets.mixkit.co/music/464/464.mp3)
**Licence:** Mixkit Stock Music Free License (https://mixkit.co/license/). It allows use in commercial projects (ads, social media, YouTube) and personal projects, with no attribution required. You can't resell or redistribute the track as a standalone file. Mixkit says its free music doesn't trigger YouTube Content ID claims.
**Downloaded:** 2026-10-01

**How it is used (v3):** `audio.py` downloads the mp3 at build time. It is not committed, because the licence doesn't allow redistributing it as a standalone file. The track is edited on its own beat grid (~137 BPM, a 16-beat phrase = 7.004 s), and the video cuts are time-warped onto that grid:
- 0 s to beat 91: the track from a phrase downbeat at 16.68 s, so the drive is there from frame 0
- one beat of stop-down, then the drop at beat 92 (logo reveal): the track from 58.71 s (another phrase downbeat)
- beat 102: cut on the end-card hit

On top of the track sits an original trailer layer synthesized in `audio.py`: braams, impacts, sub drops, risers, reversed cymbals and tom accents on the cuts.

**Why not Pixabay:** pixabay.com sits behind a bot check (HTTP 403) from this environment, so I couldn't get any track's audio URL. Several Pixabay trailer tracks are also registered with performing-rights organisations, which risks Content ID claims.

**Voice-over (v3):** Microsoft neural TTS `en-US-AvaMultilingualNeural`, generated through edge-tts (rate +10%, pitch +10 Hz). A recorded voice can replace it with `VOICE_FILE=… python3 audio.py`; see `voiceover_script.md`. Check that Microsoft's terms for neural TTS output cover commercial ad use before running paid media; recording a human or ElevenLabs voice to the script avoids the question.
