# AI companion gadgets — market, tech, cost, regulation (raw, 2026-09-24)

Tags: [V] primary source today · [R] press/secondary · [E] estimate.

## 1. AI wearables: failed vs sold
| Product | Price / sub | Numbers | One line |
|---|---|---|---|
| Humane AI Pin | $699 + $24/mo required | raised $240M; ~10k sold vs 100k target; returns > sales mid-2024; HP bought assets $116M, bricked 28 Feb 2025 [R] | Failed: price, forced subscription, heat, slow, less than a phone |
| Rabbit R1 | $199 | 100–130k sold; ~5,000 daily users Sept 2024 [R] | Failed: demo > reality, no daily reason |
| Friend | $99→$129; v2 $249 + $10/mo | ~3,000 sold by Oct 2025; $1M subway campaign defaced [R] | Always-listening + "lonely" pitch = creepy |
| Limitless | $99 | acquired by Meta Dec 2025 [R] | exit via team/memory stack |
| Bee | $49.99 + $19/mo | acquired by Amazon Jul 2025 [R] | cheap recorder + knowledge graph |
| **Plaud** | Pro $99.99/yr | **>2M devices; >$100M software ARR (Jun 2026); ~50% of owners pay** [R] | one clear job, worth paying for |
| Omi | ~$129 | open source, niche [R] | developers love it |
| Moxie | $799 | shut down Dec 2024, robots stopped working [R] | cloud-dependent companion died with its company |

OpenAI + Jony Ive screenless device rumoured H2 2026 / 2027; Meta pendant rumoured [R]. Big tech takes the "general assistant" slot; small players win on character.

## 2. AI companions that sold
| Product | Price | Units / funding | Notes |
|---|---|---|---|
| BubblePal (Haivivi) | ¥399–449; US $149 | 300k+ by Apr 2026 [R] | clip-on for plush, Wi-Fi, **press-to-talk**, licensed characters, DeepSeek, 12-month VIP bundled; 10–15 s delay criticised |
| **Fuzozo (Robopoet)** | ¥399 (~$55) | ~300k since Jul 2025; ¥100M pre-A (Tuya, Sequoia China); Makuake ¥83M [V/R] | plush bag-clip "eye-blinking" companion; active users talk **> 40 min/day**; monetises via token "energy" packs |
| **Eiliko** (Energize Lab) | $59.90 | KS ~$600k, 4,707 backers [V/R] | bag charm, 1.28" TFT face, 400 mAh (~150 min use), AI chat via app, no subscription, "soulmate" pairing |
| Ropet | ~$300 | KS ~$313k; ~20k units; Series A > $10M [V/R] | **no free chat on purpose** ("voice assistant breaks the creature feel"); 80–90% active at 90 days |
| Casio Moflin | $429 | > 20k cumulative by Jul 2026 [R] | no LLM |
| Mirumi | $118–150 | KS ¥79.4M, 2,053 backers [R] | no AI chat, shy glance robot charm |
| FoloToy | — | pulled Nov 2025 after unsafe answers; OpenAI suspended dev [R] | kids' safety failure |
| Miko | $14.99/mo | 700k–1M units [R] | kids' content subscription |
China AI-toy market ≈ ¥29B (~$4.3B) 2025, > ¥100B forecast 2030, > 1,500 companies, **30–40% return rates** [R].

## 3. xiaozhi-esp32
- Firmware github.com/78/xiaozhi-esp32: **MIT**, ~30.2k stars, ESP-IDF ≥ 6.0.1, 138 board folders [V].
- Wake word (ESP-SR), WebSocket or MQTT+UDP, Opus streaming, ASR→LLM→TTS or realtime, AEC full duplex, voiceprint, emoji/expression display, camera, battery mgmt, BluFi, 4G, **MCP on device + cloud**, OTA [V].
- Defaults point to xiaozhi.me / api.tenclass.net → must change to our EU servers [V].
- Supports Waveshare AMOLED **1.32, 1.43C, 1.75, 1.75C, 1.8, 2.06, 2.16**, LCD 1.85x; **not** the 1.43 non-C nor LCD-1.28 [V].
- Server github.com/xinnan-tech/xiaozhi-esp32-server: **MIT**, ~10.7k stars, Python + Java/Vue admin, Docker; any OpenAI-compatible LLM, OpenAI transcribe, Groq Whisper, OpenAI tts, custom HTTP TTS; **no native Anthropic** [V]. Anthropic's OpenAI-compatible endpoint is for testing and lacks prompt caching → write a native provider [V].
- Western product: yes if we own the backend (EU hosting, replace EdgeTTS, security-review activation) [E].

## 4. Recommended dev board for voice
**Waveshare ESP32-S3-Touch-AMOLED-1.75** ($29.99–39.99): round 466² CO5300, ES8311 + ES7210, **2 mics with AEC, speaker included**, QMI8658 IMU, RTC, AXP2101 PMU, PWR key, supported by xiaozhi [V]. 1.43C keeps the 46 mm size but has no IMU and only 8 MB flash.

## 5. Voice cost per user/month (10 exchanges/day; LLM excluded) [E from V prices]
- STT: gpt-4o-mini-transcribe $0.003/min → **$0.15**; Deepgram Nova-3 $0.24–0.46; ElevenLabs Scribe v2 RT $0.33; Azure $0.83.
- TTS: Azure Neural $15/1M chars → $0.99; OpenAI tts-1 $0.99; gpt-4o-mini-tts ~$1.13; Cartesia ~$2.50; **ElevenLabs Flash $3.30**.
- Stacks: budget ~$1.15/mo; balanced ~$2.8; premium character voice ~$3.6 (ElevenLabs v3 ~$6.9). Heavy users (40 min/day) ×8–10 → need fair-use caps / credits.
- Latency target < 1.5 s; Deepgram Nova-3 may lack Romanian.

## 6. Regulation
- **AI Act Art. 50(1) disclosure from 2 Aug 2026** (fines up to €15M / 3%); Art. 50(2) synthetic audio marking (existing systems until 2 Dec 2026); Art. 5 bans manipulation & exploiting age vulnerabilities (since 2 Feb 2025) → no guilt-tripping retention [V].
- Italy Garante fined Replika **€5M** (2025) — no legal basis, no age verification [V]. FTC 6(b) inquiry into AI companions & kids (Sep 2025) [V]. California SB 243 (2026): disclosure, 3-h break reminders for minors, self-harm protocol [R]; SB 1119 age verification from Jul 2027 [R]. Romania digital consent age 16.

## 7. Subscriptions
Humane $24 required (failed) · Bee $19 · Friend $10 optional · Miko $14.99 · **Plaud ~50% pay** · BubblePal 12-month bundled · Fuzozo top-ups · Eiliko/Grem/Omi none.

## Top 10 lessons
1. Creature first, chatbot second (Ropet 80–90% 90-day retention without chat; Rabbit 5% DAU).
2. Impulse band $49–79 sells volume (Fuzozo 300k at $55).
3. Never paywall the personality; sell capacity (free daily voice allowance, then credits / clear-value plan).
4. Latency is the product: stream everything, < 1.5 s, cover waits with "thinking" eyes.
5. Budget voice $1–4/user/month; cap heavy users.
6. Survive the company's death: offline mode + publish/escrow the server (trust feature).
7. Privacy by architecture: press-to-talk or wake word, visible listening state, EU hosting, delete audio by default.
8. Launch for adults 16+, not kids.
9. Visible compliance: "I'm an AI" at first boot / box / on request; no guilt-trip retention; self-harm protocol; RED cyber + CE; own the server & OTA URLs.
10. Distribute like a collectible (crowdfunding, Japan route, soulmate pairing); fight 30–40% returns with day-30 content: personality growth, memory, seasonal events.
