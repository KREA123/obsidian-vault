import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  matchLocality, findLocality, cleanCityName, detectSector, cityVariants, stripPrefix, normalizeText,
  compactKey, normCounty, isBucharest, matchCounty, localityError, localityKeys,
} from '../src/couriers/locality.js';
import { ro } from './helpers-i18n.js';

// Real FAN nomenclator rows (GET https://api.fancourier.ro/reports/localities is public), see fixture.
const FAN = JSON.parse(readFileSync(new URL('./fixtures/couriers/fancourier.json', import.meta.url), 'utf8'));
const FAN_ROWS = FAN.localitiesSample.body.data.map((d) => [d.name, d.county]);
const fan = (address) => findLocality(FAN_ROWS, address, {
  nameOf: (r) => r[0], countyOf: (r) => r[1], sameNameIsSame: true, provider: 'fancourier', providerName: 'FAN Courier',
});

// Cargus-style nomenclator of one county (Cluj).
const CLUJ = [
  { id: 5479, name: 'Cluj-Napoca', postalCode: '400001' },
  { id: 5480, name: 'Floresti', postalCode: '407280' },
  { id: 5481, name: 'Apahida', postalCode: '407035' },
  { id: 5482, name: 'Turda', postalCode: '401001' },
];
const ALBA_FLORESTI = [
  { id: 278, name: 'Floresti', postalCode: '517176' },
  { id: 312, name: 'Floresti', postalCode: '515511' },
  { id: 592, name: 'Floresti', postalCode: '517596' },
  { id: 653, name: 'Floresti', postalCode: '517684' },
];

describe('normalization', () => {
  test('diacritics (comma and cedilla), punctuation, prefixes', () => {
    assert.equal(normalizeText('Bistrița-Năsăud'), 'bistrita nasaud');
    assert.equal(normalizeText('Bistriţa–Năsăud'), 'bistrita nasaud'); // cedilla ţ + en dash
    assert.equal(compactKey('Cluj - Napoca'), 'clujnapoca');
    assert.equal(stripPrefix('mun cluj napoca'), 'cluj napoca');
    assert.equal(stripPrefix('sat'), 'sat'); // a place literally called "Sat" survives
    assert.equal(normCounty('Jud. Bistrița-Năsăud'), 'bistrita nasaud');
    assert.equal(normCounty('Municipiul București'), 'bucuresti');
    assert.ok(isBucharest('Bucharest') && isBucharest('', 'B') && !isBucharest('Ilfov', 'IF'));
  });

  test('single letters are not prefixes: real FAN names "C.A. Rosetti", "I. L. Caragiale"', () => {
    assert.equal(cleanCityName('C.A. Rosetti'), 'c a rosetti');
    assert.equal(cleanCityName('I. L. Caragiale'), 'i l caragiale');
    assert.deepEqual(fan({ city: 'C.A. Rosetti', county: 'Buzău' }), ['C.A. Rosetti', 'Buzau']);
    assert.deepEqual(fan({ city: 'Com. I.L. Caragiale', county: 'Dâmbovița' }), ['I. L. Caragiale', 'Dambovita']);
  });

  test('cleanCityName / detectSector', () => {
    assert.equal(cleanCityName('Mun. Cluj-Napoca'), 'cluj napoca');
    assert.equal(cleanCityName('Sat Roșu, Com. Chiajna'), 'rosu');
    assert.equal(cleanCityName('Voluntari (Ilfov)'), 'voluntari');
    assert.equal(detectSector({ city: 'București, Sectorul 4' }), 4);
    assert.equal(detectSector({ city: 'Bucuresti S3' }), 3);
    assert.equal(detectSector({ city: 'Bucuresti', zip: '061344', bucharest: true }), 6);
    assert.equal(detectSector({ city: 'Bucuresti', zip: '400001', bucharest: true }), undefined);
  });

  test('cityVariants: Bucharest sectors, comma parts, county never a variant', () => {
    assert.deepEqual(cityVariants({ city: 'Sector 2', county: 'București' }),
      ['bucuresti sector 2', 'sector 2', 'bucuresti sectorul 2', 'sectorul 2', 'bucuresti', 'municipiul bucuresti']);
    assert.deepEqual(cityVariants({ city: 'Sat Florești, Cluj', county: 'Cluj' }), ['floresti', 'sat floresti']);
    assert.deepEqual(cityVariants({ city: 'Roșu, Com. Chiajna', county: 'Ilfov' }), ['rosu', 'chiajna']);
    // "Voluntari" with county București is not Bucharest itself (callers try Ilfov).
    assert.deepEqual(cityVariants({ city: 'Voluntari', county: 'București', countyCode: 'B' }), ['voluntari']);
  });

  test('localityKeys covers FAN "Name (Commune)" spelling', () => {
    assert.deepEqual(localityKeys('Alun (Bosorod)'), ['alunbosorod', 'alun']);
  });
});

describe('matchLocality', () => {
  test('exact, prefix and hyphen insensitive', () => {
    for (const city of ['Cluj-Napoca', 'cluj napoca', 'Mun. Cluj-Napoca', 'CLUJ–NAPOCA', 'Municipiul Cluj Napoca']) {
      assert.equal(matchLocality({ city, county: 'Cluj' }, CLUJ).match.id, 5479, city);
    }
  });

  test('"contains" (county appended) and unrelated names', () => {
    assert.equal(matchLocality({ city: 'Turda, jud. Cluj', county: 'Cluj' }, CLUJ).match.id, 5482);
    assert.equal(matchLocality({ city: 'Apahida Cluj', county: 'Cluj' }, CLUJ).match.id, 5481);
    assert.equal(matchLocality({ city: 'Gherla', county: 'Cluj' }, CLUJ).notFound, true);
  });

  test('same-named villages: postal code (exact or ≥4-digit prefix), otherwise ambiguous in nomenclator order', () => {
    assert.equal(matchLocality({ city: 'Florești', county: 'Alba', zip: '515511' }, ALBA_FLORESTI).match.id, 312);
    assert.equal(matchLocality({ city: 'Florești', county: 'Alba', zip: '517690' }, ALBA_FLORESTI).match.id, 653);
    const r = matchLocality({ city: 'Florești', county: 'Alba' }, ALBA_FLORESTI);
    assert.deepEqual(r.ambiguous.map((c) => c.id), [278, 312, 592, 653]);
    const e = localityError({ provider: 'cargus', providerName: 'Cargus', city: 'Florești', county: 'Alba', result: r });
    assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
    assert.match(ro(e).hint, /^Ai vrut: Floresti \(cod 517176\), Floresti \(cod 515511\), Floresti \(cod 517596\)\?/);
  });

  test('same-named villages told apart by the commune typed (parent), labelled by commune', () => {
    const cands = [
      { id: 1, name: 'VALEA MARE', parent: 'BUDESTI', postalCode: '247061' },
      { id: 2, name: 'VALEA MARE', parent: 'STEFANESTI', postalCode: '247562' },
    ];
    assert.equal(matchLocality({ city: 'Valea Mare, com. Ștefănești', county: 'Vâlcea' }, cands).match.id, 2);
    const r = matchLocality({ city: 'Valea Mare', county: 'Vâlcea' }, cands);
    const e = localityError({ provider: 'dpd', providerName: 'DPD', city: 'Valea Mare', county: 'Vâlcea', result: r });
    assert.equal(ro(e).hint.split('?')[0], 'Ai vrut: VALEA MARE (BUDESTI), VALEA MARE (STEFANESTI)');
  });

  test('București: one locality, or a sector-split nomenclator (Sameday)', () => {
    const one = [{ id: 150, name: 'Bucuresti' }];
    assert.equal(matchLocality({ city: 'Sectorul 3', county: 'București', countyCode: 'B' }, one).match.id, 150);
    const sectors = [1, 2, 3, 4, 5, 6].map((n) => ({ id: n, name: `Sectorul ${n}`, postalCode: `0${n}0011` }));
    assert.equal(matchLocality({ city: 'București S4', county: 'București', countyCode: 'B' }, sectors).match.id, 4);
    assert.equal(matchLocality({ city: 'București', county: 'București', countyCode: 'B', zip: '061344' }, sectors).match.id, 6);
    const r = matchLocality({ city: 'București', county: 'București', countyCode: 'B' }, sectors);
    assert.equal(r.ambiguous.length, 6);
    const e = localityError({ provider: 'sameday', providerName: 'Sameday', city: 'București', county: 'București', result: r });
    assert.match(ro(e).message, /București, Sameday cere sectorul/);
    assert.match(ro(e).hint, /^Ai vrut: Sectorul 1, Sectorul 2, Sectorul 3\? Adaugă sectorul/);
  });

  test('unique postal code when the name is a neighbourhood', () => {
    const ilfov = [{ id: 900, name: 'Voluntari', postalCode: '077190' }, { id: 901, name: 'Otopeni', postalCode: '075100' }];
    assert.equal(matchLocality({ city: 'Pipera', county: 'Ilfov', zip: '077190' }, ilfov).match.id, 900);
  });

  test('one-letter typos only when the adapter opts in ("Bucium" ≠ "Buciumi")', () => {
    assert.equal(matchLocality({ city: 'Cluj-Napoka', county: 'Cluj' }, CLUJ).notFound, true);
    assert.equal(matchLocality({ city: 'Cluj-Napoka', county: 'Cluj' }, CLUJ, { fuzzy: true }).match.id, 5479);
    const r = matchLocality({ city: 'Cluj Napocca Est', county: 'Cluj' }, CLUJ);
    assert.equal(r.notFound, true);
    assert.equal(r.suggestions[0].id, 5479);
    assert.ok(r.suggestions.length <= 3);
  });

  test('matchCounty by code, name, diacritics and București aliases', () => {
    const counties = [{ id: 1, name: 'Bucuresti', code: 'B' }, { id: 6, name: 'Bistrita-Nasaud', code: 'BN' }];
    assert.equal(matchCounty({ county: 'Bistrița-Năsăud' }, counties).id, 6);
    assert.equal(matchCounty({ county: 'Jud. Bistrita Nasaud' }, counties).id, 6);
    assert.equal(matchCounty({ county: 'Municipiul București' }, counties).id, 1);
    assert.equal(matchCounty({ county: 'X', countyCode: 'B' }, counties).id, 1);
    assert.equal(matchCounty({ county: 'Atlantida' }, counties), null);
  });
});

describe('findLocality on the real FAN nomenclator (live sample)', () => {
  test('"Name (Commune)" entries: bare name unique → that entry; duplicates → ask, never guess', () => {
    assert.deepEqual(fan({ city: 'Merișor', county: 'Hunedoara' }), ['Merisor (Bucuresci)', 'Hunedoara']);
    assert.deepEqual(fan({ city: 'Lunca', county: 'Buzău' }), ['Lunca (C.A. Rosetti)', 'Buzau']);
    assert.throws(() => fan({ city: 'Alun', county: 'Hunedoara' }), (e) => {
      assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
      assert.match(ro(e).message, /„Alun” apare de mai multe ori în nomenclatorul FAN Courier pentru județul Hunedoara/);
      assert.equal(ro(e).hint.split('?')[0], 'Ai vrut: Alun (Bosorod), Alun (Bunila)');
      return true;
    });
  });

  test('commune typed next to the village resolves FAN duplicates', () => {
    assert.deepEqual(fan({ city: 'Alun, com. Bosorod', county: 'Hunedoara' }), ['Alun (Bosorod)', 'Hunedoara']);
    assert.deepEqual(fan({ city: 'Sat Alun Comuna Bunila', county: 'Hunedoara' }), ['Alun (Bunila)', 'Hunedoara']);
    assert.deepEqual(fan({ city: 'Alun (Bunila)', county: 'Hunedoara' }), ['Alun (Bunila)', 'Hunedoara']);
  });

  test('village + commune both in the nomenclator: the village wins', () => {
    assert.deepEqual(fan({ city: 'Sat Rosu Com Chiajna', county: 'Ilfov' }), ['Rosu', 'Ilfov']);
    assert.deepEqual(fan({ city: 'Roșu, Chiajna', county: 'Ilfov' }), ['Rosu', 'Ilfov']);
    assert.deepEqual(fan({ city: 'Comuna Chiajna', county: 'Ilfov' }), ['Chiajna', 'Ilfov']);
  });

  test('București ↔ Ilfov mix-up accepted on exact names only', () => {
    assert.deepEqual(fan({ city: 'Voluntari', county: 'București', countyCode: 'B' }), ['Voluntari', 'Ilfov']);
    assert.deepEqual(fan({ city: 'Sectorul 3', county: 'București', countyCode: 'B' }), ['Bucuresti', 'Bucuresti']);
    assert.deepEqual(fan({ city: 'București', county: 'Ilfov', countyCode: 'IF' }), ['Bucuresti', 'Bucuresti']);
    assert.throws(() => fan({ city: 'Voluntarii', county: 'București', countyCode: 'B' }), (e) => e.code === 'ADDRESS_CITY_NOT_FOUND');
  });

  test('county unknown to the nomenclator: nationwide, unique names only, county in the suggestion', () => {
    assert.deepEqual(fan({ city: 'Deva', county: 'Atlantida' }), ['Deva', 'Hunedoara']);
    assert.throws(() => fan({ city: 'Florești', county: 'Atlantida' }), (e) => {
      assert.equal(ro(e).hint.split('?')[0], 'Ai vrut: Floresti (jud. Cluj), Floresti (jud. Prahova)');
      return true;
    });
  });

  test('missing city → ADDRESS_CITY_MISSING', () => {
    assert.throws(() => fan({ city: '  ', county: 'Cluj' }), (e) => e.code === 'ADDRESS_CITY_MISSING' && e.field === 'shippingAddress.city');
  });
});
