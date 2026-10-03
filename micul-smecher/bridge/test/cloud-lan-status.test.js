// Pairing through SOUL Cloud (8-character code, /v1/bridge) and on the Wi-Fi (6 digits, mDNS discovery), the
// local status page, and the launchers (macOS/Linux sh, Windows cmd) as files.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import http from 'node:http'
import { EventEmitter } from 'node:events'
import { spawn, spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { FakeSoul } from '../tools/fake-soul.js'
import { parseCode, cloudUrl, lanUrl } from '../src/protocol.js'
import { SoulLink, LABEL } from '../src/soul-link.js'
import { encodeName, parseRecords, soulsFrom, discoverSouls, query, SERVICE } from '../src/discover.js'
import { startStatusPage, render, snapshot, openUrl } from '../src/status-page.js'
import { setup, shLauncher, cmdLauncher } from '../src/setup.js'
import * as config from '../src/config.js'

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'soul-bridge.js')
// async: the fake SOUL lives in this process, so never block the event loop with spawnSync
const cli = (args, home) => new Promise((resolve) => {
  const c = spawn(process.execPath, [BIN, ...args], { env: { ...process.env, SOUL_BRIDGE_HOME: home } })
  let out = ''
  c.stdout.on('data', (d) => (out += d)); c.stderr.on('data', (d) => (out += d))
  c.on('close', (status) => resolve({ status, out }))
})

test('codes and addresses', () => {
  assert.deepEqual(parseCode('7kq3-m9xd'), { kind: 'cloud', code: '7KQ3M9XD' })
  assert.deepEqual(parseCode(' 482913 '), { kind: 'lan', code: '482913' })
  assert.equal(parseCode('7KQ3M9XU'), null) // U is not Crockford
  assert.equal(parseCode('12345'), null)
  assert.equal(cloudUrl('soul.example'), 'wss://soul.example/v1/bridge')
  assert.equal(cloudUrl('https://soul.example/'), 'wss://soul.example/v1/bridge')
  assert.equal(cloudUrl('http://127.0.0.1:8790'), 'ws://127.0.0.1:8790/v1/bridge')
  assert.throws(() => cloudUrl('http://soul.example'), /https only/)
  assert.throws(() => cloudUrl(''), /--cloud/)
  assert.equal(lanUrl('192.168.1.42'), 'ws://192.168.1.42:8765/bridge')
  assert.equal(lanUrl('soul-ab12.local'), 'ws://soul-ab12.local:8765/bridge')
  assert.equal(lanUrl('127.0.0.1:9000'), 'ws://127.0.0.1:9000/bridge')
})

test('pair through SOUL Cloud with the 8-character code (CLI), the label goes along', async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-cloud-'))
  const soul = new FakeSoul({ pairCode: '7KQ3M9XD', name: 'Miso' })
  const url = await soul.listen()
  const base = url.replace('ws://', 'http://').replace('/bridge', '')
  const frames = []
  soul.on('frame', (m) => frames.push(m))
  const { out } = await cli(['pair', '7kq3-m9xd', '--cloud', base], home)
  assert.match(out, /Paired with Miso \(through SOUL Cloud\)/)
  assert.equal(frames[0].t, 'bridge.pair')
  assert.equal(frames[0].code, '7KQ3M9XD')
  assert.equal(frames[0].label, LABEL)
  const cfg = JSON.parse(fs.readFileSync(path.join(home, 'config.json'), 'utf8'))
  assert.equal(cfg.via, 'cloud')
  assert.equal(cfg.soul_url, base.replace('http://', 'ws://') + '/v1/bridge')
  assert.match(cfg.token, /^sbt_/)
  // a wrong code is refused, and the CLI says so
  const bad = await cli(['pair', 'ZZZZ-ZZZZ', '--cloud', base], home)
  assert.notEqual(bad.status, 0)
  assert.match(bad.out, /wrong code/)
  const usage = await cli(['pair', 'nope'], home)
  assert.equal(usage.status, 1)
  assert.match(usage.out, /XXXX-XXXX \(8 characters\)/)
  await soul.close()
  fs.rmSync(home, { recursive: true, force: true })
})

// an mDNS answer as a SOUL sends it: PTR -> SRV -> A, with name compression
function answer() {
  const rr = (name, type, data) => {
    const h = Buffer.alloc(10)
    h.writeUInt16BE(type, 0); h.writeUInt16BE(1, 2); h.writeUInt32BE(120, 4); h.writeUInt16BE(data.length, 8)
    return Buffer.concat([name, h, data])
  }
  const head = Buffer.alloc(12)
  head.writeUInt16BE(0x8400, 2); head.writeUInt16BE(3, 6)
  const svc = encodeName(SERVICE)
  const inst = Buffer.concat([Buffer.from([9]), Buffer.from('soul-ab12'), Buffer.from([0xc0, 12])]) // soul-ab12._soul._tcp.local
  const srv = Buffer.alloc(6); srv.writeUInt16BE(8765, 4)
  const host = encodeName('soul-ab12.local')
  return Buffer.concat([head, rr(svc, 12, inst), rr(Buffer.from([0xc0, 12 + svc.length + 10]), 33, Buffer.concat([srv, host])),
    rr(host, 1, Buffer.from([192, 168, 1, 42]))])
}

test('mDNS: the query, the answer, and discovery with a fake socket', async () => {
  const q = query()
  assert.equal(q.readUInt16BE(4), 1)
  assert.ok(q.includes(Buffer.from('_soul')))
  const recs = parseRecords(answer())
  assert.deepEqual(recs.map((r) => r.type), [12, 33, 1])
  const souls = soulsFrom(recs)
  assert.deepEqual(souls, [{ instance: 'soul-ab12._soul._tcp.local', host: 'soul-ab12.local', ip: '192.168.1.42', port: 8765, url: 'ws://192.168.1.42:8765/bridge' }])
  class Sock extends EventEmitter {
    bind(_p, cb) { cb() }
    send(buf, _o, _l, port, addr, cb) { this.sentTo = `${addr}:${port}`; cb(); setTimeout(() => { this.emit('message', Buffer.from('junk')); this.emit('message', answer()) }, 5) }
    close() { this.closed = true }
  }
  const sock = new Sock()
  const found = await discoverSouls({ timeoutMs: 60, socketFactory: () => sock })
  assert.equal(sock.sentTo, '224.0.0.251:5353')
  assert.equal(found.length, 1)
  assert.equal(found[0].url, 'ws://192.168.1.42:8765/bridge')
})

test('pair on the Wi-Fi with 6 digits and --soul', async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-lan-'))
  const soul = new FakeSoul({ pairCode: '482913' })
  const url = await soul.listen()
  const addr = url.replace('ws://', '').replace('/bridge', '')
  const r = await cli(['pair', '482913', '--soul', addr], home)
  assert.match(r.out, /\(on this Wi-Fi\)/)
  const cfg = JSON.parse(fs.readFileSync(path.join(home, 'config.json'), 'utf8'))
  assert.equal(cfg.via, 'lan')
  assert.equal(cfg.soul_url, lanUrl(addr))
  const p = await SoulLink.pair({ url: lanUrl(addr), code: '482913' })
  assert.match(p.token, /^sbt_/)
  await soul.close()
  fs.rmSync(home, { recursive: true, force: true })
})

const get = (port, p, method = 'GET') => new Promise((resolve, reject) => {
  const req = http.request({ host: '127.0.0.1', port, path: p, method }, (res) => {
    let b = ''
    res.on('data', (d) => (b += d)); res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: b }))
  })
  req.on('error', reject)
  req.end()
})

test('the status page: loopback, read-only, plain words, no secrets', async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-page-'))
  process.env.SOUL_BRIDGE_HOME = home
  const srv = await startStatusPage({ port: 0 })
  const port = srv.address().port
  assert.equal(srv.address().address, '127.0.0.1')
  let r = await get(port, '/')
  assert.equal(r.status, 200)
  assert.match(r.body, /Not paired with a SOUL yet/)
  assert.match(r.headers['content-security-policy'], /default-src 'none'/)
  config.save({ soul_url: 'wss://soul.example/v1/bridge', token: 'sbt_' + 'k'.repeat(43), soul_name: 'Miso<b>', via: 'cloud' })
  config.writeStatus({ mode: 'channel', pid: process.pid, soul: 'ready', device: 'Miso', pending: 0, asked: 3, answered: 2, timeouts: 1, last: '2026-10-03T18:02:00Z' })
  r = await get(port, '/')
  assert.match(r.body, /Connected to Miso&lt;b&gt;/) // escaped
  assert.match(r.body, /3 asked · 2 answered · 1 timed out/)
  assert.match(r.body, /through SOUL Cloud/)
  assert.ok(!r.body.includes('sbt_') && !(await get(port, '/status.json')).body.includes('sbt_'))
  assert.equal(JSON.parse((await get(port, '/status.json')).body).session, 'running')
  assert.equal((await get(port, '/', 'POST')).status, 405)
  assert.equal((await get(port, '/x')).status, 404)
  config.writeStatus({ mode: 'channel', pid: 999999999, soul: 'ready' }) // the session process is gone
  assert.equal(snapshot().session, 'stopped')
  assert.match(render(snapshot()), /SOUL Bridge is not running/)
  srv.close()
  const calls = []
  const fake = (cmd, args) => { calls.push([cmd, ...args]); return { on() {}, unref() {} } }
  openUrl('http://127.0.0.1:8766/', { platform: 'darwin', spawnFn: fake })
  openUrl('http://127.0.0.1:8766/', { platform: 'win32', spawnFn: fake })
  openUrl('http://127.0.0.1:8766/', { platform: 'linux', spawnFn: fake })
  assert.deepEqual(calls.map((c) => c[0]), ['open', 'cmd', 'xdg-open'])
  assert.deepEqual(calls[1], ['cmd', '/c', 'start', '""', 'http://127.0.0.1:8766/'])
  fs.rmSync(home, { recursive: true, force: true })
})

test('launchers: find claude, open the status page, keep the window open; no credentials', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'sb-launch-'))
  const r = setup({ dir: path.join(home, "Ana's SOUL"), nodePath: '/opt/node/bin/node', binPath: '/opt/sb/bin/soul-bridge.js' })
  const sh = fs.readFileSync(r.files.command, 'utf8')
  assert.equal(sh, fs.readFileSync(r.files.sh, 'utf8'))
  assert.ok((fs.statSync(r.files.command).mode & 0o111) !== 0, 'Start SOUL.command is executable')
  assert.match(sh, /^#!\/bin\/sh\n/)
  assert.match(sh, /cd '.*Ana'\\''s SOUL' \|\| exit 1/) // quoted for a folder with an apostrophe
  assert.match(sh, /PATH="\$HOME\/\.local\/bin:/) // a double-clicked .command gets a bare PATH
  assert.match(sh, /command -v claude/)
  assert.match(sh, /status-page --open/)
  assert.match(sh, /\nclaude --dangerously-load-development-channels server:soul --tools "" --allowedTools mcp__soul__soul_reply mcp__soul__soul_status --name SOUL\n/)
  assert.match(sh, /read -r _/)
  const cmd = fs.readFileSync(r.files.cmd, 'utf8')
  assert.ok(cmd.split('\n').slice(0, -1).every((l) => l.endsWith('\r')), 'CRLF line ends')
  assert.match(cmd, /chcp 65001/)
  assert.match(cmd, /where claude/)
  assert.match(cmd, /start "" \/b "\/opt\/node\/bin\/node" "\/opt\/sb\/bin\/soul-bridge.js" status-page --open/)
  assert.match(cmd, /call claude --dangerously-load-development-channels server:soul --tools ""/)
  assert.match(cmd, /\r\npause\r\n$/)
  assert.match(cmdLauncher({ dir: 'C:\\Users\\a%b', nodePath: 'n', binPath: 'b', args: '' }), /cd \/d "C:\\Users\\a%%b"/)
  for (const t of [sh, cmd]) assert.ok(!/sk-ant|setup-token|CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY|sbt_/.test(t))
  assert.ok(!r.mcp.mcpServers.soul.args[0].includes('%20'))
  // ShellCheck, when it is installed (CI / the founder's machine)
  const sc = spawnSync('shellcheck', ['-s', 'sh', r.files.sh], { encoding: 'utf8' })
  if (sc.error === undefined) assert.equal(sc.status, 0, sc.stdout)
  assert.equal(shLauncher({ dir: '/x', nodePath: 'n', binPath: 'b', args: '' }).includes("cd '/x'"), true)
  fs.rmSync(home, { recursive: true, force: true })
})
