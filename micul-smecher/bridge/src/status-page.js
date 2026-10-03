// A tiny local status page instead of a tray icon: http://127.0.0.1:8766, opened by the Start SOUL launcher.
// It reads ~/.soul-bridge/status.json (written by the running bridge) and shows, in plain words, whether SOUL is
// connected, whether the Claude Code session is up, and the last questions' counts. Loopback only, read-only,
// no secrets (the bridge token never appears; there is no Claude credential anywhere to show).
import http from 'node:http'
import { spawn } from 'node:child_process'
import * as config from './config.js'

export const STATUS_PORT = 8766

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])

function alive(pid) {
  if (!pid) return false
  try { process.kill(pid, 0); return true } catch (e) { return e.code === 'EPERM' }
}

/** What the page shows, as data (also served as /status.json). */
export function snapshot() {
  const cfg = config.load()
  const st = config.readStatus() || {}
  const running = st.pid ? alive(st.pid) && st.soul !== 'closed' : false
  return {
    paired: !!cfg.token,
    soul: cfg.soul_name || null,
    via: cfg.via || (cfg.soul_url && cfg.soul_url.includes('/v1/bridge') ? 'cloud' : cfg.soul_url ? 'lan' : null),
    session: running ? 'running' : 'stopped',
    link: running ? st.soul || 'connecting' : 'closed',
    mode: st.mode || null,
    pending: st.pending || 0,
    asked: st.asked || 0,
    answered: st.answered || 0,
    timeouts: st.timeouts || 0,
    last_question: st.last || null,
    updated: st.updated || null,
  }
}

export function render(s) {
  const ok = s.session === 'running' && s.link === 'ready'
  const headline = !s.paired ? 'Not paired with a SOUL yet'
    : ok ? `Connected to ${esc(s.soul || 'SOUL')}`
      : s.session === 'running' ? `Reaching ${esc(s.soul || 'SOUL')}…` : 'SOUL Bridge is not running'
  const hint = !s.paired ? 'On SOUL: Settings › AI › My Claude on my computer, then run the command it shows.'
    : ok ? 'Questions typed on SOUL go to your own Claude Code in the Start SOUL window. Keep it open.'
      : s.session === 'running' ? 'Is SOUL on and online? It reconnects by itself.'
        : 'Double-click Start SOUL (in your SOUL-Claude folder) and keep its window open.'
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="3">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>SOUL Bridge</title>
<style>body{font:16px/1.5 system-ui,sans-serif;background:#FAF8F3;color:#16181D;max-width:34rem;margin:2rem auto;padding:0 16px}
@media (prefers-color-scheme:dark){body{background:#0B0B0C;color:#F6F3EC}}
.dot{display:inline-block;width:.8em;height:.8em;border-radius:50%;margin-right:.4em;background:${ok ? '#2E9D5B' : '#D2622C'}}
table{border-collapse:collapse;margin-top:1rem}td{padding:.2rem 1rem .2rem 0}small{opacity:.7}</style></head>
<body><h1><span class="dot"></span>${headline}</h1><p>${esc(hint)}</p>
<table><tr><td>Claude Code session</td><td>${esc(s.session)}</td></tr>
<tr><td>Link to SOUL</td><td>${esc(s.link)}${s.via ? ` (${s.via === 'cloud' ? 'through SOUL Cloud' : 'this Wi-Fi'})` : ''}</td></tr>
<tr><td>Questions</td><td>${s.asked} asked · ${s.answered} answered · ${s.timeouts} timed out · ${s.pending} waiting</td></tr>
<tr><td>Last question</td><td>${esc(s.last_question || '—')}</td></tr></table>
<p><small>SOUL Bridge never sees your Claude password or tokens: Claude Code signs in by itself. This page is only on this computer.</small></p>
</body></html>`
}

export function startStatusPage({ port = STATUS_PORT, host = '127.0.0.1' } = {}) {
  const srv = http.createServer((req, res) => {
    const h = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'" }
    if (req.method !== 'GET') { res.writeHead(405, h); return res.end() }
    if (req.url === '/status.json') { res.writeHead(200, { ...h, 'Content-Type': 'application/json' }); return res.end(JSON.stringify(snapshot())) }
    if (req.url === '/' || req.url.startsWith('/?')) { res.writeHead(200, { ...h, 'Content-Type': 'text/html; charset=utf-8' }); return res.end(render(snapshot())) }
    res.writeHead(404, h)
    res.end()
  })
  return new Promise((resolve, reject) => {
    srv.once('error', reject)
    srv.listen(port, host, () => resolve(srv))
  })
}

/** Open a URL in the default browser (macOS open, Windows start, Linux xdg-open). Best effort. */
export function openUrl(url, { platform = process.platform, spawnFn = spawn } = {}) {
  const [cmd, args] = platform === 'darwin' ? ['open', [url]]
    : platform === 'win32' ? ['cmd', ['/c', 'start', '""', url]]
      : ['xdg-open', [url]]
  try {
    const c = spawnFn(cmd, args, { detached: true, stdio: 'ignore', windowsHide: true })
    c.on?.('error', () => {})
    c.unref?.()
    return [cmd, ...args]
  } catch { return null }
}
