#!/usr/bin/env node
// The mocked Claude Code as a process, for end-to-end runs driven from another language (ai/tools/e2e_bridge.py):
// it spawns the REAL `soul-bridge channel` over stdio exactly as Claude Code does, and answers every SOUL question
// with the mock brain through the soul_reply tool. No model is called, no Claude account is involved.
//   stdout: READY {tools} | EVENT {meta} (one line per question pushed into the "session")
//   stdin closed / SIGTERM -> closes the session (the channel exits, SOUL sees the computer go offline)
import { startFakeClaudeCode } from './fake-claude-code.js'

const cc = await startFakeClaudeCode({ onEvent: (p) => console.log('EVENT ' + JSON.stringify({ ...p.meta, content: p.content })) })
const tools = (await cc.client.listTools()).tools.map((t) => t.name)
console.log('READY ' + JSON.stringify({ tools, channel: !!cc.caps.experimental?.['claude/channel'] }))
let closing = false
const stop = async () => {
  if (closing) return
  closing = true
  try { await cc.close() } catch {}
  process.exit(0)
}
process.stdin.on('end', stop)
process.stdin.resume()
process.on('SIGTERM', stop)
process.on('SIGINT', stop)
