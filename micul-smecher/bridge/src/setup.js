// `soul-bridge setup`: prepares a dedicated, empty folder where the user starts
// his own Claude Code with the SOUL channel. Nothing here touches Claude's
// login: the user signs in to Claude Code himself (`claude`, then /login).
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

export function workDir() {
  return process.env.SOUL_CLAUDE_DIR || path.join(os.homedir(), 'SOUL-Claude')
}

/** The command line the launcher runs (documented in docs/08-OWN-CLAUDE.md §3.1). */
export function launchArgs() {
  return [
    '--dangerously-load-development-channels', 'server:soul',
    // no built-in tools at all: a SOUL question can't run shell or touch files
    '--tools', '',
    // the reply tool needs no permission prompt
    '--allowedTools', 'mcp__soul__soul_reply', 'mcp__soul__soul_status',
    '--name', 'SOUL',
  ]
}

export function setup({ dir = workDir(), nodePath = process.execPath, binPath } = {}) {
  binPath = binPath || path.resolve(new URL('../bin/soul-bridge.js', import.meta.url).pathname)
  fs.mkdirSync(path.join(dir, '.claude'), { recursive: true })
  const mcp = { mcpServers: { soul: { command: nodePath, args: [binPath, 'channel'] } } }
  fs.writeFileSync(path.join(dir, '.mcp.json'), JSON.stringify(mcp, null, 2) + '\n')
  const settings = {
    // pre-approve only this project's SOUL server (avoids the "new MCP server" dialog)
    enabledMcpjsonServers: ['soul'],
    permissions: {
      allow: ['mcp__soul__soul_reply', 'mcp__soul__soul_status'],
      deny: ['Bash', 'Edit', 'Write', 'NotebookEdit', 'Read', 'WebFetch'],
    },
  }
  fs.writeFileSync(path.join(dir, '.claude', 'settings.json'), JSON.stringify(settings, null, 2) + '\n')
  fs.writeFileSync(path.join(dir, 'CLAUDE.md'),
    '# SOUL\n\nThis folder only exists so the SOUL channel can reach you. Questions from SOUL arrive as ' +
    '<channel source="soul"> events: answer each one with the soul_reply tool, briefly, in the question\'s language.\n')

  const args = launchArgs().map((a) => (a === '' ? '""' : a)).join(' ')
  const sh = `#!/bin/sh\n# Starts YOUR Claude Code (signed in by you) with the SOUL channel. Keep this window open.\ncd "${dir}" || exit 1\nexport MCP_PROTOCOL_NEGOTIATION=legacy\nexec claude ${args}\n`
  const cmd = `@echo off\r\nrem Starts YOUR Claude Code (signed in by you) with the SOUL channel. Keep this window open.\r\ncd /d "${dir}"\r\nset MCP_PROTOCOL_NEGOTIATION=legacy\r\nclaude ${args}\r\n`
  const files = {
    sh: path.join(dir, 'start-soul.sh'),
    command: path.join(dir, 'Start SOUL.command'), // double-click on macOS
    cmd: path.join(dir, 'Start SOUL.cmd'), // double-click on Windows
  }
  fs.writeFileSync(files.sh, sh, { mode: 0o755 })
  fs.writeFileSync(files.command, sh, { mode: 0o755 })
  fs.writeFileSync(files.cmd, cmd)
  return { dir, files, mcp, settings }
}
