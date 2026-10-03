// Pairing + channel server over real stdio/WebSocket, with a fake SOUL and a fake Claude Code.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { FakeSoul } from '../tools/fake-soul.js'
import { startFakeClaudeCode } from '../tools/fake-claude-code.js'
import { SoulLink } from '../src/soul-link.js'
import { setup, launchArgs } from '../src/setup.js'
import * as config from '../src/config.js'

test('pair, then questions flow SOUL -> channel -> Claude -> soul_reply -> SOUL', async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-'))
  process.env.SOUL_BRIDGE_HOME = home
  const soul = new FakeSoul()
  const url = await soul.listen()
  await assert.rejects(SoulLink.pair({ url, code: '000000' }), /wrong code/)
  const p = await SoulLink.pair({ url, code: soul.pairCode })
  config.save({ soul_url: url, token: p.token, soul_name: p.name })

  const cc = await startFakeClaudeCode({ env: { SOUL_BRIDGE_HOME: home } })
  assert.match(cc.instructions, /soul_reply/)
  const tools = (await cc.client.listTools()).tools.map((t) => t.name)
  assert.deepEqual(tools.sort(), ['soul_reply', 'soul_status'])
  await soul.waitBridge()
  const a = await soul.ask('Trezește-mă la 6:30')
  assert.equal(a.t, 'answer')
  assert.deepEqual(a.actions, [{ type: 'alarm.set', args: { hhmm: '06:30', days: [], label: '' } }])
  assert.deepEqual(Object.keys(cc.events[0].meta).every((k) => /^[A-Za-z0-9_]+$/.test(k)), true)

  // a reply for an unknown question is refused with a tool error
  const bad = await cc.client.callTool({ name: 'soul_reply', arguments: { question_id: 'nope', text: 'x', actions: [] } })
  assert.equal(bad.isError, true)
  await cc.close()
  await soul.close()
  fs.rmSync(home, { recursive: true, force: true })
})

test('unknown bridge token is denied', async () => {
  const soul = new FakeSoul()
  const url = await soul.listen()
  const link = new SoulLink({ url, token: 'sbt_' + 'x'.repeat(30), reconnect: false })
  const denied = new Promise((r) => link.once('denied', r))
  link.start()
  assert.equal(await denied, 'unknown bridge')
  link.close(); await soul.close()
})

test('config refuses Claude credentials; setup writes a locked-down folder', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-'))
  process.env.SOUL_BRIDGE_HOME = home
  assert.throws(() => config.save({ soul_url: 'ws://soul.local', token: 'sbt_abc', model: 'sk-ant-oat01-zzz' }), /Claude credential/)
  const saved = config.save({ soul_url: 'ws://soul.local', token: 'sbt_abcdefghijklmnopqrst', claude_token: 'x' })
  assert.equal(saved.claude_token, undefined)
  const r = setup({ dir: path.join(home, 'SOUL-Claude') })
  assert.equal(r.mcp.mcpServers.soul.args.at(-1), 'channel')
  assert.ok(r.settings.permissions.deny.includes('Bash'))
  const sh = fs.readFileSync(r.files.sh, 'utf8')
  assert.match(sh, /--dangerously-load-development-channels server:soul/)
  assert.match(sh, /--tools ""/)
  assert.ok(!/sk-ant|setup-token|CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY/.test(sh))
  assert.ok(launchArgs().includes('server:soul'))
  fs.rmSync(home, { recursive: true, force: true })
})
