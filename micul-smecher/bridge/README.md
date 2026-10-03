# SOUL Bridge

Ask SOUL something, and **your own Claude Code** answers — the official Claude Code from Anthropic, installed on
your computer and signed in by you. SOUL Bridge is the small open-source program that carries the question from
SOUL to that Claude Code session (as a Claude Code *channel*) and the answer back, with any alarm, reminder, timer
or note it asked SOUL to set. Design, policy and limits: [`../docs/08-OWN-CLAUDE.md`](../docs/08-OWN-CLAUDE.md).

**SOUL Bridge never sees a Claude password, token or key.** Claude Code signs in by itself through Anthropic's own
flow; the only secret SOUL Bridge keeps is the bridge token SOUL issued when you paired (`sbt_…`, in
`~/.soul-bridge/config.json`, mode 0600), which lets this computer answer that SOUL and nothing more.

> Experimental. Custom channels are a Claude Code research preview and still need
> `--dangerously-load-development-channels`; Pro/Max plan; the computer must be on with the Start SOUL window
> open. Nothing here has been tried with a signed-in Claude account by us yet (docs/08 §3.4).

## Install (about 5 minutes, once)

1. **Node.js 20 or newer** — <https://nodejs.org> (the LTS installer, macOS / Windows / Linux).
2. **Claude Code** — <https://code.claude.com>. Then open a terminal, run `claude` once and sign in to *your own*
   Claude account (Pro or Max). Close it.
3. **SOUL Bridge**:

   ```bash
   npm install -g soul-bridge          # once it is on npm
   npm install -g ./soul-bridge-0.2.0.tgz   # meanwhile: from a release tarball (made with `npm pack` in bridge/)
   ```

4. **Pair with your SOUL.** On SOUL: *Settings › AI › My Claude on my computer*. SOUL shows the command to type:

   ```bash
   soul-bridge pair 7KQ3-M9XD --cloud soul.example   # through SOUL Cloud: works from any network
   soul-bridge pair 482913                           # on the same Wi-Fi: SOUL is found by mDNS (or add --soul <IP>)
   ```

   The 8-character code comes from SOUL Cloud (SOUL must be paired with your account; the account page `/me`
   can also make one: *Pair a computer*). The 6-digit code is SOUL's own, on your home network, no cloud involved.
   Codes work once, for a few minutes.

5. **Set up the SOUL folder**: `soul-bridge setup` (add `--desktop` for a Start SOUL icon on the Desktop). It
   creates `~/SOUL-Claude` with a locked-down Claude Code project (no shell, no files, only the reply tool) and the
   launchers: `Start SOUL.command` (macOS), `Start SOUL.cmd` (Windows), `start-soul.sh` (Linux).

## Every day

Double-click **Start SOUL**. The first time, Claude Code asks you to trust the folder, to use the `soul` MCP
server and to confirm the development channel: answer yes. Keep the window open. A status page opens at
<http://127.0.0.1:8766> (this computer only): green when SOUL is connected, with how many questions were answered.
SOUL shows "connected · <your computer>" in *Settings › AI*, its eyes wait while the question travels and think
while Claude answers; when the computer is off SOUL says so and answers simple things (alarms, timers) itself.

## Commands

| | |
|---|---|
| `soul-bridge pair <code> [--cloud host] [--soul address]` | pair with the SOUL showing `<code>` |
| `soul-bridge setup [--desktop]` | the `~/SOUL-Claude` folder and launchers |
| `soul-bridge status` / `status-page [--open]` | what the bridge is doing (JSON / the local page) |
| `soul-bridge discover` | the SOULs on this Wi-Fi that listen for a bridge |
| `soul-bridge doctor` | Node, Claude Code installed and signed in (only the method, never a token), paired |
| `soul-bridge channel` | started by Claude Code itself (from `.mcp.json`), not by you |
| `soul-bridge print` | developer experiment: answers through your own `claude -p`, off by default (docs/08 §6) |

To forget this computer: on SOUL (*My Claude on my computer › Forget*) or on the account page (*Forget* next to
the computer). The token stops working at once.

## Develop

```bash
npm install
npm test          # 23 tests (node:test): protocol, core, actions, print mode, channel e2e with a fake SOUL
                  # and a mocked Claude Code, cloud + LAN pairing, mDNS, the status page, the launchers
npm run e2e       # fake SOUL -> soul-bridge -> mocked Claude Code / mocked `claude -p` -> answer
```

The full chain with the firmware simulator and the real cloud: `../ai/tools/e2e_bridge.py` (step 4 of
`../ai/tools/e2e_demo.sh`). No test ever calls a model or touches a Claude account. The launchers pass ShellCheck
(`shellcheck -s sh start-soul.sh`); the Windows `.cmd` is checked by the tests (CRLF, `call`, `pause`, UTF-8).
