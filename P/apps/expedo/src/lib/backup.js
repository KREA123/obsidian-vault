// Database snapshots in a Redis-compatible key-value store (Render Key Value).
// For hosting without a persistent disk (e.g. Render's free plan): the SQLite file lives on an
// ephemeral disk, so the whole database is copied to the key-value store a few seconds after every
// change and restored from there on boot. The snapshot is gzipped and encrypted with APP_SECRET.
import net from 'node:net';
import tls from 'node:tls';
import { existsSync, readFileSync, writeFileSync, rmSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { gzipSync, gunzipSync } from 'node:zlib';
import { createCipheriv, createDecipheriv, createHash, randomBytes } from 'node:crypto';
import { config } from '../config.js';

const KEY = 'expedo:db';
const key = () => createHash('sha256').update(`expedo-backup:${config.appSecret}`).digest();

export function seal(buf) {
  const iv = randomBytes(12);
  const c = createCipheriv('aes-256-gcm', key(), iv);
  const enc = Buffer.concat([c.update(buf), c.final()]);
  return Buffer.concat([iv, c.getAuthTag(), enc]);
}
export function unseal(buf) {
  const d = createDecipheriv('aes-256-gcm', key(), buf.subarray(0, 12));
  d.setAuthTag(buf.subarray(12, 28));
  return Buffer.concat([d.update(buf.subarray(28)), d.final()]);
}

// ---- minimal RESP client: one connection per command, binary-safe GET / SET ----
function encodeCommand(args) {
  const parts = [Buffer.from(`*${args.length}\r\n`)];
  for (const a of args) {
    const b = Buffer.isBuffer(a) ? a : Buffer.from(String(a));
    parts.push(Buffer.from(`$${b.length}\r\n`), b, Buffer.from('\r\n'));
  }
  return Buffer.concat(parts);
}

/** Parses one RESP reply from buf. Returns { value } when complete, null when more bytes are needed. */
export function parseReply(buf) {
  const eol = buf.indexOf('\r\n');
  if (eol < 0) return null;
  const type = String.fromCharCode(buf[0]);
  const line = buf.subarray(1, eol).toString();
  if (type === '+') return { value: line };
  if (type === '-') return { error: line };
  if (type === ':') return { value: Number(line) };
  if (type === '$') {
    const len = Number(line);
    if (len < 0) return { value: null };
    if (buf.length < eol + 2 + len + 2) return null;
    return { value: buf.subarray(eol + 2, eol + 2 + len) };
  }
  return { error: `unsupported reply type ${type}` };
}

export function command(url, args, { timeoutMs = 15000 } = {}) {
  const u = new URL(url);
  const opts = { host: u.hostname, port: Number(u.port || 6379) };
  const auth = u.password ? [u.username ? ['AUTH', decodeURIComponent(u.username), decodeURIComponent(u.password)] : ['AUTH', decodeURIComponent(u.password)]] : [];
  return new Promise((resolve, reject) => {
    const sock = u.protocol === 'rediss:' ? tls.connect({ ...opts, servername: u.hostname }) : net.connect(opts);
    let buf = Buffer.alloc(0);
    let pending = auth.length + 1;
    const done = (err, value) => { sock.destroy(); clearTimeout(timer); err ? reject(err) : resolve(value); };
    const timer = setTimeout(() => done(new Error('key-value store timeout')), timeoutMs);
    sock.on('error', (err) => done(err));
    sock.on('data', (chunk) => {
      buf = Buffer.concat([buf, chunk]);
      for (;;) {
        const r = parseReply(buf);
        if (!r) return;
        if (r.error) return done(new Error(`key-value store: ${r.error}`));
        // Skip past this reply (AUTH +OK) and keep reading.
        pending -= 1;
        if (!pending) return done(null, r.value);
        buf = buf.subarray(buf.indexOf('\r\n') + 2);
      }
    });
    sock.write(Buffer.concat([...auth, args].map(encodeCommand)));
  });
}

// ---- restore / snapshot ----

/** Before the database is opened: if the file is missing and a snapshot exists, write it back. */
export async function restore(file = config.dbFile, url = process.env.BACKUP_REDIS_URL) {
  if (!url || file === ':memory:' || existsSync(file)) return { restored: false };
  const blob = await command(url, ['GET', KEY]);
  if (!blob) return { restored: false };
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, gunzipSync(unseal(blob)));
  return { restored: true, bytes: blob.length };
}

/** Copies the open database to the key-value store. `db` is the node:sqlite connection. */
export async function snapshot(db, file = config.dbFile, url = process.env.BACKUP_REDIS_URL) {
  const tmp = `${file}.snapshot`;
  rmSync(tmp, { force: true });
  db.exec(`VACUUM INTO '${tmp.replaceAll("'", "''")}'`);
  try {
    const blob = seal(gzipSync(readFileSync(tmp)));
    await command(url, ['SET', KEY, blob]);
    return { bytes: blob.length };
  } finally {
    rmSync(tmp, { force: true });
  }
}

/**
 * Snapshots a few seconds after the database changes (never more often than every `minGapMs`),
 * at least every `refreshMs`, and once more on SIGTERM (deploy, restart, spin-down) before exiting.
 */
export function startBackups(getDb, { file = config.dbFile, url = process.env.BACKUP_REDIS_URL, checkMs = 3000, minGapMs = 10000, refreshMs = 15 * 60_000 } = {}) {
  if (!url || file === ':memory:') return null;
  let saved = -1;
  let lastAt = 0;
  let running = null;
  const changes = () => getDb().prepare('SELECT total_changes() AS c').get().c;
  const run = async (force = false) => {
    if (running) return running;
    const c = changes();
    // Unchanged: still re-sent every `refreshMs`, in case the key-value store itself restarted empty.
    const stale = Date.now() - lastAt > refreshMs;
    if ((c === saved && !stale) || (!force && Date.now() - lastAt < minGapMs)) return;
    running = snapshot(getDb(), file, url)
      .then((r) => {
        saved = c;
        lastAt = Date.now();
        if (r.bytes > 20 * 1024 * 1024) console.warn(`backup: snapshot is ${(r.bytes / 1048576).toFixed(1)} MB, close to the key-value store limit`);
      })
      .catch((err) => console.error('backup: snapshot failed', err.message))
      .finally(() => { running = null; });
    return running;
  };
  const timer = setInterval(run, checkMs);
  timer.unref();
  const onStop = (signal) => {
    clearInterval(timer);
    Promise.resolve(running).then(() => run(true)).finally(() => process.exit(signal === 'SIGINT' ? 130 : 0));
  };
  process.once('SIGTERM', onStop);
  process.once('SIGINT', onStop);
  return { run, stop: () => clearInterval(timer) };
}

/**
 * Hosting that sleeps without inbound traffic (Render free: after 15 minutes) would make the first
 * webhook or app load after a pause wait for a cold start. A request to our own public URL every
 * few minutes counts as inbound traffic.
 */
export function startKeepAwake(appUrl = config.appUrl, everyMs = 10 * 60_000) {
  if (process.env.KEEP_AWAKE !== '1' || !/^https:/.test(appUrl)) return null;
  const timer = setInterval(() => fetch(`${appUrl}/healthz`).catch(() => {}), everyMs);
  timer.unref();
  return timer;
}
