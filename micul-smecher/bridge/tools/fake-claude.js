#!/usr/bin/env node
// Stand-in for the `claude` binary in print mode (`claude -p --output-format json --json-schema ...`).
// Reads the prompt on stdin and prints one JSON result like Claude Code does.
// FAKE_CLAUDE_FAIL=not_logged_in simulates a user who has not signed in.
import { mockAnswer } from './mock-brain.js'

const args = process.argv.slice(2)
if (!args.includes('-p') || !args.includes('--json-schema')) { console.error('fake claude: expected -p --json-schema'); process.exit(2) }
if (args.includes('--bare')) { console.error('fake claude: --bare would skip the subscription login'); process.exit(2) }
let input = ''
process.stdin.on('data', (d) => (input += d))
process.stdin.on('end', () => {
  if (process.env.FAKE_CLAUDE_FAIL === 'not_logged_in') {
    console.log(JSON.stringify({ type: 'result', subtype: 'success', is_error: true, result: 'Not logged in · Please run /login' }))
    process.exit(1)
  }
  const q = (input.split('QUESTION FROM SOUL:\n')[1] || '').trim()
  const a = mockAnswer(q)
  console.log(JSON.stringify({ type: 'result', subtype: 'success', is_error: false, result: a.text, structured_output: a, session_id: 'fake', total_cost_usd: 0 }))
})
