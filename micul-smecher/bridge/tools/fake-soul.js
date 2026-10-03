// A fake SOUL device speaking the bridge protocol (server side), for tests and
// the end-to-end demo. The real SOUL (firmware) / SOUL Cloud must implement the
// same frames: docs/08-OWN-CLAUDE.md §4.
import { EventEmitter } from 'node:events'
import crypto from 'node:crypto'
import { WebSocketServer } from 'ws'

export class FakeSoul extends EventEmitter {
  constructor({ name = 'SOUL de test', deviceId = 'soul-a1b2c3', lang = 'ro', tz = 'Europe/Bucharest', pairCode = '482913' } = {}) {
    super()
    Object.assign(this, { name, deviceId, lang, tz, pairCode })
    this.tokens = new Set()
    this.bridge = null
    this.answers = new Map()
  }

  async listen(port = 0) {
    this.wss = new WebSocketServer({ host: '127.0.0.1', port, maxPayload: 16384 })
    await new Promise((r) => this.wss.on('listening', r))
    this.url = `ws://127.0.0.1:${this.wss.address().port}/bridge`
    this.wss.on('connection', (ws) => {
      ws.on('message', (raw) => {
        let m
        try { m = JSON.parse(raw) } catch { return }
        this.emit('frame', m)
        if (m.t === 'bridge.pair') {
          if (m.code !== this.pairCode) return ws.send(JSON.stringify({ t: 'bridge.denied', reason: 'wrong code' }))
          const token = 'sbt_' + crypto.randomBytes(24).toString('base64url')
          this.tokens.add(token)
          ws.send(JSON.stringify({ t: 'bridge.paired', token, device_id: this.deviceId, name: this.name }))
        } else if (m.t === 'bridge.hello') {
          if (!this.tokens.has(m.token)) { ws.send(JSON.stringify({ t: 'bridge.denied', reason: 'unknown bridge' })); return ws.close() }
          this.bridge = ws
          ws.send(JSON.stringify({ t: 'bridge.welcome', device_id: this.deviceId, name: this.name, lang: this.lang, tz: this.tz }))
          this.emit('bridge', m)
        } else if (ws === this.bridge && (m.t === 'answer' || m.t === 'answer.error' || m.t === 'ask.ack')) {
          if (m.t !== 'ask.ack') {
            this.answers.set(m.id, m)
            ws.send(JSON.stringify({ t: 'answer.ack', id: m.id, shown: true }))
          }
          this.emit(m.t, m)
        }
      })
      ws.on('close', () => { if (ws === this.bridge) { this.bridge = null; this.emit('bridge.gone') } })
    })
    return this.url
  }

  /** Simulate the user typing a question on SOUL. Resolves with the bridge's answer frame. */
  ask(text, { id = 'q_' + crypto.randomBytes(4).toString('hex'), now = '2026-10-03T18:02', timeoutMs = 10000 } = {}) {
    if (!this.bridge) return Promise.reject(new Error('no bridge connected'))
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error('no answer')), timeoutMs)
      const on = (m) => { if (m.id === id) { clearTimeout(t); this.off('answer', on); this.off('answer.error', on); resolve(m) } }
      this.on('answer', on); this.on('answer.error', on)
      this.bridge.send(JSON.stringify({ t: 'ask', id, text, lang: this.lang, now, tz: this.tz, from: 'keyboard' }))
    })
  }

  waitBridge(timeoutMs = 10000) {
    if (this.bridge) return Promise.resolve()
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error('bridge did not connect')), timeoutMs)
      this.once('bridge', () => { clearTimeout(t); resolve() })
    })
  }

  close() { for (const c of this.wss?.clients ?? []) c.terminate(); return new Promise((r) => this.wss ? this.wss.close(() => r()) : r()) }
}
