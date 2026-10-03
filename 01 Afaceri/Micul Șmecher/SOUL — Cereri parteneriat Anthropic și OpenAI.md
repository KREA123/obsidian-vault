---
tip: corespondență
afacere: Micul Șmecher
actualizat: 2026-10-03
---

# SOUL — cereri către Anthropic și OpenAI

> Decizia lui Andu (2026-10-03): **fiecare om cu AI-ul lui**, din contul lui. Nu plătim noi AI. Vezi [[Jurnal decizii]] și [[SOUL — Harta memoriei]].
> - **ChatGPT:** login cu contul lui prin „Sign in with ChatGPT” (cere aprobarea OpenAI pentru aplicații comerciale) → email 2.
> - **Claude:** abonamentul (Pro/Max) nu poate fi folosit de alte firme (regulile Anthropic). Azi: contul lui de Anthropic Console (cheie API, plătește la bucată) + conectorul din aplicația Claude. Cerem excepție/parteneriat → email 1.

> **Status 2026-10-03: nicio confirmare în vault că au fost trimise** [neverificat] — pas fondator în [[De continuat — SOUL]]. La Anthropic adaugă și cererea pentru **canalul SOUL Bridge** (listare în pluginurile oficiale Claude Code + confirmare scrisă pentru uz personal pe Pro/Max) — `micul-smecher/docs/08-OWN-CLAUDE.md` §7.

Trimite de pe adresa firmei, semnat ARTEMIS DIGITAL S.R.L. Atașează link-ul site-ului și trailerul.

---

## Email 1 — Anthropic (sales / partnerships)

Unde: formularul „Contact sales” de pe https://www.anthropic.com/contact-sales (link-ul apare și pe pagina de reguli https://code.claude.com/docs/en/legal-and-compliance).

**Subject:** SOUL — a dedicated Claude hardware companion: request to let users connect their own Claude account

Hello Anthropic team,

I'm Andu, founder of ARTEMIS DIGITAL S.R.L. (Bucharest, Romania). We are building **SOUL**, a palm-sized aluminium device with a round glass screen and two living eyes, designed first and foremost as a physical home for Claude: you hold the glass and talk to Claude, it shows Claude's answers, sets reminders and notes, and approves Claude Code requests via the Claude Desktop hardware buddy protocol.

We have read your policy that third-party products may not offer Claude.ai login or route requests through Free/Pro/Max credentials, and we comply with it. Today SOUL supports:
- the user's own Anthropic API key (their own Console account), and
- a remote MCP connector, so the user's Claude app (web, desktop, mobile) can act on SOUL.

Our users strongly want to use **their own Claude subscription** with SOUL. We would like to ask:
1. Is there a partner programme or approved path (e.g. OAuth on behalf of the user) that would let SOUL owners connect their own Claude account?
2. If not, could we be considered for one, or for listing the SOUL connector in your connector directory?
3. Any guidance for hardware partners (branding "Works with Claude", review of our connector, rate limits).

We are preparing a first batch of 10–25 units and an EU-funded proof-of-concept project. Happy to send a prototype, the firmware and connector source, and a demo video.

Thank you,
Andu — Founder, ARTEMIS DIGITAL S.R.L.
[email firmă] · [telefon] · [link site SOUL]

---

## Email 2 — OpenAI („Sign in with ChatGPT” waitlist)

Unde: **formularul de interes OpenAI: https://openai.com/form/sign-in-with-chatgpt-interest/** („Sign in with ChatGPT”, lansat 29.09.2026; aplicațiile plătite sau găzduite — SOUL e ambele — intră pe waitlist; linkul e verificat în `micul-smecher/docs/07-CONNECT-AI.md` §1.10, câmpurile formularului nu au fost citite). Textul de mai jos îl pui în câmpul de descriere.

**Subject:** Waitlist request — SOUL hardware companion (Sign in with ChatGPT)

Hello OpenAI team,

I'm Andu, founder of ARTEMIS DIGITAL S.R.L. (Bucharest, Romania). We build **SOUL**, a small Wi-Fi/BLE AI companion device with a round screen and expressive eyes. We would like to join the **Sign in with ChatGPT** waitlist so SOUL owners can connect their own ChatGPT Plus/Pro account instead of using API keys.

How we would use it:
- Sign-in happens in the owner's phone browser on our HTTPS cloud page (system browser + PKCE); the device never sees credentials.
- Requests go through the Responses API (store:false, stream:true): short text turns and function tools (alarms, reminders, notes).
- EU hosting, no always-on listening (SOUL only listens while the user holds the glass).

We also offer a remote MCP connector for ChatGPT developer mode and would welcome guidance on publishing it as a ChatGPT app.

Thank you,
Andu — Founder, ARTEMIS DIGITAL S.R.L.
[email firmă] · [telefon] · [link site SOUL]
