#!/usr/bin/env node
// End-to-end demo with no real SOUL and no real Claude:
//   fake SOUL (WebSocket) -> soul-bridge -> mocked Claude -> answer + actions -> fake SOUL
// Runs both bridge modes: channel (what Claude Code would spawn) and print (`claude -p`).
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn, spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { FakeSoul } from './fake-soul.js'
import { startFakeClaudeCode } from './fake-claude-code.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const BIN = path.join(here, '..', 'bin', 'soul-bridge.js')
const home = fs.mkdtempSync(path.join(os.tmpdir(), 'soul-bridge-e2e-'))
const env = { SOUL_BRIDGE_HOME: home, SOUL_CLAUDE_DIR: path.join(home, 'SOUL-Claude') }
const show = (label, m) => console.log(`  ${label}: ${m.t === 'answer' ? JSON.stringify({ text: m.text, actions: m.actions }) : JSON.stringify(m)}`)
let failures = 0
const expect = (cond, what) => { if (!cond) { failures++; console.log(`  FAIL: ${what}`) } else console.log(`  ok: ${what}`) }

const soul = new FakeSoul()
const url = await soul.listen()
console.log(`fake SOUL listening on ${url} (pairing code ${soul.pairCode})`)

console.log('\n1. pairing (user types the code shown on SOUL)')
const pr = spawnSync(process.execPath, [BIN, 'pair', soul.pairCode, '--soul', url], { env: { ...process.env, ...env }, encoding: 'utf8' })
console.log('  ' + (pr.stdout || pr.stderr).trim())
const cfg = JSON.parse(fs.readFileSync(path.join(home, 'config.json'), 'utf8'))
expect(cfg.token?.startsWith('sbt_'), 'bridge token stored (SOUL token, not a Claude credential)')
expect((fs.statSync(path.join(home, 'config.json')).mode & 0o077) === 0 || process.platform === 'win32', 'config.json is private (0600)')

console.log('\n2. channel mode: (fake) Claude Code spawns `soul-bridge channel`')
const cc = await startFakeClaudeCode({ env })
expect(!!cc.caps.experimental['claude/channel'], 'server declares claude/channel')
expect(!cc.caps.experimental['claude/channel/permission'], 'no permission relay declared')
await soul.waitBridge()
for (const q of ['Trezește-mă mâine la 7', 'Amintește-mi să sun la bancă la 18:30', 'Cât e 12 x 12?', 'invalid action test']) {
  console.log(`  SOUL asks: ${q}`)
  const a = await soul.ask(q)
  show('SOUL got', a)
}
expect(soul.answers.size === 4, '4 answers delivered to SOUL')
const inv = [...soul.answers.values()].find((m) => m.text.startsWith('Test cu'))
expect(inv && inv.actions.length === 0, 'invalid action filtered before reaching SOUL')
console.log(`  channel event as Claude sees it: ${JSON.stringify(cc.events[0])}`)
await cc.close()
await new Promise((r) => setTimeout(r, 300))

console.log('\n3. print mode: bridge runs (fake) `claude -p` per question')
const fake = path.join(here, 'fake-claude.js')
const p = spawn(process.execPath, [BIN, 'print', '--claude', fake], { env: { ...process.env, ...env }, stdio: ['ignore', 'inherit', 'pipe'] })
p.stderr.on('data', () => {})
await soul.waitBridge()
const a1 = await soul.ask('Wake me at 6:45')
show('SOUL got', a1)
expect(a1.t === 'answer' && a1.actions[0]?.args.hhmm === '06:45', 'alarm 06:45 from print mode')
p.kill('SIGTERM')
await new Promise((r) => setTimeout(r, 300))

console.log('\n4. print mode, Claude Code not signed in')
const p2 = spawn(process.execPath, [BIN, 'print', '--claude', fake], { env: { ...process.env, ...env, FAKE_CLAUDE_FAIL: 'not_logged_in' }, stdio: ['ignore', 'inherit', 'pipe'] })
p2.stderr.on('data', () => {})
await soul.waitBridge()
const a2 = await soul.ask('Salut')
show('SOUL got', a2)
expect(a2.t === 'answer.error' && a2.code === 'claude_unavailable', 'SOUL told "Claude unavailable" (shows: open Claude Code and sign in)')
p2.kill('SIGTERM')

await soul.close()
fs.rmSync(home, { recursive: true, force: true })
console.log(failures ? `\n${failures} check(s) FAILED` : '\nALL END-TO-END CHECKS PASSED')
process.exit(failures ? 1 : 0)
