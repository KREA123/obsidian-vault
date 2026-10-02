# Expedo trailer: voice-over script (EN + RO)

Timeline: `expedo_trailer_en.mp4` / `expedo_trailer_en_vertical.mp4` (English, primary) and `expedo_trailer_ro.mp4` / `expedo_trailer_ro_vertical.mp4` (Romanian), 56 s, music at 120 BPM (one beat = 0.5 s). Each line starts on a beat, right on its cut: one short line per scene.
Voices: Microsoft neural TTS through edge-tts. EN `en-US-AndrewMultilingualNeural` (rate +6%), RO `ro-RO-EmilNeural` (rate +6%, pitch +2Hz).
To replace a voice with a recorded one (ElevenLabs or a human), record these lines to these timecodes: **Start** is the beat
the line starts on, **End (max)** the latest it may run (the next line or cut), "TTS length" what the current synthetic read takes.

## English (primary)

| # | Start | End (max) | TTS length | Line | On screen |
|---|---|---|---|---|---|
| 1 | 00:00.50 | 00:04.00 | 2.25 s | Failed labels. Invoice errors. | error cards pile up |
| 2 | 00:04.00 | 00:08.50 | 1.48 s | And nobody tells you what to fix. | headline over the blurred errors |
| 3 | 00:08.50 | 00:12.00 | 0.86 s | Meet Expedo. | logo reveal on the drop |
| 4 | 00:12.00 | 00:16.00 | 2.54 s | From order to cash on delivery. All automatic. | the six-step chain + courier / invoicing names |
| 5 | 00:16.00 | 00:20.00 | 2.78 s | Every address is checked before it reaches the courier. | order #1110, Cargus locality error |
| 6 | 00:20.00 | 00:24.00 | 1.81 s | Wrong town? Fix it on the spot. | "Did you mean …?", typing Eforie Nord, label + invoice |
| 7 | 00:24.00 | 00:28.00 | 2.38 s | Every error in plain words, plus what to do. | orders that need attention |
| 8 | 00:28.00 | 00:31.00 | 1.53 s | Select all. One click. | select all → generate label + invoice |
| 9 | 00:31.00 | 00:36.00 | 3.67 s | Labels and invoices for every order, in one PDF. | label + invoice per row, labels PDF |
| 10 | 00:36.00 | 00:40.00 | 2.61 s | Rules for every case. And a test mode. | rules, test mode |
| 11 | 00:40.00 | 00:44.00 | 3.69 s | No duplicates. And a heads-up on customers who refuse parcels. | safety cards: no duplicates, retries, refusal warning |
| 12 | 00:44.00 | 00:47.00 | 1.84 s | Every parcel, tracked to the door. | tracking timeline, second drop |
| 13 | 00:47.00 | 00:50.00 | 2.49 s | And cash on delivery, marked as collected. | dashboard counter |
| 14 | 00:50.00 | 00:53.50 | 2.24 s | Expedo. Orders that ship themselves. | end card |
| 15 | 00:53.50 | 00:55.50 | 2.02 s | Built for Shopify stores in Romania. | end card subline |

## Română

| # | Start | End (max) | TTS length | Line | On screen |
|---|---|---|---|---|---|
| 1 | 00:00.50 | 00:04.00 | 3.12 s | AWB eșuat. Factură cu eroare. | error cards pile up |
| 2 | 00:04.00 | 00:08.50 | 1.72 s | Și nimeni nu-ți spune ce să repari. | headline over the blurred errors |
| 3 | 00:08.50 | 00:12.00 | 1.45 s | Fă cunoștință cu Expedo. | logo reveal on the drop |
| 4 | 00:12.00 | 00:16.00 | 2.50 s | De la comandă la ramburs, totul automat. | the six-step chain + courier / invoicing names |
| 5 | 00:16.00 | 00:20.00 | 2.78 s | Adresa e verificată înainte să ajungă la curier. | order #1110, Cargus locality error |
| 6 | 00:20.00 | 00:24.00 | 3.17 s | Ai greșit localitatea? Corectezi pe loc. | "Ai vrut: …?", typing Eforie Nord, AWB + invoice |
| 7 | 00:24.00 | 00:28.00 | 3.11 s | Fiecare eroare, pe românește, cu ce ai de făcut. | orders that need attention |
| 8 | 00:28.00 | 00:31.00 | 2.77 s | Selectezi tot. Un singur clic. | select all → Generează AWB + factură |
| 9 | 00:31.00 | 00:36.00 | 3.49 s | AWB-uri, facturi și etichete, într-un singur PDF. | AWB + invoice per row, labels PDF |
| 10 | 00:36.00 | 00:40.00 | 3.43 s | Reguli pentru fiecare caz. Și un mod de probă. | rules, test mode |
| 11 | 00:40.00 | 00:44.00 | 3.74 s | Fără AWB-uri duble. Și știi cine refuză colete. | safety cards: no duplicates, retries, refusal warning |
| 12 | 00:44.00 | 00:47.00 | 1.81 s | Coletul e urmărit până la livrare. | tracking timeline, second drop |
| 13 | 00:47.00 | 00:50.00 | 1.95 s | Iar rambursul e bifat ca încasat. | dashboard counter |
| 14 | 00:50.00 | 00:53.50 | 2.97 s | Expedo. Comenzile pleacă singure. | end card |
| 15 | 00:53.50 | 00:55.50 | 1.57 s | Pentru magazinele Shopify. | end card subline |

**How to drop a recorded voice in:** export one WAV/MP3 of the whole voice track, starting at 00:00.00 and timed to
the video. Then run `VOICE_FILE_RO=/path/voice_ro.wav python3 audio.py ro` (or `VOICE_FILE_EN=… python3 audio.py en`).
That replaces the TTS: gentle low cut and compression, the music ducks about 7 dB under the voice, -14 LUFS, and the
language's mp4s are re-muxed.
