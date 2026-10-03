import test from 'node:test'
import assert from 'node:assert/strict'
import { parseFromSoul, checkSoulUrl, MAX_FRAME } from '../src/protocol.js'

test('ask is validated and normalized', () => {
  const r = parseFromSoul(JSON.stringify({ t: 'ask', id: 'q_1', text: '  hi ', lang: 'ro', from: 'weird' }))
  assert.equal(r.ok, true)
  assert.equal(r.msg.text, 'hi')
  assert.equal(r.msg.from, 'touch')
})

test('bad frames are dropped', () => {
  assert.equal(parseFromSoul('nope').ok, false)
  assert.equal(parseFromSoul(JSON.stringify({ t: 'ask', id: 'bad id!', text: 'x' })).ok, false)
  assert.equal(parseFromSoul(JSON.stringify({ t: 'ask', id: 'q', text: '' })).ok, false)
  assert.equal(parseFromSoul(JSON.stringify({ t: 'ask', id: 'q', text: 'x'.repeat(2001) })).ok, false)
  assert.equal(parseFromSoul('x'.repeat(MAX_FRAME + 1)).ok, false)
  assert.equal(parseFromSoul(JSON.stringify({ t: 'bridge.paired', token: 'sk-ant-oat01-xxxxxxxxxxxxxxxxxxxx' })).ok, false)
  assert.equal(parseFromSoul(JSON.stringify({ t: 'run.shell' })).ok, false)
})

test('plain ws only on the home network', () => {
  assert.equal(checkSoulUrl('ws://soul-a1b2.local:8765/bridge').ok, true)
  assert.equal(checkSoulUrl('ws://192.168.1.40:8765/bridge').ok, true)
  assert.equal(checkSoulUrl('wss://cloud.example.com/v1/bridge').ok, true)
  assert.equal(checkSoulUrl('ws://cloud.example.com/v1/bridge').ok, false)
  assert.equal(checkSoulUrl('http://192.168.1.40').ok, false)
})
