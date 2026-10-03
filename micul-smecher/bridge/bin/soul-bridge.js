#!/usr/bin/env node
// SOUL Bridge CLI.
//   soul-bridge pair <code> [--soul <ws-url>]   pair with the SOUL showing <code>
//   soul-bridge setup                            prepare ~/SOUL-Claude + launchers
//   soul-bridge channel                          (started BY Claude Code) the SOUL channel server
//   soul-bridge print                            optional: answer via your own `claude -p`
//   soul-bridge status | doctor
import { spawnSync } from 'node:child_process'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { SoulLink } from '../src/soul-link.js'
import { BridgeCore } from '../src/core.js'
import { createChannelServer } from '../src/channel.js'
import { runClaudePrint } from '../src/print-runner.js'
import { ERR } from '../src/protocol.js'
import * as config from '../src/config.js'
import { setup, workDir } from '../src/setup.js'

const DEFAULT_SOUL = 'ws://soul.local:8765/bridge'
const argv = process.argv.slice(2)
const cmd = argv[0]
const opt = (name, dflt) => { const i = argv.indexOf(`--${name}`); return i > 0 && argv[i + 1] !== undefined ? argv[i + 1] : dflt }
// In channel mode stdout belongs to MCP: log to stderr only.
const log = (...a) => console.error('[soul-bridge]', ...a)

function needPaired(cfg) {
  if (!cfg.soul_url || !cfg.token) { log('not paired yet: run `soul-bridge pair <code shown on SOUL>`'); process.exit(2) }
}

function wireStatus(link, core, mode) {
  const upd = () => config.writeStatus({ mode, soul: link.state, device: link.device?.name ?? null, pending: core.pending.size, ...core.stats })
  link.on('state', upd); core.on('answered', upd); core.on('question', upd); core.on('timeout', upd)
  link.on('log', log); core.on('log', log)
  link.on('denied', (r) => { log(`SOUL refused this bridge (${r}). Pair again.`); upd() })
  upd()
}

async function main() {
  const cfg = config.load()
  switch (cmd) {
    case 'pair': {
      const code = argv[1]
      if (!code || !/^\d{4,8}$/.test(code)) { console.log('usage: soul-bridge pair <code shown on SOUL> [--soul ws://soul-xxxx.local:8765/bridge]'); process.exit(1) }
      const url = opt('soul', cfg.soul_url || DEFAULT_SOUL)
      const r = await SoulLink.pair({ url, code })
      config.save({ ...cfg, soul_url: url, token: r.token, device_id: r.device_id, soul_name: r.name })
      console.log(`Paired with ${r.name}. Next: soul-bridge setup`)
      break
    }
    case 'setup': {
      const r = setup({ dir: opt('dir', workDir()) })
      console.log(`Ready: ${r.dir}\nStart SOUL with: ${process.platform === 'win32' ? r.files.cmd : process.platform === 'darwin' ? r.files.command : r.files.sh}\n(first time: run \`claude\` once and sign in to YOUR Claude account yourself)`)
      break
    }
    case 'channel': {
      needPaired(cfg)
      const link = new SoulLink({ url: cfg.soul_url, token: cfg.token, mode: 'channel' })
      const core = new BridgeCore({ link, timeoutMs: (cfg.timeout_s || 120) * 1000 })
      wireStatus(link, core, 'channel')
      const mcp = createChannelServer({ core, link })
      await mcp.connect(new StdioServerTransport())
      link.start()
      const stop = () => { link.close(); core.close(); config.writeStatus({ mode: 'channel', soul: 'closed' }); process.exit(0) }
      process.stdin.on('end', stop) // Claude Code closed the session
      process.on('SIGTERM', stop); process.on('SIGINT', stop)
      break
    }
    case 'print': {
      needPaired(cfg)
      const claudeBin = opt('claude', process.env.SOUL_BRIDGE_CLAUDE || 'claude')
      const link = new SoulLink({ url: cfg.soul_url, token: cfg.token, mode: 'print' })
      const core = new BridgeCore({ link, timeoutMs: (cfg.timeout_s || 120) * 1000, maxPending: 3 })
      wireStatus(link, core, 'print')
      let chain = Promise.resolve() // one question at a time
      core.on('question', (q) => {
        chain = chain.then(async () => {
          const r = await runClaudePrint(q, { claudeBin, model: cfg.model, timeoutMs: (cfg.timeout_s || 120) * 1000 - 5000, cwd: workDir() })
          if (r.ok) {
            const a = core.answer(q.id, r.text, r.actions)
            if (!a.ok) log(`answer not delivered: ${a.error}`)
          } else {
            log(`claude -p failed: ${r.error}`)
            core.fail(q.id, r.error === 'timeout' ? ERR.TIMEOUT : ERR.CLAUDE_UNAVAILABLE, r.error)
          }
        })
      })
      link.start()
      log(`print mode: waiting for questions from ${cfg.soul_name || 'SOUL'} (Ctrl+C to stop)`)
      break
    }
    case 'status': {
      const st = config.readStatus()
      console.log(JSON.stringify({ paired: !!cfg.token, soul: cfg.soul_name || null, url: cfg.soul_url || null, status: st }, null, 2))
      break
    }
    case 'doctor': {
      const v = spawnSync('claude', ['--version'], { encoding: 'utf8' })
      console.log(`Claude Code: ${v.status === 0 ? v.stdout.trim() : 'NOT FOUND - install from https://code.claude.com'}`)
      // `claude auth status` prints JSON about the sign-in; we only read authMethod, never any token.
      const a = spawnSync('claude', ['auth', 'status'], { encoding: 'utf8' })
      let method = 'unknown'
      try { method = JSON.parse(a.stdout).authMethod } catch {}
      console.log(`Signed in: ${a.status === 0 ? `yes (${method})` : 'no - run `claude` and sign in to your own Claude account'}`)
      console.log(`Paired with SOUL: ${cfg.token ? `yes (${cfg.soul_name || cfg.soul_url})` : 'no - run soul-bridge pair <code>'}`)
      console.log(`SOUL folder: ${workDir()}`)
      break
    }
    default:
      console.log('soul-bridge pair <code> [--soul url] | setup | channel | print | status | doctor')
      process.exit(cmd ? 1 : 0)
  }
}

main().catch((e) => { log(e.message); process.exit(1) })
