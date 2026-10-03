// Bridge core: keeps track of questions from SOUL waiting for Claude's answer,
// validates answers and actions, and enforces timeouts. Shared by the channel
// mode (Claude Code channel) and the print mode (`claude -p`).
import { EventEmitter } from 'node:events'
import { msg, ERR } from './protocol.js'
import { validateActions, validateMemory, MAX_TEXT } from './actions.js'

export class BridgeCore extends EventEmitter {
  constructor({ link, timeoutMs = 120000, maxPending = 5 }) {
    super()
    this.link = link
    this.timeoutMs = timeoutMs
    this.maxPending = maxPending
    this.pending = new Map() // id -> {q, timer, at}
    this.stats = { asked: 0, answered: 0, timeouts: 0, last: null }
    link.on('ask', (q) => this._onAsk(q))
    link.on('cancel', (id) => this._drop(id))
  }

  _onAsk(q) {
    if (this.pending.has(q.id)) return // duplicate delivery
    if (this.pending.size >= this.maxPending) {
      this.link.send(msg.error(q.id, ERR.BUSY, 'too many questions waiting for Claude'))
      return
    }
    const timer = setTimeout(() => {
      if (!this.pending.has(q.id)) return
      this.pending.delete(q.id)
      this.stats.timeouts++
      this.link.send(msg.error(q.id, ERR.TIMEOUT, 'Claude did not answer in time'))
      this.emit('timeout', q)
    }, this.timeoutMs)
    timer.unref?.()
    this.pending.set(q.id, { q, timer, at: Date.now() })
    this.stats.asked++
    this.stats.last = new Date().toISOString()
    this.link.send(msg.ack(q.id))
    this.emit('question', q)
  }

  _drop(id) {
    const p = this.pending.get(id)
    if (p) { clearTimeout(p.timer); this.pending.delete(id) }
    return p
  }

  /**
   * Deliver Claude's answer to SOUL.
   * @returns {{ok:boolean, error?:string, sent_actions?:number, rejected?:Array}}
   */
  answer(id, text, actions, memory) {
    if (!this.pending.has(id)) return { ok: false, error: `no open question with id ${id} (already answered, cancelled or timed out)` }
    if (typeof text !== 'string' || !text.trim()) return { ok: false, error: 'text must be a non-empty string' }
    const v = validateActions(actions)
    const mem = validateMemory(memory)  // SOUL Memory ops: validated here, and again on SOUL
    const clean = text.trim().slice(0, MAX_TEXT)
    const sent = this.link.send(msg.answer(id, clean, v.ok, mem.ok))
    if (!sent) return { ok: false, error: 'SOUL is not connected right now; try again in a moment' }
    this._drop(id)
    this.stats.answered++
    this.emit('answered', { id, text: clean, actions: v.ok, memory: mem.ok, rejected: v.rejected.concat(mem.rejected) })
    return { ok: true, sent_actions: v.ok.length, rejected: v.rejected.concat(mem.rejected), sent_memory: mem.ok.length }
  }

  fail(id, code, detail) {
    if (!this._drop(id)) return false
    return this.link.send(msg.error(id, code, detail))
  }

  close() {
    for (const id of [...this.pending.keys()]) this._drop(id)
  }
}
