#!/usr/bin/env node
// SOUL Bridge CLI.
//   soul-bridge pair <code> [--cloud <host>] [--soul <address>]
//                         the code SOUL shows under Settings › AI › My Claude on my computer:
//                         8 characters (XXXX-XXXX) = through SOUL Cloud (--cloud, the host SOUL shows),
//                         6 digits = SOUL on this Wi-Fi (--soul <IP / soul-xxxx.local>, else found by mDNS)
//   soul-bridge setup [--desktop]               prepare ~/SOUL-Claude + launchers (+ a Desktop icon)
//   soul-bridge channel                          (started BY Claude Code) the SOUL channel server
//   soul-bridge print                            optional: answer via your own `claude -p`
//   soul-bridge status | status-page [--open] | doctor | discover
import fs from 'node:fs'
import os from 'node:os'
import { spawnSync } from 'node:child_process'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { SoulLink } from '../src/soul-link.js'
import { BridgeCore } from '../src/core.js'
import { createChannelServer } from '../src/channel.js'
import { runClaudePrint } from '../src/print-runner.js'
import { ERR, parseCode, cloudUrl, lanUrl } from '../src/protocol.js'
import * as config from '../src/config.js'
import { setup, workDir } from '../src/setup.js'
import { discoverSouls } from '../src/discover.js'
import { startStatusPage, openUrl, STATUS_PORT } from '../src/status-page.js'

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
  const upd = () => config.writeStatus({ mode, pid: process.pid, soul: link.state, device: link.device?.name ?? null, pending: core.pending.size, ...core.stats })
  link.on('state', upd); core.on('answered', upd); core.on('question', upd); core.on('timeout', upd)
  link.on('log', log); core.on('log', log)
  link.on('denied', (r) => { log(`SOUL refused this bridge (${r}). Pair again.`); upd() })
  upd()
}

async function main() {
  const cfg = config.load()
  switch (cmd) {
    case 'pair': {
      const c = parseCode(argv[1])
      if (!c) {
        console.log('usage: soul-bridge pair <code shown on SOUL> [--cloud <host>] [--soul <address>]\n' +
          '  XXXX-XXXX (8 characters): through SOUL Cloud, add --cloud <the host SOUL shows>\n' +
          '  123456 (6 digits): SOUL on this Wi-Fi, add --soul <the address SOUL shows> or let me find it')
        process.exit(1)
      }
      let url
      if (c.kind === 'cloud') {
        url = cloudUrl(opt('cloud', cfg.cloud))
      } else if (opt('soul')) {
        url = lanUrl(opt('soul'))
      } else {
        const found = await discoverSouls()
        if (found.length > 1) { console.log('Several SOULs answered; add --soul with the address on yours:\n' + found.map((f) => `  ${f.host} ${f.ip || ''}`).join('\n')); process.exit(1) }
        url = found.length ? found[0].url : (cfg.via === 'lan' && cfg.soul_url) || DEFAULT_SOUL
      }
      const r = await SoulLink.pair({ url, code: c.code })
      config.save({ ...cfg, soul_url: url, token: r.token, device_id: r.device_id, soul_name: r.name, via: c.kind,
        cloud: c.kind === 'cloud' ? opt('cloud', cfg.cloud) : cfg.cloud })
      console.log(`Paired with ${r.name}${c.kind === 'cloud' ? ' (through SOUL Cloud)' : ' (on this Wi-Fi)'}. Next: soul-bridge setup`)
      break
    }
    case 'discover': {
      const found = await discoverSouls({ timeoutMs: Number(opt('wait', 2000)) })
      console.log(found.length ? found.map((f) => `${f.host}\t${f.ip || '?'}\t${f.url}`).join('\n') : 'No SOUL answered. Is its brain "My Claude on my computer", on this Wi-Fi?')
      break
    }
    case 'status-page': {
      const port = Number(opt('port', STATUS_PORT))
      const url = `http://127.0.0.1:${port}/`
      try {
        await startStatusPage({ port })
        log(`status page: ${url}`)
      } catch (e) {
        if (e.code !== 'EADDRINUSE') throw e // already running (another Start SOUL window): just show it
        if (argv.includes('--open')) openUrl(url)
        process.exit(0)
      }
      if (argv.includes('--open')) openUrl(url)
      break
    }
    case 'setup': {
      const r = setup({ dir: opt('dir', workDir()), desktop: argv.includes('--desktop') })
      console.log(`Ready: ${r.dir}\nStart SOUL with: ${process.platform === 'win32' ? r.files.cmd : process.platform === 'darwin' ? r.files.command : r.files.sh}` +
        `${r.files.desktop ? `\n(and the Start SOUL icon on your Desktop)` : ''}\n` +
        `(first time: run \`claude\` once and sign in to YOUR Claude account yourself)\nStatus while it runs: http://127.0.0.1:${STATUS_PORT}/`)
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
          const r = await runClaudePrint(q, { claudeBin, model: cfg.model, timeoutMs: (cfg.timeout_s || 120) * 1000 - 5000, cwd: fs.existsSync(workDir()) ? workDir() : os.homedir() })
          if (r.ok) {
            const a = core.answer(q.id, r.text, r.actions, r.memory)
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
      console.log(`Paired with SOUL: ${cfg.token ? `yes (${cfg.soul_name || cfg.soul_url}, ${cfg.via === 'cloud' ? 'through SOUL Cloud' : 'on this Wi-Fi'})` : 'no - run soul-bridge pair <code>'}`)
      console.log(`Node.js: ${process.version}${Number(process.versions.node.split('.')[0]) >= 20 ? '' : ' (too old: SOUL Bridge needs 20+)'}`)
      console.log(`SOUL folder: ${workDir()}`)
      break
    }
    default:
      console.log('soul-bridge pair <code> [--cloud host | --soul address] | setup [--desktop] | channel | print | status | status-page [--open] | discover | doctor')
      process.exit(cmd ? 1 : 0)
  }
}

main().catch((e) => { log(e.message); process.exit(1) })
