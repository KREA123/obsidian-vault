# SOUL trailer v4: voice-over script

Timeline: `soul_trailer.mp4` / `soul_trailer_vertical.mp4`, 47.28 s, music at ~137 BPM (one beat = 0.438 s).
Each line starts on a beat, right on its cut, one short line per scene, in the style of the reference ad.
The current mix uses the Microsoft neural voice `en-US-AvaMultilingualNeural` (edge-tts, rate +10%, pitch +10Hz).
To replace it with a real voice (ElevenLabs or a human), record these lines to these timecodes. **End** is the
latest each line may run (the next line or cut); "TTS length" is how long the current synthetic read takes.

| # | Start | End (max) | TTS length | Line | On screen |
|---|---|---|---|---|---|
| 1 | 00:00.88 | 00:02.63 | 0.67 s | Meet Soul. | hero rises in front of the SOUL wordmark, the eyes open |
| 2 | 00:02.63 | 00:05.25 | 1.61 s | A little device, with a soul. | tagline, hero glides right |
| 3 | 00:05.25 | 00:07.44 | 1.42 s | Every day, you talk to AI. | headline |
| 4 | 00:07.44 | 00:08.75 | 0.94 s | In a chat box. | typed into a chat box that then shrinks away |
| 5 | 00:08.75 | 00:10.51 | 1.18 s | AI has a brain. |  |
| 6 | 00:10.51 | 00:12.69 | 1.08 s | Now, it has a soul. | 'soul' turns amber on the hit |
| 7 | 00:12.69 | 00:15.76 | 1.10 s | It lives on your desk. | 3/4 SOUL on the desk, eyes look around |
| 8 | 00:15.76 | 00:17.73 | 1.89 s | Always on. Never in the way. | hero with a soft halo, words left and right |
| 9 | 00:17.73 | 00:19.26 | 0.76 s | It looks back. | push-in on the glass, the eyes look at the camera |
| 10 | 00:19.26 | 00:22.19 | 2.02 s | Hold the glass. It listens. | touch on the glass, ripples, listening ring |
| 11 | 00:22.19 | 00:22.89 | 0.48 s | Type. | keyboard UI in the glass |
| 12 | 00:22.89 | 00:23.55 | 0.48 s | Talk. | talk UI |
| 13 | 00:23.55 | 00:24.51 | 0.60 s | Remember. | reminders UI |
| 14 | 00:24.51 | 00:26.26 | 0.86 s | Claude asks. | Claude approval card + the Claude screen in the glass |
| 15 | 00:26.26 | 00:28.02 | 0.76 s | You approve. | Approve tapped, the face goes happy |
| 16 | 00:28.02 | 00:29.90 | 1.84 s | Works with the AI you already have. |  |
| 17 | 00:29.90 | 00:32.39 | 2.38 s | Claude. ChatGPT. Your key. | pills pop on each word, then No AI |
| 18 | 00:32.39 | 00:35.02 | 1.80 s | Five colours. One soul. | the five colours fly in and line up |
| 19 | 00:35.02 | 00:40.49 | 1.37 s | It sleeps in its egg. | the egg at night, the eyes close |
| 20 | 00:40.49 | 00:43.34 | 2.72 s | Soul. From two hundred forty-nine euros. | wordmark on the drop, then From €249 |
| 21 | 00:43.34 | 00:44.91 | 1.07 s | Join the waitlist. | waitlist button, pressed |
| 22 | 00:44.91 | 00:46.68 | 1.20 s | Designed in Romania. | stacked logo end card |

**How to drop a recorded voice in:** export one WAV/MP3 of the whole voice track, starting at 00:00.00 and
timed to the video. Then run `VOICE_FILE=/path/voice.wav python3 audio.py`. That replaces the TTS: a gentle
low cut and compression, the music ducks about 7 dB under the voice, -14 LUFS, and both mp4s are re-muxed.
