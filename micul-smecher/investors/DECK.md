# SOUL: pitch deck content (v1, 2026-09-25)

14 slides, English. Each slide: **on-screen text** (keep it this short), **visual** (file paths are relative to `micul-smecher/`), **speaker notes**. Tags as in [[INVESTORS]]: [V] fetched today · [V-vault] verified in a vault note · [K] background · [E] estimate.
**Rule for every render:** add a small corner label "Render / concept (CGI)" (renders/v6/README and v5/README require it). Show a real photo of the dev-board prototype wherever one exists; investors trust one honest phone photo more than ten renders.
Format: 16:9, black background, one idea per slide, the eyes as the only colour accent. Export the eyes clips (`media/*.mp4`) as looping GIF/MP4 inside the slides.

---

## 1. Title
**On screen:** SOUL — *Your AI. Your object. Nobody else's.* · "Pre-seed · Bucharest · [month] 2027" · Andu, founder · [email]
**Visual:** `renders/v6/soul_v6_hero.png` full-bleed (natural silver, 3/4 view, OU blurred behind). Loop `media/idle.mp4` on the face if the tool allows.
**Notes:** "This is SOUL. It fits in your palm, it's machined aluminium, and the only thing on the front is a face. In the next ten minutes I'll show you why the most interesting AI device of the next two years isn't one the labs will make."

## 2. Problem
**On screen:**
- Your AI lives in a browser tab.
- Every AI device locks you into one company's model (Meta Muse, OpenAI × Ive, Alexa+).
- And most of them listen all the time, or carry cameras.
**Visual:** three small grey tiles: Muse Charm (2 cameras, 5G, US-only), OpenAI device (no screen, 2027, $300–400), Friend ("listens to everything"). Text only, no competitor logos.
**Notes:** Facts: Muse Charm has front and back cameras, 5G, is US-only and 18+ [V-vault 11]; OpenAI's device is a $300–400 metal speaker for 2027 [V-vault 11]; Friend 2.0 at $249 "struggled to sell in volume" [V-vault 11]. People already pay for Claude or ChatGPT. None of these devices let them use it. Humane is the warning: cloud-locked, subscription-locked, bricked in 2025 [V-vault 11].

## 3. The insight
**On screen:** **The labs make the brain. We make the body.**
Model-neutral · private by design · alive without the cloud.
**Visual:** a diagram: three "brains" (Claude, ChatGPT, your API key, plus "offline") → one SOUL. Use `site/media/os-modes.jpg` or `os/screenshots/soulos-ai-mode-picker-1440.png`.
**Notes:** "Meta, OpenAI, Amazon and Google structurally cannot say 'bring your own AI'; their device exists to sell their model. That's a business-model moat, not a code moat [E, 11]. Anthropic has no consumer device and has opened a Bluetooth hardware API for Claude (claude-desktop-buddy, MIT) [V]. We are building the best body for it, and for every other brain."

## 4. Product
**On screen:** 63 × 74 × 27 mm · machined 6061 aluminium, bead-blasted, anodised · round AMOLED face with living eyes · nothing else on the front · no camera · OU: the charging egg that cuts the mic in hardware.
**Visual:** left `renders/v6/soul_v6_family.png` (5 colourways); right-top `renders/v5/soul_v5_ou_night.png` (asleep in OU); right-bottom `renders/v6/soul_v6_macro.png` (bead-blast + chamfer). Optional scale: `renders/v5/soul_v5_hand.png`.
**Notes:** "One object you want to hold. Every day it hatches from OU, its charging egg; at night OU cuts the microphone's power in hardware, so in the egg it is physically deaf [V-vault 09]. In the hand it's hold-to-talk. Five anodised colours. Designed in Romania." Be explicit: these are renders; the pilot shell is CNC-machined (10).

## 5. How it works: four AI modes
**On screen:**
| Mode | What it does |
|---|---|
| **Offline (no AI)** | eyes, notes, reminders, alarms, timer, keyboard EN/RO. Alive forever, no account |
| **Your Claude** | MCP connector + Bluetooth permission buddy for Claude Code / Cowork: approve with a touch |
| **Your ChatGPT** | talk and type through your own account |
| **Your API key** | any compatible model, your bill, your data |
**Visual:** 4 phone-sized screenshots in a row: `os/screenshots/soulos-ai-mode-none-reply-1440.png`, `os/screenshots/soulos-claude-type-reply-1440.png`, `os/screenshots/soulos-ai-mode-chatgpt-reply-1440.png`, `os/screenshots/soulos-ai-mode-settings-1440.png`.
**Notes:** "The AI bill is the customer's, with the provider they already trust; our core has no subscription [E, 11 §4 complaint #4]. Optional paid extras later: premium voice, EU relay (money plan: ~€4.99/month) [E]." Mention the AI Act Art. 50 disclosure on first boot: "I'm an AI, not a person" [V-vault 09].

## 6. Demo moments (3 × 15 seconds)
**On screen:** 1) Claude Code asks → SOUL's eyes get eager → hold to approve. 2) "Remind me at 7 to call Mum" → eyes nod → alarm dial. 3) Nudge it at night in OU → it blinks, sleeps again.
**Visual:** `media/claude_buddy.mp4` (or `media/claude_buddy.gif`), `os/screenshots/soulos-notes-type-reminder-dial-1440.png` + `os/screenshots/soulos-alarm-ring-awake-1440.png`, `media/sleep.mp4` / `renders/v5/soul_v5_ou_night.png`. Live: bring the dev board.
**Notes:** Run the Claude approval live on the dev board if at all possible: it's the one demo nobody else has on a beautiful object (Buddy clones are ASCII on plastic, $110–125 [V-vault 11]). Then the notes/reminder: "it does things". End with sleep: calm, no guilt, no nagging (the #10 complaint in the category, 11 §4).

## 7. Why now
**On screen:**
- Apr 2026: Anthropic opens a Bluetooth hardware API for Claude (open source) [V]
- 2026: Meta Muse Charm (US-only), OpenAI device slips to 2027 [V-vault]
- ESP32-S3 + round AMOLED make a premium device buildable for ~$30 of core electronics [V-vault 10]
- EU window: Muse isn't in the EU; Alexa+ doesn't speak Romanian [V-vault 11]
**Visual:** a timeline strip; small inset `os/screenshots/soulos-claude-1440.png`.
**Notes:** "The market is being defined in the next 12 months. The big players have announced but not shipped in Europe. We want our hero film out before OpenAI's reveal (plan: before Feb 2027) [E, 11]." Espressif is already promoting Claude-on-ESP32 hardware [V].

## 8. Market & comparables
**On screen:** Premium personal AI hardware is a proven wallet, not a proven winner.
| Company | Proof |
|---|---|
| Oura | 5.5M rings, ~$1B revenue 2025, $11B valuation [V-vault 05] |
| Plaud | 2M+ devices, ~$100M ARR on software [V-vault 11] |
| Nothing | $8M from 8k+ community investors; $1.3B valuation [V-vault 05] |
| Fuzozo (CN) | ~300k AI companions sold, 40k in one shopping festival [V-vault 11] |
| Starboy (metal, no AI) | $139–599, batches sold out [V-vault 11] |
| Tamagotchi | 100M+ units lifetime [V-vault 05] |
**Visual:** `renders/v5/soul_v5_family.png` faded right, table left.
**Notes:** Don't show a top-down TAM number we can't defend. Say: "our beachhead is people who already pay for Claude or ChatGPT and care about objects: developers, designers, the Claude Code community. Our plan is 25 → 300 → 1,000 → 10,000 units [E]." Be honest that no one has yet built a large AI-companion business in the West; that's the risk and the opportunity.

## 9. Competition map
**On screen:** the 2 × 2 from note 11: X = useful (does things) ↔ emotional (creature); Y = closed AI ↔ your AI / offline. SOUL alone in the bottom middle.
**Visual:** redraw the ASCII map from `research/11-competitori.md` §2 as a clean chart: top-left Alexa+/Bee/OpenAI × Ive/Rabbit/Plaud; top-right Muse Charm/Friend/Fuzozo/Emo; bottom-left Buddy DIY/xiaozhi/Omi; bottom-right Starboy/Moflin/Ropet/Eilik; SOUL on the axis, slightly right.
**Notes:** "Useful ones look like kits; beautiful ones do nothing; big ones lock you in. Nobody has face + premium object + bring-your-own-AI + actions + offline at once [E, 11]." Pre-empt copying: a xiaozhi clone could appear in 2–6 weeks; our moat is neutrality, object, trust (EU, no cameras), Romanian/small languages and the Founders community (11 §3).

## 10. Business model & unit economics (estimates, labelled)
**On screen:**
| | Founders 00 (25) | Standard @1k | Standard @10k |
|---|---|---|---|
| Price incl. 21 % VAT | €349 | €249 | €249 |
| Net of VAT | €288 | €206 | €206 |
| COGS (device + OU + box) | ~€200 [E, 10] | ~€90–100 [E] | ~€50–55 [E] |
| Payment + warranty | ~€12 | ~€9 | ~€9 |
| **Gross margin / unit** | **~€75 (26 %)** | **~€100 (48 %)** | **~€145 (70 %)** |
| × landed (rule ≥ 2.5) | 1.3 × | **2.0 × (below rule)** | 3.4–3.7 × |
Plus: optional voice/relay subscription ~€4.99/month (model: 30 % attach) [E].
**Visual:** table only; small `blueprints/soul_blueprint_exploded.png` in the corner.
**Notes:** Say it straight: "The pilot loses money once you add CE testing (€5–12k) [V-vault 10]; it's a proof purchase, not a business. Standard at €249 only clears our 2.5× rule on steel/stamped tooling at ≥ 5–10k units; at 1k we either price €279 or accept 2×." Sources: COGS €200 at 25 units (CNC aluminium, 10 §1.3); PC-shell system COGS $94 @1k and $52 @10k (09 §3.7) plus an aluminium premium of +$1–6 at 10k for stamped 5052 (10 §0) [E]. Tooling for 10k ≈ €64–107k all-in (09) [E]. Voice cost ~$1–4/user/month + LLM, but BYO-AI moves the model cost to the user's own plan [E, money plan].

## 11. Go-to-market: Founders 00 → Standard
**On screen:**
1. **Founders 00**: 25 numbered units, €349 (#001–#010 €399 or auction), after CE radio tests; owners are co-designers.
2. **Deposits**: €20 refundable reservations for Batch 1; target 2,000.
3. **Batch 1**: 300 units on bridge tools, own Shopify (Kickstarter is not open to Romanian companies [V]).
4. **Standard €249** after the OpenAI reveal sets the ceiling.
Channels: Claude/dev community (r/ClaudeAI, HN, X, Product Hunt), design press, 20–30 creators under embargo, Romania + DE/FR/IT/PL.
**Visual:** `renders/v5/soul_v5_unbox.png` (the "birth" unboxing) + `site/screenshots` landing page capture (or `site/media/render-desk.jpg`).
**Notes:** "Founder's edge: Andu runs e-commerce and paid acquisition (MundiShop) [add real numbers]. Lesson from Friend: $1M of ads for ~3k units [V-vault 11]. We start where the community already is and where the demo is native: Claude Code users." Gate A from the money plan: ≥ 100 paid reservations within 14 days of the clip [V-vault].

## 12. Traction & milestones
**On screen (built, as of Sep 2026):**
- Firmware "Suflet" v0: living eyes, 24 reactions, personality from the chip, Claude Hardware Buddy link; compiles for 2 Waveshare AMOLED boards; 24 native tests + simulator [V-vault firmware README]
- AI backend: birth, talk, memory, reminders, notes, diary; Claude SDK with structured output; 49 tests
- SoulOS interactive prototype (keyboard EN/RO, notes, reminders, alarms, AI-mode picker)
- Landing page (EN/RO), photoreal renders, CAD for the DIY pilot
**Next (fill in live numbers):** waitlist [N] · deposits [N] · Founders 00 [sold in X h] · clip views [N]
**Visual:** a 2 × 2 grid: `media/contact_sheet.png` (eye states), `os/screenshots/soulos-keyboard-hello-1440.png`, `os/screenshots/soulos2-home-1440.png`, `site/media/render-hero.jpg`; a real photo of the dev board if available.
**Notes:** Honesty wins here: "No physical aluminium unit yet; the first 10 CNC shells are ordered [update]. Everything on this slide is software or renders; the next 90 days are about turning it into paid demand." Milestones to show as a line: CE pre-scan → Founders 00 shipped (Q1 2027) → 2,000 deposits → Batch 1 (300) → DVT on custom PCB.

## 13. Team & hires
**On screen:**
- **Andu**, founder & CEO: brand, e-commerce, growth (MundiShop, Expandly) [add 2 real numbers]
- **Technical co-founder** (firmware + electronics): [name, signed / in final talks]
- **Advisors**: hardware operations (EVT→PVT), industrial design/CMF, AI/agents, a Romanian angel
- **First hires with the round**: RF/hardware engineer (contract → hire), part-time community/content
**Visual:** portraits or silhouettes; `renders/v6/soul_v6_side.png` as a quiet background.
**Notes:** Name the risk before they do: "I'm not an engineer. That's why the first money goes to a technical co-founder with vesting, and why we already have firmware, tests and CAD instead of a slide." Show full-time commitment and how the other businesses run without you.

## 14. The ask
**On screen:** **Raising €350k** (angel proof round, convertible, cap €2.5M [E])
| Use of funds | € |
|---|---|
| Team: technical co-founder 12 months + founder stipend | 110k |
| Engineering: custom PCBA, RF in aluminium, EVT | 60k |
| Compliance: CE/RED, EN 18031 cyber, battery tests | 40k |
| Founders 00 + Batch 1 inventory (300 units, recouped by sales) | 45k |
| Hero film, launch, creators | 35k |
| Legal, IP, trademarks | 15k |
| Cloud, voice, tools | 10k |
| Contingency (10 %) | 35k |
**Milestones it buys (9–12 months):** CE-tested Founders 00 shipped · 2,000 paid deposits · 300 units in customers' hands · DVT on a custom board · pre-seed €1–1.5M ready (EGV/Credo/Inovo).
**Visual:** `renders/v6/soul_v6_back.png` or `renders/v6/soul_v6_hero.png` small; closing line: "The labs make the brain. Help us make the body."
**Notes:** "The round is structured so every euro unlocks a gate: no tooling without paid orders, bridge tools only for Founders [V-vault 05/09]." Numbers are [E]; sanity check: CE €5–12k small lot and €30–80k for 1,000+ units incl. cyber [V-vault 09/10]; PCBA design $15–30k [V-vault 09]. If an investor wants more, the €1–1.5M version adds steel tooling (€64–107k) and a 1,000-unit run (05: €0.36–0.75M all-in for 1,000 units [V-vault]).

---

## Appendix slides (backup, not presented)
- **A1 Privacy & compliance:** no camera, hold-to-talk, mic hardware-gated in OU, AI Act Art. 50 disclosure at first boot, 18+ AI account, EU relay, offline for life ("Soul Pledge") [V-vault 09/11]. Visual: `renders/v5/soul_v5_ou_closed.png`.
- **A2 Hardware stack:** ESP32-S3, round AMOLED 466 × 466, 2 mics, speaker, AXP2101 PMU, IMU, RTC, ~1000 mAh user-replaceable cell (EU battery rule from 18 Feb 2027) [V-vault 09, money plan]. Visual: `blueprints/soul_blueprint_section.png`, `renders/v6/soul_v6_bottom.png`.
- **A3 Risks & mitigations:** table from INVESTORS §5.
- **A4 Roadmap to 10k:** EVT → DVT → PVT 16–30 weeks, $65–210k [V-vault 05]; tooling €47–79k (09).
- **A5 SoulOS gallery:** `os/screenshots/soulos-today-1440.png`, `os/screenshots/soulos-translate-1440.png`, `os/screenshots/soulos-reminders-1440.png`, `os/screenshots/soulos2-weather-1440.png`, `os/screenshots/soulos2-timer-countdown-1440.png`.
