// The "mocked Claude": deterministic answers so tests do not need a signed-in
// Claude Code. Real answers come from the user's own Claude.
export function mockAnswer(text) {
  const t = text.toLowerCase()
  const wake = t.match(/(?:trezește-mă|trezeste-ma|wake me)\D*(\d{1,2})(?::(\d{2}))?/)
  if (wake) {
    const hh = wake[1].padStart(2, '0'); const mm = wake[2] || '00'
    return { text: `Gata, te trezesc la ${hh}:${mm}.`, actions: [{ type: 'alarm.set', args: { hhmm: `${hh}:${mm}`, days: [], label: '' } }] }
  }
  const rem = t.match(/(?:amintește-mi|aminteste-mi|remind me)\s+(.*?)\s+(?:la|at)\s+(\d{1,2})(?::(\d{2}))?/)
  if (rem) {
    const hh = rem[2].padStart(2, '0'); const mm = rem[3] || '00'
    return { text: `Îți amintesc la ${hh}:${mm}.`, actions: [{ type: 'reminder.create', args: { when: `2026-10-03T${hh}:${mm}`, text: rem[1] } }] }
  }
  if (t.includes('invalid')) return { text: 'Test cu o acțiune greșită.', actions: [{ type: 'alarm.set', args: { hhmm: '25:99' } }] }
  return { text: `(mock Claude) Ai întrebat: ${text}`, actions: [] }
}
