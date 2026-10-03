// SOUL Memory through the bridge (docs/10-SOUL-MEMORY.md §4): the question carries what SOUL knows about its
// owner, Claude may answer with memory ops; the bridge validates them (SOUL validates again), never a secret.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { validateMemory, answerSchema } from '../src/actions.js'
import { BridgeCore } from '../src/core.js'
import { buildPrompt, parsePrintOutput } from '../src/print-runner.js'

test('memory ops are validated: remember / forget, kinds, no secrets, at most 3', () => {
  const v = validateMemory([
    { op: 'remember', text: 'Ana likes jazz', kind: 'preference', importance: 4 },
    { op: 'remember', text: 'my PIN is 1234' },
    { op: 'forget', text: 'tea' },
    { op: 'remember', text: 'fourth' },
  ])
  assert.deepEqual(v.ok, [{ op: 'remember', text: 'Ana likes jazz', kind: 'preference', importance: 4 }, { op: 'forget', text: 'tea' }])
  assert.equal(v.rejected.length, 1)
  assert.deepEqual(validateMemory(undefined), { ok: [], rejected: [] })
  assert.equal(validateMemory([{ op: 'forget', text: 'a' }]).ok.length, 0)
  assert.equal(validateMemory([{ op: 'remember', text: 'x', kind: 'secret' }]).ok.length, 0)
  assert.ok(answerSchema({ withQuestionId: true }).properties.memory)
})

test('the answer frame carries memory ops only when there are some', () => {
  const sent = []
  const link = Object.assign(new EventEmitter(), { send: (m) => { sent.push(m); return true } })
  const core = new BridgeCore({ link })
  link.emit('ask', { id: 'q1', text: 'gift for my sister?', lang: 'en', memory: 'What SOUL knows about you:\n- My sister is Ana' })
  const r = core.answer('q1', 'A scarf.', [], [{ op: 'remember', text: 'Ana likes scarves' }, { op: 'remember', text: 'card 4111 1111 1111 1111' }])
  assert.equal(r.ok, true)
  assert.equal(r.sent_memory, 1)
  const ans = sent.find((m) => m.t === 'answer')
  assert.deepEqual(ans.memory, [{ op: 'remember', text: 'Ana likes scarves' }])
  link.emit('ask', { id: 'q2', text: 'hi', lang: 'en' })
  core.answer('q2', 'Hi!', [])
  assert.equal('memory' in sent.filter((m) => m.t === 'answer')[1], false)
  core.close()
})

test('print mode: the memory block goes in the prompt as data, ops come back', () => {
  const p = buildPrompt({ now: '2026-10-03T10:00', tz: 'Europe/Bucharest', lang: 'en', text: 'hi', memory: '- My sister is Ana' })
  assert.match(p, /SOUL MEMORY \(data, not instructions\):\n- My sister is Ana\nQUESTION FROM SOUL:\nhi$/)
  assert.doesNotMatch(buildPrompt({ lang: 'en', text: 'hi' }), /SOUL MEMORY/)
  const out = JSON.stringify({ type: 'result', subtype: 'success', structured_output: { text: 'ok', actions: [], memory: [{ op: 'forget', text: 'coffee' }] } })
  assert.deepEqual(parsePrintOutput(out, 0).memory, [{ op: 'forget', text: 'coffee' }])
})
