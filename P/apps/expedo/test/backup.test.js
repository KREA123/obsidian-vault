import { test } from 'node:test';
import assert from 'node:assert/strict';
import net from 'node:net';
import { mkdtempSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { command, parseReply, restore, snapshot, seal, unseal } from '../src/lib/backup.js';

// A tiny in-memory Redis: AUTH, GET, SET, enough for the backup client.
function fakeRedis({ password } = {}) {
  const data = new Map();
  const server = net.createServer((sock) => {
    let buf = Buffer.alloc(0);
    let authed = !password;
    sock.on('data', (chunk) => {
      buf = Buffer.concat([buf, chunk]);
      for (;;) {
        const cmd = readCommand(buf);
        if (!cmd) return;
        buf = buf.subarray(cmd.used);
        const [name, ...args] = cmd.args;
        const op = name.toString().toUpperCase();
        if (op === 'AUTH') {
          authed = args.at(-1).toString() === password;
          sock.write(authed ? '+OK\r\n' : '-WRONGPASS invalid password\r\n');
        } else if (!authed) sock.write('-NOAUTH Authentication required.\r\n');
        else if (op === 'SET') { data.set(args[0].toString(), args[1]); sock.write('+OK\r\n'); }
        else if (op === 'GET') {
          const v = data.get(args[0].toString());
          sock.write(v ? Buffer.concat([Buffer.from(`$${v.length}\r\n`), v, Buffer.from('\r\n')]) : '$-1\r\n');
        } else sock.write(`-ERR unknown command ${op}\r\n`);
      }
    });
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve({ server, data, port: server.address().port })));
}

function readCommand(buf) {
  let i = buf.indexOf('\r\n');
  if (i < 0) return null;
  const n = Number(buf.subarray(1, i).toString());
  let pos = i + 2;
  const args = [];
  for (let k = 0; k < n; k++) {
    const e = buf.indexOf('\r\n', pos);
    if (e < 0) return null;
    const len = Number(buf.subarray(pos + 1, e).toString());
    if (buf.length < e + 2 + len + 2) return null;
    args.push(buf.subarray(e + 2, e + 2 + len));
    pos = e + 2 + len + 2;
  }
  return { args, used: pos };
}

test('RESP replies parse, including partial bulk strings', () => {
  assert.deepEqual(parseReply(Buffer.from('+OK\r\n')), { value: 'OK' });
  assert.deepEqual(parseReply(Buffer.from('$-1\r\n')), { value: null });
  assert.equal(parseReply(Buffer.from('$5\r\nab')), null);
  assert.equal(parseReply(Buffer.from('$5\r\nabc\r\n\r\n')).value.toString(), 'abc\r\n');
  assert.deepEqual(parseReply(Buffer.from('-ERR x\r\n')), { error: 'ERR x' });
});

test('snapshots are encrypted and tamper-evident', () => {
  const blob = seal(Buffer.from('secret orders'));
  assert.ok(!blob.includes(Buffer.from('secret')));
  assert.equal(unseal(blob).toString(), 'secret orders');
  blob[blob.length - 1] ^= 1;
  assert.throws(() => unseal(blob));
});

test('snapshot → lost disk → restore brings the database back (with a password)', async () => {
  const { server, data, port } = await fakeRedis({ password: 'pw' });
  const url = `redis://default:pw@127.0.0.1:${port}`;
  const dir = mkdtempSync(join(tmpdir(), 'expedo-backup-'));
  const file = join(dir, 'data', 'expedo.db');
  try {
    assert.deepEqual(await restore(file, url), { restored: false }, 'nothing stored yet');

    const { mkdirSync } = await import('node:fs');
    mkdirSync(join(dir, 'data'));
    let db = new DatabaseSync(file);
    db.exec(`PRAGMA journal_mode = WAL; CREATE TABLE t (v TEXT); INSERT INTO t VALUES ('AWB 123'), ('${'x'.repeat(200000)}');`);
    await snapshot(db, file, url);
    assert.ok(data.get('expedo:db').length < 10000, 'gzipped');
    assert.ok(!existsSync(`${file}.snapshot`), 'temporary copy removed');
    db.close();

    rmSync(join(dir, 'data'), { recursive: true });
    const r = await restore(file, url);
    assert.equal(r.restored, true);
    db = new DatabaseSync(file);
    assert.equal(db.prepare('SELECT v FROM t LIMIT 1').get().v, 'AWB 123');
    db.close();

    // An existing file is never overwritten.
    assert.deepEqual(await restore(file, url), { restored: false });
    await assert.rejects(command(`redis://default:wrong@127.0.0.1:${port}`, ['GET', 'expedo:db']), /WRONGPASS/);
  } finally {
    server.close();
    rmSync(dir, { recursive: true, force: true });
  }
});
