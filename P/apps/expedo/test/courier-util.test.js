import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TrackingStatus } from '../src/couriers/contract.js';
import {
  normalizePhoneRO, toIntlPhone, classifyStatusText, roLocalToIso, courierDateToIso, splitStreet, money,
  accountKey, assertRonCod, looksLikeHtml, parseDimensions,
} from '../src/couriers/util.js';

test('phones', () => {
  assert.equal(normalizePhoneRO('+40 (722) 123-456'), '0722123456');
  assert.equal(normalizePhoneRO('0040722123456'), '0722123456');
  assert.equal(normalizePhoneRO('722123456'), '0722123456');
  assert.equal(toIntlPhone('0722 123 456'), '+40722123456');
  assert.equal(toIntlPhone('+40722123456'), '+40722123456');
});

test('classifyStatusText checks negatives before positives', () => {
  assert.equal(classifyStatusText('Colet nelivrat'), TrackingStatus.FAILED_ATTEMPT);
  assert.equal(classifyStatusText('Coletul a fost livrat cu succes'), TrackingStatus.DELIVERED);
  assert.equal(classifyStatusText('Retur livrat la expeditor'), TrackingStatus.RETURNED);
  assert.equal(classifyStatusText('Ramburs returnat expeditorului'), TrackingStatus.DELIVERED);
});

test('dates: zone-less courier dates are Bucharest local time, explicit zones honoured', () => {
  assert.equal(roLocalToIso('2024-01-15 12:00:00'), '2024-01-15T10:00:00.000Z'); // EET
  assert.equal(courierDateToIso('2024-07-15T12:00:00'), '2024-07-15T09:00:00.000Z'); // EEST, not the server's zone
  assert.equal(courierDateToIso('2019-02-26T09:37:28+0200'), '2019-02-26T07:37:28.000Z'); // Sameday SDK sample
  assert.equal(courierDateToIso('2019-10-24T12:33:12.035Z'), '2019-10-24T12:33:12.035Z');
  assert.equal(courierDateToIso(''), undefined);
  assert.equal(courierDateToIso('not a date'), undefined);
});

test('splitStreet', () => {
  assert.deepEqual(splitStreet('Bd. Unirii 15A'), { street: 'Bd. Unirii', number: '15', info: 'A' });
  assert.deepEqual(splitStreet('Aleea Teiului bl. A3 sc. 2'), { street: 'Aleea Teiului bl. A3 sc. 2', number: '', info: '' });
  assert.deepEqual(splitStreet('Str. Memorandumului nr. 28, ap. 3'), { street: 'Str. Memorandumului', number: '28', info: 'ap. 3' });
});

test('money rounds to bani without float artefacts', () => {
  assert.equal(money(149.899999999), 149.9);
  assert.equal(money(1.005), 1.01);
  assert.equal(money(0.1 + 0.2), 0.3);
  assert.equal(money('199.99'), 199.99);
  assert.equal(money(-5), 0);
  assert.equal(money(undefined), 0);
});

test('accountKey: stable, different per account / secret / environment, never the secret itself', () => {
  const a = accountKey('prod', 'shop', 'secret');
  assert.equal(a, accountKey('prod', 'shop', 'secret'));
  assert.notEqual(a, accountKey('prod', 'shop', 'secret2'));
  assert.notEqual(a, accountKey('demo', 'shop', 'secret'));
  assert.notEqual(accountKey('ab', 'c'), accountKey('a', 'bc'));
  assert.ok(!a.includes('secret') && /^[0-9a-f]{16}$/.test(a));
});

test('assertRonCod refuses COD in another currency, ignores prepaid', () => {
  assert.throws(() => assertRonCod({ cod: 49.9, currency: 'EUR' }, { provider: 'cargus', providerName: 'Cargus' }),
    (e) => e.code === 'COD_CURRENCY_UNSUPPORTED' && e.field === 'cod' && !e.retryable && /EUR/.test(e.message));
  assertRonCod({ cod: 0, currency: 'EUR' }, { provider: 'cargus', providerName: 'Cargus' });
  assertRonCod({ cod: 10, currency: 'ron' }, { provider: 'cargus', providerName: 'Cargus' });
  assertRonCod({ cod: 10 }, { provider: 'cargus', providerName: 'Cargus' });
});

test('looksLikeHtml / parseDimensions', () => {
  assert.ok(looksLikeHtml('<!DOCTYPE html><html><head><title>Just a moment...</title>'));
  assert.ok(looksLikeHtml(Buffer.from('<html><body>502</body></html>')));
  assert.ok(!looksLikeHtml({ error: { code: 403 } }) && !looksLikeHtml('Failed to authenticate!'));
  assert.deepEqual(parseDimensions('30x20x10'), { length: 30, width: 20, height: 10 });
  assert.equal(parseDimensions('n/a'), null);
});
