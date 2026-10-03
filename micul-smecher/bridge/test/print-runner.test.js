import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { buildArgs, parsePrintOutput, runClaudePrint } from '../src/print-runner.js'

const FAKE = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'tools', 'fake-claude.js')

test('args: own login (no --bare), no tools, no MCP, no saved session', () => {
  const a = buildArgs()
  assert.ok(!a.includes('--bare'))
  assert.equal(a[a.indexOf('--tools') + 1], '')
  for (const f of ['-p', '--strict-mcp-config', '--no-session-persistence', '--json-schema']) assert.ok(a.includes(f), f)
  assert.ok(!a.some((x) => /sk-ant|token/i.test(x)))
})

test('parse structured output, plain result, errors', () => {
  assert.deepEqual(parsePrintOutput(JSON.stringify({ subtype: 'success', is_error: false, structured_output: { text: 'a', actions: [] } }), 0),
    { ok: true, text: 'a', actions: [] })
  assert.equal(parsePrintOutput(JSON.stringify({ subtype: 'success', result: 'b' }), 0).text, 'b')
  assert.equal(parsePrintOutput(JSON.stringify({ is_error: true, result: 'Not logged in' }), 1).ok, false)
  assert.equal(parsePrintOutput('garbage', 1).ok, false)
})

test('runs the (mocked) claude binary', async () => {
  const r = await runClaudePrint({ text: 'Wake me at 7', lang: 'en', now: '2026-10-03T22:00' }, { claudeBin: FAKE })
  assert.equal(r.ok, true)
  assert.equal(r.actions[0].args.hhmm, '07:00')
  const missing = await runClaudePrint({ text: 'x', lang: 'en' }, { claudeBin: '/nonexistent/claude' })
  assert.equal(missing.ok, false)
})
