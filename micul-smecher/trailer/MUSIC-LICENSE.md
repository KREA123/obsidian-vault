# Trailer music licence

**Track:** "Sci-Fi Score"
**Author:** Arulo
**Source page:** https://mixkit.co/free-stock-music/tag/technology/ (track listing; the audio file is https://assets.mixkit.co/music/464/464.mp3)
**Licence:** Mixkit Stock Music Free License (https://mixkit.co/license/). It allows use in commercial projects (ads, social media, YouTube) and personal projects, with no attribution required. You can't resell or redistribute the track as a standalone file. Mixkit says its free music doesn't trigger YouTube Content ID claims.
**Downloaded:** 2026-10-01

**How it is used:** `audio.py` downloads the mp3 at build time. It is not committed, because the licence doesn't allow redistributing it as a standalone file. The track is edited into a 49 s bed:
- 0–41.5 s: track from 0.5 s (quiet intro; the drums enter on the 13.5 s cut)
- 41.5–42.0 s: half-second stop-down
- 42.0–46.5 s: track from 44.70 s (a phrase downbeat), so the drop lands on the logo reveal
- 46.5 s: cut on the final hit

On top of the track sits an original trailer layer synthesized in `audio.py`: braams, impacts, sub drops, risers, reversed cymbals and tom accents on the cuts.

**Why not Pixabay:** pixabay.com sits behind a bot check (HTTP 403) from this environment, so I couldn't get any track's audio URL. Several Pixabay trailer tracks are also registered with performing-rights organisations, which risks Content ID claims.

**Voice-over:** Kokoro-82M (hexgrad/Kokoro-82M, Apache-2.0), voice `am_michael`, speed 0.9.
