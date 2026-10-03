// Finds SOULs on this Wi-Fi with one mDNS question (RFC 6762): PTR _soul._tcp.local. Each SOUL whose brain is
// "My Claude on my computer" answers as soul-xxxx.local, port 8765 (firmware/src/bridge_lan.cpp). No library:
// a 40-line DNS reader over node:dgram. Used by `soul-bridge pair <6 digits>` when no --soul is given.
import dgram from 'node:dgram'

const MDNS = { address: '224.0.0.251', port: 5353 }
export const SERVICE = '_soul._tcp.local'

export function encodeName(name) {
  const parts = name.split('.').filter(Boolean)
  const out = []
  for (const p of parts) {
    const b = Buffer.from(p, 'utf8')
    out.push(Buffer.from([b.length]), b)
  }
  out.push(Buffer.from([0]))
  return Buffer.concat(out)
}

/** A one-question mDNS query (QU bit set: answer by unicast, so no multicast listener is needed). */
export function query(name = SERVICE, type = 12) {
  const head = Buffer.alloc(12)
  head.writeUInt16BE(1, 4) // QDCOUNT
  const tail = Buffer.alloc(4)
  tail.writeUInt16BE(type, 0)
  tail.writeUInt16BE(0x8001, 2) // class IN + unicast-response
  return Buffer.concat([head, encodeName(name), tail])
}

function readName(buf, off, depth = 0) {
  const labels = []
  let jumped = false
  let end = off
  while (off < buf.length && depth < 16) {
    const len = buf[off]
    if (len === 0) { if (!jumped) end = off + 1; break }
    if ((len & 0xc0) === 0xc0) { // compression pointer
      if (!jumped) end = off + 2
      off = ((len & 0x3f) << 8) | buf[off + 1]
      jumped = true
      depth++
      continue
    }
    labels.push(buf.toString('utf8', off + 1, off + 1 + len))
    off += 1 + len
  }
  return { name: labels.join('.'), next: end }
}

/** Every record of an mDNS answer: [{name, type, data}] (PTR/SRV/A data decoded). Throws on garbage. */
export function parseRecords(buf) {
  if (buf.length < 12) throw new Error('short packet')
  const qd = buf.readUInt16BE(4)
  const rr = buf.readUInt16BE(6) + buf.readUInt16BE(8) + buf.readUInt16BE(10)
  let off = 12
  for (let i = 0; i < qd; i++) off = readName(buf, off).next + 4
  const out = []
  for (let i = 0; i < rr && off + 10 <= buf.length; i++) {
    const n = readName(buf, off)
    off = n.next
    const type = buf.readUInt16BE(off)
    const len = buf.readUInt16BE(off + 8)
    const start = off + 10
    off = start + len
    if (off > buf.length) break
    let data = null
    if (type === 12) data = readName(buf, start).name // PTR
    else if (type === 33) data = { port: buf.readUInt16BE(start + 4), target: readName(buf, start + 6).name } // SRV
    else if (type === 1 && len === 4) data = [...buf.subarray(start, start + 4)].join('.') // A
    if (data !== null) out.push({ name: n.name, type, data })
  }
  return out
}

/** SOULs from a set of records: [{instance, host, ip, port, url}] */
export function soulsFrom(records) {
  const ptr = records.filter((r) => r.type === 12 && r.name.toLowerCase() === SERVICE).map((r) => r.data)
  const out = []
  for (const inst of ptr) {
    const srv = records.find((r) => r.type === 33 && r.name === inst)
    const host = srv ? srv.data.target : inst.split('.')[0] + '.local'
    const a = records.find((r) => r.type === 1 && r.name === host)
    const port = srv ? srv.data.port : 8765
    const addr = a ? a.data : host
    out.push({ instance: inst, host, ip: a ? a.data : null, port, url: `ws://${addr}:${port}/bridge` })
  }
  return out
}

/** Ask the Wi-Fi which SOULs listen for a bridge. Resolves with what answered within `timeoutMs`. */
export function discoverSouls({ timeoutMs = 1500, socketFactory = () => dgram.createSocket({ type: 'udp4', reuseAddr: true }) } = {}) {
  return new Promise((resolve) => {
    const sock = socketFactory()
    const records = []
    const done = () => { try { sock.close() } catch {} ; resolve(dedupe(soulsFrom(records))) }
    sock.on('message', (m) => { try { records.push(...parseRecords(m)) } catch {} })
    sock.on('error', done)
    sock.bind(0, () => {
      const q = query()
      sock.send(q, 0, q.length, MDNS.port, MDNS.address, () => {})
      setTimeout(done, timeoutMs)
    })
  })
}

function dedupe(list) {
  const seen = new Set()
  return list.filter((s) => (seen.has(s.url) ? false : seen.add(s.url)))
}
