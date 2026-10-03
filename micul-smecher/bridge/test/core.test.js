import test from 'node:test'
import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { BridgeCore } from '../src/core.js'

class FakeLink extends EventEmitter {
  constructor() { super(); this.sent = []; this.up = true; this.state = 'ready' }
  send(m) { if (!this.up) return false; this.sent.push(m); return true }
}
const q = (id, text = 'hi') => ({ t: 'ask', id, text, lang: 'en', from: 'touch' })

test('ack, answer once, then refuse duplicates', () => {
  const link = new FakeLink(); const core = new BridgeCore({ link })
  link.emit('ask', q('a'))
  assert.equal(link.sent[0].t, 'ask.ack')
  const r = core.answer('a', 'hello', [{ type: 'timer.start', args: { seconds: 60 } }, { type: 'nope', args: {} }])
  assert.equal(r.ok, true); assert.equal(r.sent_actions, 1); assert.equal(r.rejected.length, 1)
  assert.equal(link.sent[1].t, 'answer')
  assert.equal(core.answer('a', 'again').ok, false)
  core.close()
})

test('timeout sends answer.error', async () => {
  const link = new FakeLink(); const core = new BridgeCore({ link, timeoutMs: 30 })
  link.emit('ask', q('b'))
  await new Promise((r) => setTimeout(r, 60))
  assert.equal(link.sent.at(-1).t, 'answer.error')
  assert.equal(link.sent.at(-1).code, 'timeout')
  assert.equal(core.pending.size, 0)
})

test('busy when too many pending; cancel drops', () => {
  const link = new FakeLink(); const core = new BridgeCore({ link, maxPending: 1 })
  link.emit('ask', q('c')); link.emit('ask', q('d'))
  assert.equal(link.sent.at(-1).code, 'busy')
  link.emit('cancel', 'c')
  assert.equal(core.pending.size, 0)
  core.close()
})

test('answer kept pending while SOUL is offline', () => {
  const link = new FakeLink(); const core = new BridgeCore({ link })
  link.emit('ask', q('e')); link.up = false
  assert.equal(core.answer('e', 'x').ok, false)
  assert.equal(core.pending.size, 1)
  link.up = true
  assert.equal(core.answer('e', 'x').ok, true)
  core.close()
})
