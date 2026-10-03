// Stand-in for a running Claude Code session with the SOUL channel loaded:
// spawns `soul-bridge channel` over stdio exactly as Claude Code would, checks
// the channel capability, receives notifications/claude/channel events and
// answers each one through the soul_reply tool (using the mock brain).
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { mockAnswer } from './mock-brain.js'

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'soul-bridge.js')

export async function startFakeClaudeCode({ env, onEvent } = {}) {
  const transport = new StdioClientTransport({ command: process.execPath, args: [BIN, 'channel'], env: { ...process.env, ...env }, stderr: 'pipe' })
  const client = new Client({ name: 'fake-claude-code', version: '0.0.0' }, { capabilities: {} })
  const events = []
  client.fallbackNotificationHandler = async (n) => {
    if (n.method !== 'notifications/claude/channel') return
    const { content, meta } = n.params
    events.push(n.params)
    onEvent?.(n.params)
    const a = mockAnswer(content)
    await client.callTool({ name: 'soul_reply', arguments: { question_id: meta.question_id, text: a.text, actions: a.actions } })
  }
  await client.connect(transport)
  const caps = client.getServerCapabilities()
  if (!caps?.experimental?.['claude/channel']) throw new Error('server did not declare claude/channel')
  return { client, events, instructions: client.getInstructions(), caps, close: () => client.close() }
}
