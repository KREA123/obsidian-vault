// SOUL actions the bridge may send back with an answer.
// Mirrors ai/suflet_ai/actions.py (names, fields, limits). SOUL validates again
// on its side; the bridge validates first so a bad action never leaves the PC.

const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/
const WHEN = /^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d$/

const str = (min, max, re) => ({ kind: 'str', min, max, re })
const int = (min, max) => ({ kind: 'int', min, max })
const strList = (min, max, itemMax, enumVals) => ({ kind: 'list', min, max, itemMax, enumVals })
const oneOf = (vals) => ({ kind: 'enum', vals })

// field spec: [validator, defaultValue|undefined (undefined = required)]
export const ACTIONS = {
  'note.create': {
    description: 'Save a note on SOUL.',
    fields: { text: [str(1, 2000)], tags: [strList(0, 10, 40), []] },
  },
  'reminder.create': {
    description: 'Reminder at a local date-time YYYY-MM-DDTHH:MM (compute it from the question\'s `now`).',
    fields: { when: [str(16, 16, WHEN)], text: [str(1, 300)] },
  },
  'alarm.set': {
    description: 'Wake-up alarm, 24h HH:MM; days [] = once.',
    fields: { hhmm: [str(5, 5, HHMM)], days: [strList(0, 7, 3, DAYS), []], label: [str(0, 60), ''] },
  },
  'timer.start': {
    description: 'Countdown timer in seconds.',
    fields: { seconds: [int(1, 86400)], label: [str(0, 60), ''] },
  },
  'focus.start': {
    description: 'Focus session in minutes.',
    fields: { minutes: [int(1, 240)], label: [str(0, 60), ''] },
  },
  'message.draft': {
    description: 'Draft a message the user reviews and sends from the phone (SOUL never sends it).',
    fields: { to: [str(1, 80)], text: [str(1, 1000)], channel: [oneOf(['any', 'sms', 'whatsapp', 'email']), 'any'] },
  },
  'list.add': {
    description: 'Add items to a named list.',
    fields: { list: [str(1, 40)], items: [strList(1, 30, 200)] },
  },
  'answer.show': {
    description: 'Keep the answer on SOUL\'s round screen as a card.',
    fields: { say: [str(1, 400)], title: [str(0, 60), ''], body: [str(0, 600), ''] },
  },
}

export const MAX_ACTIONS = 5
export const MAX_TEXT = 1200

function checkField(name, spec, v) {
  switch (spec.kind) {
    case 'str': {
      if (typeof v !== 'string') return `${name} must be a string`
      const s = v.trim()
      if (s.length < spec.min || s.length > spec.max) return `${name} length must be ${spec.min}..${spec.max}`
      if (spec.re && !spec.re.test(s)) return `${name} has the wrong format`
      return null
    }
    case 'int':
      if (!Number.isInteger(v) || v < spec.min || v > spec.max) return `${name} must be an integer ${spec.min}..${spec.max}`
      return null
    case 'enum':
      return spec.vals.includes(v) ? null : `${name} must be one of ${spec.vals.join('|')}`
    case 'list': {
      if (!Array.isArray(v)) return `${name} must be a list`
      if (v.length < spec.min || v.length > spec.max) return `${name} must have ${spec.min}..${spec.max} entries`
      for (const it of v) {
        if (typeof it !== 'string' || !it.trim() || it.length > spec.itemMax) return `${name} entries must be short strings`
        if (spec.enumVals && !spec.enumVals.includes(it)) return `${name} entries must be in ${spec.enumVals.join('|')}`
      }
      return null
    }
  }
  return `${name}: unknown spec`
}

/** Validate one action {type, args}. Returns {ok:true, action} (normalized) or {ok:false, error}. */
export function validateAction(a) {
  if (!a || typeof a !== 'object' || Array.isArray(a)) return { ok: false, error: 'action must be an object' }
  const spec = ACTIONS[a.type]
  if (!spec) return { ok: false, error: `unknown action type: ${String(a.type).slice(0, 40)}` }
  const args = a.args && typeof a.args === 'object' && !Array.isArray(a.args) ? a.args : {}
  const extra = Object.keys(args).filter((k) => !(k in spec.fields))
  if (extra.length) return { ok: false, error: `${a.type}: unknown field(s) ${extra.join(', ')}` }
  const out = {}
  for (const [name, [check, dflt]] of Object.entries(spec.fields)) {
    let v = args[name]
    if (v === undefined) {
      if (dflt === undefined) return { ok: false, error: `${a.type}: ${name} is required` }
      v = dflt
    }
    const err = checkField(name, check, v)
    if (err) return { ok: false, error: `${a.type}: ${err}` }
    out[name] = typeof v === 'string' ? v.trim() : v
  }
  return { ok: true, action: { type: a.type, args: out } }
}

/** Validate a list of actions; keeps the valid ones, reports the rest. */
export function validateActions(list) {
  const ok = []
  const rejected = []
  if (list === undefined || list === null) return { ok, rejected }
  if (!Array.isArray(list)) return { ok, rejected: [{ index: -1, error: 'actions must be a list' }] }
  list.slice(0, MAX_ACTIONS).forEach((a, index) => {
    const r = validateAction(a)
    if (r.ok) ok.push(r.action)
    else rejected.push({ index, error: r.error })
  })
  if (list.length > MAX_ACTIONS) rejected.push({ index: MAX_ACTIONS, error: `at most ${MAX_ACTIONS} actions per answer` })
  return { ok, rejected }
}

/** JSON Schema of an answer: used for the soul_reply tool and for `claude -p --json-schema`. */
export function answerSchema({ withQuestionId }) {
  const props = {
    text: { type: 'string', description: 'The answer SOUL shows/says: short, plain text, same language as the question (<= 2-3 sentences).' },
    actions: {
      type: 'array',
      description: 'Optional SOUL actions. [] if none. Types: ' +
        Object.entries(ACTIONS).map(([k, v]) => `${k} {${Object.keys(v.fields).join(', ')}}: ${v.description}`).join(' | '),
      items: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: Object.keys(ACTIONS) },
          args: { type: 'object', description: 'Fields for this action type (see the list above).' },
        },
        required: ['type', 'args'],
      },
    },
  }
  const required = ['text', 'actions']
  if (withQuestionId) {
    props.question_id = { type: 'string', description: 'The question_id attribute of the <channel> tag you are answering.' }
    required.unshift('question_id')
  }
  return { type: 'object', properties: props, required }
}
