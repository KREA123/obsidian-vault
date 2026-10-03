import test from 'node:test'
import assert from 'node:assert/strict'
import { validateAction, validateActions, answerSchema, ACTIONS } from '../src/actions.js'

test('valid alarm gets defaults', () => {
  const r = validateAction({ type: 'alarm.set', args: { hhmm: '07:00' } })
  assert.deepEqual(r, { ok: true, action: { type: 'alarm.set', args: { hhmm: '07:00', days: [], label: '' } } })
})

test('bad formats and unknown things are rejected', () => {
  assert.equal(validateAction({ type: 'alarm.set', args: { hhmm: '25:00' } }).ok, false)
  assert.equal(validateAction({ type: 'alarm.set', args: { hhmm: '07:00', days: ['monday'] } }).ok, false)
  assert.equal(validateAction({ type: 'reminder.create', args: { when: '2026-10-03 18:00', text: 'x' } }).ok, false)
  assert.equal(validateAction({ type: 'timer.start', args: { seconds: 0 } }).ok, false)
  assert.equal(validateAction({ type: 'shell.run', args: {} }).ok, false)
  assert.equal(validateAction({ type: 'note.create', args: { text: 'a', evil: 1 } }).ok, false)
  assert.equal(validateAction(null).ok, false)
})

test('list keeps valid, reports invalid, caps count', () => {
  const many = Array.from({ length: 7 }, () => ({ type: 'note.create', args: { text: 'x' } }))
  const r = validateActions([{ type: 'alarm.set', args: { hhmm: '99:99' } }, ...many])
  assert.equal(r.ok.length, 4)
  assert.equal(r.rejected.length, 2)
  assert.deepEqual(validateActions(undefined), { ok: [], rejected: [] })
  assert.equal(validateActions('x').rejected.length, 1)
})

test('schema lists every action type', () => {
  const s = answerSchema({ withQuestionId: true })
  assert.deepEqual(s.required, ['question_id', 'text', 'actions'])
  assert.deepEqual(s.properties.actions.items.properties.type.enum, Object.keys(ACTIONS))
  assert.equal(answerSchema({ withQuestionId: false }).properties.question_id, undefined)
})
