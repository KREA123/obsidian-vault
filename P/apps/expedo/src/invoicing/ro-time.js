// Dates for invoicing providers are always Romanian calendar dates (Europe/Bucharest), never UTC.
// new Date().toISOString().slice(0, 10) is the previous day between 00:00 and 03:00 local time.

const TZ = 'Europe/Bucharest';
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

function parts(d) {
  const out = {};
  for (const p of new Intl.DateTimeFormat('en-GB', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).formatToParts(d)) out[p.type] = p.value;
  return out;
}

function toDate(input) {
  if (input instanceof Date) return input;
  const d = new Date(String(input));
  return Number.isNaN(d.getTime()) ? null : d;
}

/** 'YYYY-MM-DD' in Bucharest. A plain date string is trusted as-is; timestamps are converted. */
export function bucharestDay(input = new Date()) {
  if (typeof input === 'string' && DATE_ONLY.test(input.trim())) return input.trim();
  const d = toDate(input);
  if (!d) return String(input).slice(0, 10);
  const p = parts(d);
  return `${p.year}-${p.month}-${p.day}`;
}

/**
 * 'YYYY-MM-DD HH:mm:ss' in Bucharest. A plain date that is today gets the current local time (a payment
 * registered "today" must not predate the invoice issued a moment ago); another plain date gets 00:00:00.
 */
export function bucharestDateTime(input, now = new Date()) {
  if (input == null || input === '') input = now;
  if (typeof input === 'string' && DATE_ONLY.test(input.trim())) {
    const day = input.trim();
    if (day !== bucharestDay(now)) return `${day} 00:00:00`;
    input = now;
  }
  const d = toDate(input);
  if (!d) return String(input).slice(0, 19);
  const p = parts(d);
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
}
