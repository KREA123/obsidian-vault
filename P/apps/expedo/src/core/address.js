// Romanian address normalization and validation, run BEFORE any courier call.
// Most AWB failures are bad input (county typed as "Bucuresti S3", phone with +40,
// zip with spaces), so we catch and fix them here with a clear message.

export const COUNTIES = [
  ['AB', 'Alba'], ['AR', 'Arad'], ['AG', 'Argeș'], ['BC', 'Bacău'], ['BH', 'Bihor'],
  ['BN', 'Bistrița-Năsăud'], ['BT', 'Botoșani'], ['BV', 'Brașov'], ['BR', 'Brăila'], ['B', 'București'],
  ['BZ', 'Buzău'], ['CS', 'Caraș-Severin'], ['CL', 'Călărași'], ['CJ', 'Cluj'], ['CT', 'Constanța'],
  ['CV', 'Covasna'], ['DB', 'Dâmbovița'], ['DJ', 'Dolj'], ['GL', 'Galați'], ['GR', 'Giurgiu'],
  ['GJ', 'Gorj'], ['HR', 'Harghita'], ['HD', 'Hunedoara'], ['IL', 'Ialomița'], ['IS', 'Iași'],
  ['IF', 'Ilfov'], ['MM', 'Maramureș'], ['MH', 'Mehedinți'], ['MS', 'Mureș'], ['NT', 'Neamț'],
  ['OT', 'Olt'], ['PH', 'Prahova'], ['SM', 'Satu Mare'], ['SJ', 'Sălaj'], ['SB', 'Sibiu'],
  ['SV', 'Suceava'], ['TR', 'Teleorman'], ['TM', 'Timiș'], ['TL', 'Tulcea'], ['VS', 'Vaslui'],
  ['VL', 'Vâlcea'], ['VN', 'Vrancea'],
].map(([code, name]) => ({ code, name }));

/** Lowercase, strip diacritics (incl. cedilla ş/ţ variants) and punctuation, collapse spaces. */
export function fold(s) {
  return String(s ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[şș]/gi, 's')
    .replace(/[ţț]/gi, 't')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

const countyByFold = new Map();
for (const c of COUNTIES) {
  countyByFold.set(fold(c.name), c);
  countyByFold.set(fold(c.code), c);
  countyByFold.set(fold(`judetul ${c.name}`), c);
  countyByFold.set(fold(`jud ${c.name}`), c);
}
for (const alias of ['bucharest', 'bucuresti', 'municipiul bucuresti', 'mun bucuresti', 'buc']) {
  countyByFold.set(alias, COUNTIES.find((c) => c.code === 'B'));
}

/** Finds a county from a Shopify province name/code; tolerant to "Sector 3", "Jud. Cluj", typos in diacritics. */
export function findCounty(input) {
  const f = fold(input);
  if (!f) return null;
  if (countyByFold.has(f)) return countyByFold.get(f);
  if (/^(sector|sectorul|s)\s*[1-6]$/.test(f) || f.startsWith('bucuresti')) return countyByFold.get('bucuresti');
  const stripped = f.replace(/^(judetul|judet|jud)\s+/, '');
  if (countyByFold.has(stripped)) return countyByFold.get(stripped);
  // Edit distance 1-2 handles common typos ("Constanta" vs "Constata").
  let best = null;
  for (const c of COUNTIES) {
    const d = levenshtein(stripped, fold(c.name));
    if (d <= 2 && (!best || d < best.d)) best = { c, d };
  }
  return best?.c ?? null;
}

/** Extracts the București sector from any address field. */
export function findSector(...fields) {
  for (const v of fields) {
    const m = fold(v).match(/\b(?:sector(?:ul)?|sect|s)\s*([1-6])\b/);
    if (m) return Number(m[1]);
  }
  return null;
}

/** Normalizes Romanian phone numbers to 07xxxxxxxx / 02xxxxxxxx / 03xxxxxxxx. Foreign numbers kept as +CC... */
export function normalizePhone(input) {
  let d = String(input ?? '').replace(/[^\d+]/g, '');
  if (!d) return { phone: '', valid: false };
  if (d.startsWith('+40')) d = '0' + d.slice(3);
  else if (d.startsWith('0040')) d = '0' + d.slice(4);
  else if (d.startsWith('40') && d.length === 11) d = '0' + d.slice(2);
  else if (/^7\d{8}$/.test(d)) d = '0' + d;
  if (/^0[237]\d{8}$/.test(d)) return { phone: d, valid: true };
  if (d.startsWith('+') && d.length >= 10) return { phone: d, valid: true, foreign: true };
  return { phone: d, valid: false };
}

export function normalizeZip(input) {
  const z = String(input ?? '').replace(/\D/g, '');
  return { zip: z, valid: z.length === 6 };
}

/** Cleans a city string: "Mun. Cluj-Napoca" → "Cluj-Napoca"; București sectors → "București". */
export function cleanCity(city, county) {
  let c = String(city ?? '').trim().replace(/\s+/g, ' ');
  c = c.replace(/^(mun\.?|municipiul|oras(ul)?|oraș(ul)?|or\.|com\.?|comuna|sat(ul)?)\s+/i, '');
  if (county?.code === 'B' || /^bucure[sș]ti/i.test(fold(c)) || /^sector/i.test(fold(c))) return 'București';
  return c;
}

/**
 * Validates and normalizes a shipping address. Returns the normalized address plus
 * `issues`: { level: 'error'|'warning', code, field, message, hint }.
 * Errors block AWB generation; warnings are shown but don't block.
 */
export function validateAddress(addr = {}, { requireZip = false } = {}) {
  const issues = [];
  const add = (level, code, field, message, hint) => issues.push({ level, code, field, message, hint });

  const country = (addr.countryCode || 'RO').toUpperCase();
  const name = [addr.firstName, addr.lastName].filter(Boolean).join(' ').trim() || String(addr.name || '').trim();
  if (!name) add('error', 'ADDRESS_NAME_MISSING', 'shippingAddress.name', 'Lipsește numele destinatarului.', 'Completează numele în adresa de livrare.');

  if (country !== 'RO') {
    add('error', 'ADDRESS_FOREIGN', 'shippingAddress.country', `Adresa de livrare e în afara României (${country}).`, 'Livrările internaționale nu sunt încă suportate automat; procesează comanda manual.');
  }

  const county = findCounty(addr.provinceCode) || findCounty(addr.province) || findCounty(addr.city);
  if (!county) {
    const given = addr.province || addr.provinceCode;
    add('error', given ? 'ADDRESS_COUNTY_INVALID' : 'ADDRESS_COUNTY_MISSING', 'shippingAddress.province',
      given ? `Județul „${given}” nu e recunoscut.` : 'Lipsește județul.', 'Alege județul corect din listă.');
  }

  const city = cleanCity(addr.city, county);
  if (!city) add('error', 'ADDRESS_CITY_MISSING', 'shippingAddress.city', 'Lipsește localitatea.', 'Completează localitatea în adresa de livrare.');

  const street = [addr.address1, addr.address2].map((s) => String(s ?? '').trim()).filter(Boolean).join(', ');
  if (street.length < 3) {
    add('error', 'ADDRESS_STREET_MISSING', 'shippingAddress.address1', 'Lipsește strada.', 'Completează strada și numărul.');
  } else if (!/\d/.test(street) && !/\b(fn|f\.n\.|nr)\b/i.test(street)) {
    add('warning', 'ADDRESS_NO_NUMBER', 'shippingAddress.address1', 'Adresa nu conține un număr de stradă.', 'Verifică dacă e completă; la sate e normal să lipsească.');
  }

  let sector = null;
  if (county?.code === 'B') {
    sector = findSector(addr.city, addr.address1, addr.address2, addr.province, addr.zip);
    if (!sector) {
      const z = normalizeZip(addr.zip);
      // București postal codes: 0[1-6]xxxx → sector from the second digit.
      if (z.valid && /^0[1-6]/.test(z.zip)) sector = Number(z.zip[1]);
    }
    if (!sector) add('warning', 'ADDRESS_SECTOR_MISSING', 'shippingAddress.city', 'Nu am găsit sectorul pentru București.', 'Adaugă sectorul (ex. „Sector 3”) ca să ajungă coletul mai repede.');
  }

  const p = normalizePhone(addr.phone);
  if (!p.phone) add('error', 'ADDRESS_PHONE_MISSING', 'shippingAddress.phone', 'Lipsește telefonul destinatarului.', 'Curierii nu primesc AWB fără telefon. Adaugă-l în comandă.');
  else if (!p.valid) add('error', 'ADDRESS_PHONE_INVALID', 'shippingAddress.phone', `Telefonul „${addr.phone}” nu pare valid.`, 'Un număr românesc are 10 cifre și începe cu 07, 02 sau 03.');

  const z = normalizeZip(addr.zip);
  if (!z.zip && requireZip) add('error', 'ADDRESS_ZIP_MISSING', 'shippingAddress.zip', 'Lipsește codul poștal.', 'Curierul ales cere cod poștal. Îl găsești pe posta-romana.ro.');
  else if (z.zip && !z.valid) add('warning', 'ADDRESS_ZIP_INVALID', 'shippingAddress.zip', `Codul poștal „${addr.zip}” nu are 6 cifre.`, 'Verifică-l pe posta-romana.ro.');

  return {
    address: {
      name,
      company: String(addr.company ?? '').trim(),
      phone: p.phone,
      county: county?.name ?? '',
      countyCode: county?.code ?? '',
      city,
      sector,
      street,
      zip: z.valid ? z.zip : '',
      country,
    },
    issues,
  };
}

export function levenshtein(a, b) {
  if (a === b) return 0;
  const m = a.length, n = b.length;
  if (!m) return n;
  if (!n) return m;
  let prev = Array.from({ length: n + 1 }, (_, j) => j);
  for (let i = 1; i <= m; i++) {
    const cur = [i];
    for (let j = 1; j <= n; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = cur;
  }
  return prev[n];
}
