// Wire protocol between SOUL Bridge (on the user's computer) and SOUL
// (the device on the LAN, or SOUL Cloud relaying to it). JSON text frames over
// WebSocket. Version 1. Normative description: docs/08-OWN-CLAUDE.md §4.
//
// Nothing in this protocol carries a Claude credential. The only secret is the
// bridge token SOUL issues at pairing (prefix "sbt_"), which authorises this
// bridge to talk to that SOUL and nothing else.

export const PROTOCOL_VERSION = 1
export const MAX_FRAME = 16 * 1024
export const MAX_QUESTION = 2000

export const msg = {
  pair: (code, bridge) => ({ t: 'bridge.pair', v: PROTOCOL_VERSION, code: String(code), bridge }),
  hello: (token, bridge, mode) => ({ t: 'bridge.hello', v: PROTOCOL_VERSION, token, bridge, mode }),
  ack: (id) => ({ t: 'ask.ack', id, state: 'thinking' }),
  answer: (id, text, actions) => ({ t: 'answer', id, text, actions }),
  error: (id, code, detail = '') => ({ t: 'answer.error', id, code, detail: String(detail).slice(0, 200) }),
  status: (state, detail = '') => ({ t: 'bridge.status', state, detail: String(detail).slice(0, 200) }),
}

// Error codes the bridge sends in answer.error
export const ERR = {
  TIMEOUT: 'timeout', // Claude did not answer in time
  CLAUDE_UNAVAILABLE: 'claude_unavailable', // Claude Code not running / not signed in / limit reached
  BUSY: 'busy', // too many questions waiting
  BAD_REQUEST: 'bad_request',
}

const ID = /^[A-Za-z0-9_.:-]{1,64}$/

/** Parse and validate a frame received from SOUL. Returns {ok, msg} or {ok:false, error}. */
export function parseFromSoul(raw) {
  const s = typeof raw === 'string' ? raw : Buffer.isBuffer(raw) ? raw.toString('utf8') : String(raw)
  if (s.length > MAX_FRAME) return { ok: false, error: 'frame too large' }
  let m
  try { m = JSON.parse(s) } catch { return { ok: false, error: 'not json' } }
  if (!m || typeof m !== 'object' || typeof m.t !== 'string') return { ok: false, error: 'no type' }
  switch (m.t) {
    case 'bridge.welcome':
      return { ok: true, msg: {
        t: m.t,
        device_id: str(m.device_id, 64),
        name: str(m.name, 60) || 'SOUL',
        lang: str(m.lang, 8) || 'en',
        tz: str(m.tz, 64),
      } }
    case 'bridge.paired':
      if (typeof m.token !== 'string' || !/^sbt_[A-Za-z0-9_-]{16,128}$/.test(m.token)) return { ok: false, error: 'bad token' }
      return { ok: true, msg: { t: m.t, token: m.token, device_id: str(m.device_id, 64), name: str(m.name, 60) || 'SOUL' } }
    case 'bridge.denied':
      return { ok: true, msg: { t: m.t, reason: str(m.reason, 120) || 'denied' } }
    case 'ask': {
      if (typeof m.id !== 'string' || !ID.test(m.id)) return { ok: false, error: 'bad id' }
      if (typeof m.text !== 'string' || !m.text.trim()) return { ok: false, error: 'empty question' }
      if (m.text.length > MAX_QUESTION) return { ok: false, error: 'question too long' }
      return { ok: true, msg: {
        t: 'ask', id: m.id, text: m.text.trim(),
        lang: str(m.lang, 8) || 'en',
        now: str(m.now, 25),
        tz: str(m.tz, 64),
        from: ['touch', 'keyboard', 'voice', 'phone'].includes(m.from) ? m.from : 'touch',
      } }
    }
    case 'ask.cancel':
      if (typeof m.id !== 'string' || !ID.test(m.id)) return { ok: false, error: 'bad id' }
      return { ok: true, msg: { t: m.t, id: m.id } }
    case 'answer.ack':
      return { ok: true, msg: { t: m.t, id: str(m.id, 64), shown: !!m.shown } }
    default:
      return { ok: false, error: `unknown type ${m.t.slice(0, 32)}` }
  }
}

function str(v, max) {
  return typeof v === 'string' ? v.slice(0, max) : ''
}

/** Accept wss:// anywhere, ws:// only for the local network (SOUL on the LAN). */
export function checkSoulUrl(u) {
  let url
  try { url = new URL(u) } catch { return { ok: false, error: 'not a URL' } }
  if (url.protocol === 'wss:') return { ok: true }
  if (url.protocol !== 'ws:') return { ok: false, error: 'use ws:// (home network) or wss://' }
  const h = url.hostname
  const local = h.endsWith('.local') || h === 'localhost' || h === '127.0.0.1' || h === '[::1]' ||
    /^10\./.test(h) || /^192\.168\./.test(h) || /^172\.(1[6-9]|2\d|3[01])\./.test(h) || /^169\.254\./.test(h)
  return local ? { ok: true } : { ok: false, error: 'plain ws:// is only allowed on the home network; use wss://' }
}
