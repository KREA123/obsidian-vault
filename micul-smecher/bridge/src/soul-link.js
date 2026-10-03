// Outbound WebSocket link from the bridge to SOUL (LAN) or SOUL Cloud.
import { EventEmitter } from 'node:events'
import WebSocket from 'ws'
import { msg, parseFromSoul, checkSoulUrl, MAX_FRAME } from './protocol.js'

export const BRIDGE_ID = 'soul-bridge/0.1.0'

export class SoulLink extends EventEmitter {
  /**
   * @param {object} o
   * @param {string} o.url      ws://soul-xxxx.local:8765/bridge or wss://<cloud>/v1/bridge
   * @param {string} [o.token]  bridge token from pairing (sbt_...)
   * @param {string} [o.mode]   'channel' | 'print'
   * @param {boolean} [o.reconnect=true]
   */
  constructor({ url, token, mode = 'channel', reconnect = true, backoffMs = [1000, 2000, 5000, 10000, 30000] }) {
    super()
    const c = checkSoulUrl(url)
    if (!c.ok) throw new Error(c.error)
    this.url = url
    this.token = token
    this.mode = mode
    this.reconnect = reconnect
    this.backoffMs = backoffMs
    this.attempt = 0
    this.ws = null
    this.state = 'idle' // idle | connecting | ready | closed
    this.device = null
    this._closed = false
  }

  /** One-shot pairing: send the code shown on SOUL, resolve with {token, device_id, name}. */
  static pair({ url, code, timeoutMs = 15000 }) {
    const c = checkSoulUrl(url)
    if (!c.ok) return Promise.reject(new Error(c.error))
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(url, { maxPayload: MAX_FRAME })
      const t = setTimeout(() => { ws.terminate(); reject(new Error('pairing timed out')) }, timeoutMs)
      ws.on('open', () => ws.send(JSON.stringify(msg.pair(code, BRIDGE_ID))))
      ws.on('message', (raw) => {
        const p = parseFromSoul(raw)
        if (!p.ok) return
        if (p.msg.t === 'bridge.paired') { clearTimeout(t); ws.close(); resolve(p.msg) }
        if (p.msg.t === 'bridge.denied') { clearTimeout(t); ws.close(); reject(new Error(`SOUL refused: ${p.msg.reason}`)) }
      })
      ws.on('error', (e) => { clearTimeout(t); reject(e) })
    })
  }

  start() {
    this._closed = false
    this._connect()
    return this
  }

  _connect() {
    if (this._closed) return
    this.state = 'connecting'
    this.emit('state', this.state)
    const ws = new WebSocket(this.url, { maxPayload: MAX_FRAME })
    this.ws = ws
    ws.on('open', () => ws.send(JSON.stringify(msg.hello(this.token, BRIDGE_ID, this.mode))))
    ws.on('message', (raw) => this._onMessage(raw))
    ws.on('close', () => this._onClose())
    ws.on('error', (e) => this.emit('log', `link error: ${e.message}`))
  }

  _onMessage(raw) {
    const p = parseFromSoul(raw)
    if (!p.ok) { this.emit('log', `dropped frame from SOUL: ${p.error}`); return }
    const m = p.msg
    if (m.t === 'bridge.welcome') {
      this.attempt = 0
      this.device = m
      this.state = 'ready'
      this.emit('state', this.state)
      this.emit('ready', m)
    } else if (m.t === 'bridge.denied') {
      this.emit('denied', m.reason)
      this.close()
    } else if (this.state !== 'ready') {
      this.emit('log', `ignored ${m.t} before welcome`)
    } else if (m.t === 'ask') {
      this.emit('ask', m)
    } else if (m.t === 'ask.cancel') {
      this.emit('cancel', m.id)
    } else if (m.t === 'answer.ack') {
      this.emit('answerAck', m)
    }
  }

  _onClose() {
    const was = this.state
    this.state = this._closed ? 'closed' : 'connecting'
    if (was !== this.state) this.emit('state', this.state)
    if (this._closed || !this.reconnect) { this.state = 'closed'; return }
    const d = this.backoffMs[Math.min(this.attempt++, this.backoffMs.length - 1)]
    this._timer = setTimeout(() => this._connect(), d)
  }

  send(obj) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN || this.state !== 'ready') return false
    this.ws.send(JSON.stringify(obj))
    return true
  }

  close() {
    this._closed = true
    clearTimeout(this._timer)
    this.state = 'closed'
    if (this.ws) try { this.ws.close() } catch {}
  }
}
