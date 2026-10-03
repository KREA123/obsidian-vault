# 08 · Your own Claude on SOUL (Pro/Max, through Anthropic's own apps)

*SOUL package · 3 Oct 2026 · rev. 1. Scope: how a SOUL owner types or says something on SOUL and gets the answer from **their own** Claude subscription, using only Anthropic's official apps that the owner installs and signs in to himself. Complements `07-CONNECT-AI.md` (lab path L1 there is this document's §3). Code: `bridge/` (SOUL Bridge prototype, Node). Markers as in doc 07: [V] verified today against the official page in §9 · [R] read/run in this repo · [L] likely · [U] unverified, test before promising · [E] our estimate.*

---

## Rezumat pentru fondator (RO)

**Întrebarea:** poate cineva cu abonament Claude Pro/Max să scrie pe SOUL și să primească răspunsul de la *Claude-ul lui*, fără să plătim noi AI și fără să încălcăm regulile Anthropic?

**Răspunsul scurt: da, dar numai cu calculatorul utilizatorului pornit, și cu un risc de politică pe care trebuie să-l închidem cu Anthropic înainte de a-l promova.**

Ce e interzis clar [V]: noi (SOUL) nu avem voie să cerem, să stocăm, să trecem prin serverele noastre sau să extragem login-ul/tokenul claude.ai al cuiva, și nici să rulăm Claude Code cu tokenul utilizatorului pe serverele noastre. Nu construim așa ceva, niciodată.

Ce e permis și am construit: **SOUL Bridge**, un mic program open-source care rulează *pe calculatorul utilizatorului*. Utilizatorul instalează singur **Claude Code** (aplicația oficială Anthropic) și se loghează singur în contul lui. Claude Code pornește SOUL Bridge ca „canal" (*channel*, funcție oficială Anthropic, în *research preview*, la fel ca pluginurile oficiale Telegram/Discord/iMessage). Întrebarea scrisă pe SOUL ajunge prin rețeaua de acasă la Bridge → intră în sesiunea Claude Code a utilizatorului → Claude răspunde cu un instrument `soul_reply` → răspunsul (și eventual o alarmă / un memento / o notiță) apare pe SOUL. Nicio parolă sau token Claude nu trece prin Bridge sau prin SOUL.

| Ruta | Merge azi? | Ce trebuie | Risc de politică |
|---|---|---|---|
| **1. SOUL Bridge ca *channel* Claude Code** (recomandat) | Prototip funcțional, testat cu SOUL simulat și Claude simulat; Claude Code real (2.1.288) pornește Bridge-ul și vede instrumentele lui. **Livrarea mesajului într-o sesiune Claude reală, logată, NU a fost testată** (aici nu avem voie să folosim un cont real) | PC/Mac pornit, fereastra Claude Code deschisă, abonament Pro/Max, firmware SOUL cu endpoint-ul `/bridge` (**nu există încă**) | **Mediu.** Canalele „custom" cer azi flag-ul `--dangerously-load-development-channels`, documentat pentru dezvoltare locală. Ca să-l vindem ca funcție trebuie ca Anthropic să ne pună pe lista aprobată (cerere prin partener). Până atunci: „experimental, pentru utilizatori avansați", nu în reclame |
| 1b. Bridge cu `claude -p` (fără fereastră deschisă) | Construit, **oprit implicit** | la fel, dar fără fereastră | **Mai mare.** Arată ca „un produs terț care folosește abonamentul utilizatorului prin Agent SDK", exact zona pe care Anthropic spune că n-o permite fără aprobare. Nu-l livrăm fără confirmare scrisă |
| **2. iPhone: Shortcut cu acțiunea „Ask Claude"** | Acțiunea există oficial (iOS 18+) și răspunsul curge în Shortcut [V]. Nu am construit fișierul Shortcut (trebuie un iPhone) și cloudul nu are încă endpoint-urile de citire/răspuns | iPhone cu app-ul Claude logat; utilizatorul apasă (widget/Siri/notificare) | **Mic** (utilizatorul folosește app-ul oficial, mesajele se scad din limita lui [V]). Dar **nu e automat**: rulează când utilizatorul îl declanșează; rularea complet în fundal e [U] |
| **3. Claude Desktop / claude.ai → SOUL (conectorul, modul C din doc 07)** | Construit în cloud, netestat cu claude.ai real | orice plan Claude | Mic (funcție oficială). Dar direcția e inversă: Claude comandă SOUL, nu SOUL întreabă Claude |

**Ce înseamnă pentru utilizator (ruta 1), prima dată:** instalează Claude Code și se loghează (1–2 min) → instalează SOUL Bridge → pe SOUL: *Setări › AI › Conectează calculatorul* afișează un cod → îl tastează în Bridge → dublu-click pe „Start SOUL" → acceptă 3 dialoguri ale Claude Code. Zilnic: dublu-click „Start SOUL" + confirmarea avertismentului „development channels" (la fiecare pornire, cât timp suntem în afara listei aprobate). Latență estimată: 3–15 s pe răspuns [E].

**Riscul, în cuvinte simple:** nu atingem niciodată login-ul Claude, deci nu suntem în zona interzisă explicit. Zona gri e alta: (a) folosim un flag de dezvoltator pentru o funcție de produs; (b) Anthropic ar putea considera că SOUL „își oferă produsul pe limitele abonamentului utilizatorului". Ca să reducem riscul: Bridge open-source, rulează doar pe calculatorul utilizatorului, cu login-ul lui, uz personal, nicio dată Claude prin serverele noastre, fără branding „Claude Code" în numele produsului, și **cerem Anthropic, în scris, aprobarea canalului** (adăugăm la draftul de parteneriat existent). Dacă Anthropic spune nu, ruta 1 rămâne un proiect open-source pentru pasionați, nu o funcție SOUL.

**Acțiuni fondator:** (1) trimite cererea către Anthropic: listarea canalului SOUL în marketplace-ul oficial + confirmare pentru uz personal (§7); (2) prioritizează în firmware endpoint-ul `/bridge` (§4) după ce agentul de firmware termină CloudLink; (3) testează pe propriul Mac/PC cu contul tău Pro/Max pașii din §3.1 (singurul test pe care noi nu-l putem face aici).

---

## 1. What "use my own Claude" can and cannot mean

Anthropic's Claude Code legal page, verified today [V]:

- OAuth sign-in "is intended exclusively for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications."
- "Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, or Max plan credentials on behalf of their users. Moreover, developers may not collect, store, or intermediate Claude.ai credentials or session tokens — sign-in to a Claude account must complete through Anthropic's own flow."
- It "does not … prevent an end user from signing in to the unmodified Claude Code binary with their own Claude subscription".
- "Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and the Agent SDK."

The Agent SDK overview adds [V]: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK."

The support article on Agent SDK plan usage says today [V]: "We're pausing the changes to Claude Agent SDK usage described below. For now, nothing has changed: Claude Agent SDK, `claude -p`, and third-party app usage still draw from your subscription's usage limits." (The paused plan would have moved that usage to separate monthly credits.)

So the only legitimate shapes are those where **the user runs an Anthropic app, signs in through Anthropic's flow, on his own device**, and SOUL only exchanges plain questions and answers with that app. Never built, never suggested: a SOUL login screen for claude.ai, reading `~/.claude` / the keychain, `claude setup-token` piped to SOUL, running Claude Code with the user's token on SOUL Cloud, or any proxy of claude.ai traffic.

## 2. The three routes compared

| | **1 · SOUL Bridge (Claude Code channel)** | **2 · iPhone "Ask Claude" Shortcut** | **3 · Claude app → SOUL (connector / local MCP)** |
|---|---|---|---|
| Direction | SOUL asks, user's Claude answers | SOUL asks (via inbox), user's Claude answers when the Shortcut runs | user's Claude acts on SOUL |
| Official mechanism | Claude Code *channels*, research preview [V] | Claude iOS App Intent "Ask Claude", iOS 18+ [V] | remote MCP connector (claude.ai, Desktop, mobile) [V]; local MCP in Claude Desktop [V] |
| Status in this repo | **prototype built** (`bridge/`), 17 tests + e2e with fake SOUL and mocked Claude [R]; wiring checked against real Claude Code 2.1.288 (§3.4) | **recipe only** (§5); cloud endpoints not built; Shortcut file not built | connector built in `ai/` (doc 07 mode C), not tried with real claude.ai |
| Plan | Pro or Max (Claude Code is not in Free [L]); Team/Enterprise only if an Owner enables channels [V] | any plan with the iOS app (counts toward usage limits [V]) | any plan incl. Free (1 custom connector) [V] |
| Needs | computer on and awake, Claude Code window open, home Wi-Fi (or SOUL Cloud relay, not built) | iPhone, Claude iOS app signed in, user trigger | Claude app |
| Real time | yes, while the session is open [V] | no: runs when triggered | n/a |
| Latency | ≈ 3–15 s per answer [E] (model time; push is immediate [V]) | ≈ 5–20 s after the trigger [E] | Claude's own reply time |
| First-time steps | ≈ 7 (§3.1) | ≈ 6 (§5) | ≈ 7 (doc 07 §0.1) |
| Policy risk | **medium**: dev-channel flag; "product on user's plan" reading (§6) | **low** | **low** |

## 3. Route 1 · SOUL Bridge

### 3.1 User steps (target UX, and what exists today)

| # | Step | Today |
|---|---|---|
| 1 | Install **Claude Code** from Anthropic (code.claude.com; one installer per OS) | official [V] |
| 2 | Open a terminal, run `claude`, sign in to **your own** Claude account in Anthropic's browser flow | official [V]; SOUL never sees it |
| 3 | Install **SOUL Bridge** | today: `cd bridge && npm install` (Node ≥ 20). **Not built:** a signed one-click installer bundling Node, and a tray/menu-bar icon "SOUL connected". Today the status is `soul-bridge status` / `~/.soul-bridge/status.json` |
| 4 | On SOUL: *Settings › AI › Pair a computer* shows a 6-digit code; run `soul-bridge pair 123456` (SOUL found as `soul.local`, or `--soul ws://soul-xxxx.local:8765/bridge`) | **firmware screen + endpoint not built** (§4); works against the fake SOUL |
| 5 | `soul-bridge setup` → creates `~/SOUL-Claude/` with `.mcp.json`, locked-down `.claude/settings.json`, `CLAUDE.md`, and launchers `Start SOUL.command` (macOS), `Start SOUL.cmd` (Windows), `start-soul.sh` | built [R] |
| 6 | Double-click **Start SOUL**. First time Claude Code asks: trust this folder → *Yes*; "New MCP server found: soul" → *Use this MCP server*; development-channels warning → *I am using this for local development*. Keep the window open | dialogs [V] from the docs; the dev-channel warning appears on **every** start while SOUL is not on the approved allowlist [L] |
| 7 | Ask on SOUL ("Trezește-mă mâine la 7"). SOUL shows "Claude is thinking…" then the answer; the alarm is set | e2e with fake SOUL + mocked Claude [R]; **not tried with a signed-in Claude** [U] |

What the launcher runs (no credential anywhere, binary unmodified):

```
cd ~/SOUL-Claude
MCP_PROTOCOL_NEGOTIATION=legacy claude --dangerously-load-development-channels server:soul \
  --tools "" --allowedTools mcp__soul__soul_reply mcp__soul__soul_status --name SOUL
```

- `--tools ""` removes every built-in tool (shell, files, web) from that session [V: CLI reference]: a question typed on SOUL by anyone in the house cannot make Claude run commands on the PC. `.claude/settings.json` also denies Bash/Edit/Write/Read/WebFetch as a second fence (it only applies once the folder is trusted [R: Claude Code says so]).
- `--allowedTools` pre-approves only the reply tool, so answering never stalls on a permission prompt.
- `MCP_PROTOCOL_NEGOTIATION=legacy`: channels cannot be delivered over MCP revision 2026-07-28 [V]; our SDK (1.32.0, latest revision 2025-11-25 [R]) never negotiates it anyway; the variable is belt and braces.
- Optional for users who want web answers (weather, news): `--tools "WebSearch"` plus `--allowedTools WebSearch` [L]; not the default.

### 3.2 How it works

```
SOUL (round screen)  --ws, LAN-->  soul-bridge channel  --stdio MCP-->  Claude Code (user's own, signed in)
      ^                              (spawned BY Claude Code)                    |
      +------ answer {text, actions} <--- soul_reply tool call <-----------------+
```

- **Channel contract** [V: channels reference]: the server declares `capabilities.experimental['claude/channel'] = {}`, pushes `notifications/claude/channel` with `content` (the question) and `meta` (identifier keys only: `question_id`, `lang`, `from`, `now`, `tz`, `soul_name`), and exposes a reply tool. Claude sees `<channel source="soul" question_id="q_…" lang="ro" now="2026-10-03T18:02" …>Trezește-mă mâine la 7</channel>` and calls `soul_reply {question_id, text, actions}`.
- **No permission relay**: we do not declare `claude/channel/permission`; nobody approves tool use from SOUL's screen.
- **Sender gating** [V: required by the docs]: only the paired SOUL can push; the link is authenticated with the bridge token SOUL issued at pairing (`sbt_…`, stored `0600` in `~/.soul-bridge/config.json`). It is a SOUL token, not a Claude credential; `config.save()` refuses anything that looks like an Anthropic key or OAuth token [R].
- **Validation**: the bridge checks every action against the same schemas as `ai/suflet_ai/actions.py` (`note.create`, `reminder.create`, `alarm.set`, `timer.start`, `focus.start`, `message.draft`, `list.add`, `answer.show`), max 5 per answer; invalid ones are dropped and reported back to Claude in the tool result [R].
- **Timeouts**: SOUL gets `ask.ack` at once, then `answer` or `answer.error {timeout|claude_unavailable|busy}` within 120 s. Events queue in Claude Code while it is busy and arrive together on the next turn [V].
- **Limits** [V]: events only arrive while the session is open; Claude Code drops channel events silently if the channel is not registered (no error to us), hence the timeout. Conversation context accumulates in that one session (auto-compact handles it).

**Print mode (1b, off by default).** `soul-bridge print` runs the user's own `claude -p` once per question with `--output-format json --json-schema <answer schema> --tools "" --strict-mcp-config --no-session-persistence`, never `--bare` (bare mode never reads the subscription login [V]). No terminal window needed, but see §6 for why we do not ship it.

### 3.3 Files

| File | What |
|---|---|
| `bridge/src/protocol.js` | wire protocol v1 (§4), frame validation, `ws://` only on the LAN |
| `bridge/src/soul-link.js` | outbound WebSocket to SOUL, pairing, reconnect with backoff |
| `bridge/src/core.js` | pending questions, ack/answer/timeout/busy, action validation |
| `bridge/src/actions.js` | action schemas mirroring `ai/suflet_ai/actions.py` |
| `bridge/src/channel.js` | the Claude Code channel MCP server (`soul_reply`, `soul_status`) |
| `bridge/src/print-runner.js` | optional `claude -p` runner |
| `bridge/src/config.js`, `setup.js` | config (no Claude secrets), `~/SOUL-Claude` folder + launchers |
| `bridge/bin/soul-bridge.js` | CLI: `pair`, `setup`, `channel`, `print`, `status`, `doctor` |
| `bridge/tools/fake-soul.js` | fake SOUL device (server side of §4) |
| `bridge/tools/fake-claude-code.js`, `fake-claude.js`, `mock-brain.js` | mocked Claude Code (spawns the channel over stdio like Claude Code does) and mocked `claude -p` |
| `bridge/tools/e2e-fake-soul.js` | end-to-end demo: `npm run e2e` |
| `bridge/test/*.test.js` | `npm test` (node:test, 17 tests) |

### 3.4 What was verified, and how

| Claim | Status |
|---|---|
| Channel contract, flags, dev-flag requirement, allowlist, Team/Enterprise `channelsEnabled`, Pro/Max skip org checks | [V] docs (§9) |
| Pair → channel → mocked Claude → `soul_reply` → fake SOUL (alarm, reminder, plain answer, invalid action filtered); print mode with mocked `claude -p`; "not signed in" → `claude_unavailable` | [R] `npm test` (17/17) and `npm run e2e` pass |
| Real **Claude Code 2.1.288** reads `~/SOUL-Claude/.mcp.json`, spawns `soul-bridge channel`, MCP handshake `connected`, tools exposed as `mcp__soul__soul_reply` / `mcp__soul__soul_status`, `--tools ""` leaves only those two tools, and the bridge connects and authenticates to the (fake) SOUL | [R] run in a scratch HOME in the build sandbox (`claude mcp list`; `system/init` of a `-p` run) |
| Until the folder is trusted interactively, Claude Code shows the server as "Pending approval" and ignores the project `permissions.allow` | [R] observed; that is why step 6 includes the trust dialog. We do **not** write Claude Code's own `~/.claude.json` to skip it |
| A pushed SOUL question actually appears in a signed-in **interactive** session and Claude calls `soul_reply` | **[U]** not tested: needs a real user account on a real machine (founder test, §7) |
| Windows/macOS launchers, `soul.local` resolution on Windows | [U] |

## 4. SOUL side: bridge protocol v1 (for the firmware and cloud builders)

Not built in firmware or cloud. The firmware agent is editing CloudLink now; this section is the contract to implement after that. JSON text frames over WebSocket, max 16 KB.

- **Transport, LAN (first):** SOUL listens on `ws://<hostname>.local:8765/bridge` and advertises mDNS `soul-xxxx.local` (+ `_soul._tcp` service, optional). Plain `ws://` is accepted by the bridge only for `.local`/private addresses.
- **Transport, cloud (later):** `wss://{BASE}/v1/bridge` with SOUL Cloud relaying frames to the device's existing WebSocket; lets the PC be on another network. Needs a new gateway route (not built).

| Direction | `t` | Fields |
|---|---|---|
| bridge → SOUL | `bridge.pair` | `v:1, code:"482913", bridge:"soul-bridge/0.1.0"` (code shown on SOUL's screen, 6 digits, valid 120 s, 5 tries) |
| SOUL → bridge | `bridge.paired` | `token:"sbt_<≥16 b64url>", device_id, name` |
| bridge → SOUL | `bridge.hello` | `v:1, token, bridge, mode:"channel"\|"print"` (first frame of every connection) |
| SOUL → bridge | `bridge.welcome` / `bridge.denied` | `device_id, name, lang, tz` / `reason` |
| SOUL → bridge | `ask` | `id:[A-Za-z0-9_.:-]{1,64}, text:1..2000, lang, now:"YYYY-MM-DDTHH:MM", tz, from:"touch"\|"keyboard"\|"voice"\|"phone"` |
| SOUL → bridge | `ask.cancel` | `id` |
| bridge → SOUL | `ask.ack` | `id, state:"thinking"` (SOUL shows thinking eyes) |
| bridge → SOUL | `answer` | `id, text:≤1200, actions:[{type, args}] ≤5` (same `args` as doc 07 §6.8) |
| bridge → SOUL | `answer.error` | `id, code:"timeout"\|"claude_unavailable"\|"busy"\|"bad_request", detail` |
| SOUL → bridge | `answer.ack` | `id, shown:bool` |

SOUL rules: store the token hash only; one active bridge per device (newest wins); revoke from *Settings › AI › Paired computers*; actions from the bridge are executed by the same dispatcher as any brain and shown with a "Claude (PC)" source badge; a new brain value `"bridge"` (doc 07 §0.2 list) routes the *Ask* button to the bridge when it is connected, else falls back to rules (E) with the message "Your computer is offline: open Start SOUL".

## 5. Route 2 · iPhone "Ask Claude" Shortcut

**Verified [V]:** Claude for iOS (iOS 18+) has the **Ask Claude** App Intent, usable "without launching the Claude app", and usable in Shortcuts, where you can "chain multiple 'Ask Claude' actions together … and process Claude's responses", i.e. the reply is the action's output. It uses the app's default model and "messages to Claude will count towards your overall usage limit." Apple's `shortcuts://run-shortcut?name=…&input=text&text=…` URL scheme runs a shortcut with text input [V]; personal automations on recent iOS can run without confirmation for triggers such as Email and Message [L: Apple's current list; older iOS versions differed].

**Recipe "SOUL → my Claude" (not built; needs two cloud endpoints and an iPhone to author the file):**

1. Cloud (not built): extend doc 07 §3.6 personal-token API with scopes `inbox.read` and `inbox.answer`: `GET /v1/pt/inbox?state=pending` → `[{id, text, lang, now}]`, `POST /v1/pt/inbox/{id}/answer {text, actions}` (same validation as `answer_soul`). Token `spt_…` is a SOUL token, entered once via an *Import Question* when installing the Shortcut, so the iCloud link itself carries no secret.
2. Shortcut "SOUL Questions": *Get Contents of URL* (GET inbox, header `Authorization: Bearer [token]`) → *Repeat with Each* item → **Ask Claude** with prompt "Answer briefly in [lang]. Reply ONLY as JSON {"text":…, "actions":[…]} … Question: [text]" → *Get Dictionary from Input* → *Get Contents of URL* (POST answer) → end repeat → *Show Notification* "SOUL: N answered".
3. Triggers, in order of reliability: the user taps the SOUL widget / says "Hey Siri, SOUL questions" / Action button; or SOUL Cloud sends a notification whose tap opens `shortcuts://run-shortcut?name=SOUL%20Questions`; or an **Email** personal automation ("from soul@…, subject contains SOUL question", Run Immediately) when the cloud emails on a new inbox item.
4. Share via iCloud link; SOUL's `/me` page shows the link and a 30-second video.

**Honest limits:** not real time and not hands-free unless the email automation runs unattended, which we have not tested [U]; whether Ask Claude completes while the phone is locked or inside an automation is [U]; JSON from a free-text prompt can fail, so the cloud must accept a plain-text answer without actions [E]. iPhone only (Android has no Claude App Intent equivalent [L]). Risk: low, it is the user's own app used as Anthropic designed it.

**Steps for the user (≈ 6):** open the iCloud link → *Add Shortcut* → paste the SOUL token from `/me` → allow network access to SOUL's domain the first time → (optional) create the email automation → tap/ask Siri when SOUL shows "waiting for your Claude (2)".

## 6. Policy risk, plainly

What we are sure of [V]: SOUL never touches Claude credentials, the user signs in through Anthropic's own flow, Claude Code runs unmodified on the user's own computer, usage is billed to the user's own plan. That keeps us out of every explicitly forbidden behaviour in §1.

Where it is ambiguous:

1. **Development flag.** Custom channels need `--dangerously-load-development-channels`, which the docs describe for testing your own channel locally; a channel in our own marketplace "still needs" that flag; the official allowlist is `claude-plugins-official`, reached "if you are working with an Anthropic partner contact" [V]. Shipping a consumer feature that depends on a dev flag is using it outside its stated purpose, and the flag syntax "may change" during the preview [V].
2. **"Rate limits for their products."** A hardware company whose device feature runs on the buyer's Pro/Max limits could be read as offering "rate limits for their products" (Agent SDK note) or "routing requests through … plan credentials on behalf of their users" (legal page). Our reading: the user is asking his own Claude, in his own session, through an official channel mechanism, just like texting it from the official Telegram plugin; that is individual use. Anthropic may read it differently. Print mode (1b) is closer to the line (the bridge, not the user, starts each Claude run) and the paused support-article change shows Anthropic thinks about "third-party apps that authenticate with your Claude subscription through the Agent SDK" as a separate category [V].
3. **Branding.** We may say "works with Claude Code" in plain text but may not use Claude Code's name/logo in our product name or imply endorsement [V]. Product name stays "SOUL Bridge".

How we minimise it:
- Open-source bridge (MIT), runs only on the user's machine; no SOUL server ever sees Claude traffic or credentials; tests assert no `--bare`, no token flags, and refuse to store Claude-looking secrets.
- Channel mode is the default; print mode is off, labelled "developer experiment, personal use", excluded from marketing.
- Built-in tools disabled in the SOUL session; no permission relay; sender gating on a SOUL-issued token.
- Marketing: nothing until Anthropic answers; then at most "SOUL can talk to your own Claude Code (Pro/Max) on your computer — experimental".
- **Ask first** (§7). If Anthropic says no, the bridge stays a community project and SOUL's supported paths remain doc 07 (own API key, connector).

## 7. Next actions

| Who | What |
|---|---|
| Founder | Add to the Anthropic partnership request: (a) list a SOUL channel plugin in `claude-plugins-official` (no dev flag); (b) written confirmation that a device vendor's open-source local channel, run by the user on his own Pro/Max login, is acceptable; (c) whether print mode is acceptable for personal use. |
| Founder | Run §3.1 on your own Mac/PC with your Pro/Max account and the fake SOUL: `npm install`, then in one terminal `node -e "import('./tools/fake-soul.js').then(async m=>{const s=new m.FakeSoul();await s.listen(8765);console.log(s.url);s.on('bridge',()=>setTimeout(()=>s.ask('Trezește-mă mâine la 7').then(a=>console.log(a)),3000))})"`, then `node bin/soul-bridge.js pair 482913 --soul ws://127.0.0.1:8765/bridge`, `node bin/soul-bridge.js setup`, start `~/SOUL-Claude/start-soul.sh`. Expect the alarm answer printed in the first terminal. |
| Firmware | After CloudLink: §4 endpoint, pairing screen, brain `"bridge"`, "Claude (PC)" badge. |
| Cloud | `/v1/bridge` relay (optional), `/v1/pt/inbox` read + answer scopes for route 2. |
| Bridge | Installer (bundled Node, signed, macOS/Windows), tray icon from `status.json`, auto-start at login, `_soul._tcp` discovery. |

## 8. Route 3 (complement): Claude → SOUL

Unchanged from doc 07 mode C: the SOUL connector (remote MCP + OAuth) lets the user's Claude on web, Desktop, iOS and Android put alarms, notes and cards on SOUL and answer SOUL's inbox when the user says "check my SOUL". It works on every plan and has the lowest risk, but it is the opposite direction: SOUL cannot start a conversation. A local MCP server in Claude Desktop (stdio, on the same computer) can do the same at home without SOUL Cloud; the bridge's `soul_status` tool is a seed for that, but a full local command set is not built.

## 9. Sources (read 3 Oct 2026)

- Claude Code channels: https://code.claude.com/docs/en/channels
- Channels reference (contract, dev flag, permission relay, plugin packaging): https://code.claude.com/docs/en/channels-reference
- MCP in Claude Code (channels and protocol revision 2026-07-28, `MCP_PROTOCOL_NEGOTIATION`): https://code.claude.com/docs/en/mcp
- Legal and compliance (authentication and credential use): https://code.claude.com/docs/en/legal-and-compliance
- Agent SDK overview (claude.ai login note, branding): https://code.claude.com/docs/en/agent-sdk/overview
- Run Claude Code programmatically (`-p`, `--bare` skips subscription login, `--json-schema`): https://code.claude.com/docs/en/headless
- CLI reference (`--tools`, `--allowedTools`, `--strict-mcp-config`, `--no-session-persistence`, `claude auth status`): https://code.claude.com/docs/en/cli-reference
- Claude Agent SDK and Claude plan usage (paused change): https://support.claude.com/en/articles/15036540
- Claude iOS App Intents, Shortcuts and widgets: https://support.claude.com/en/articles/10263469-use-claude-app-intents-shortcuts-and-widgets-on-ios
- Apple, run a shortcut from a URL: https://support.apple.com/guide/shortcuts/run-a-shortcut-from-a-url-apd624386f42/ios
- Apple, personal automations: https://support.apple.com/guide/shortcuts/intro-to-personal-automation-apd690170742/ios
