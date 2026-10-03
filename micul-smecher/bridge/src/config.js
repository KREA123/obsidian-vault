// Bridge settings in ~/.soul-bridge/config.json (mode 0600).
// Holds only SOUL-side data: SOUL's address and the bridge token SOUL issued.
// Never a Claude credential: there is no field for one and save() refuses
// anything that looks like an Anthropic key or OAuth token.
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

export function homeDir() {
  return process.env.SOUL_BRIDGE_HOME || path.join(os.homedir(), '.soul-bridge')
}
export const configPath = () => path.join(homeDir(), 'config.json')
export const statusPath = () => path.join(homeDir(), 'status.json')

const ALLOWED = ['soul_url', 'token', 'device_id', 'soul_name', 'mode', 'model', 'timeout_s', 'via', 'cloud']
const FORBIDDEN = /sk-ant-|oauth|session[_-]?key|refresh[_-]?token|access[_-]?token/i

export function load() {
  try { return JSON.parse(fs.readFileSync(configPath(), 'utf8')) } catch { return {} }
}

export function save(cfg) {
  const clean = {}
  for (const k of ALLOWED) if (cfg[k] !== undefined) clean[k] = cfg[k]
  const s = JSON.stringify(clean, null, 2)
  if (FORBIDDEN.test(s.replace(/"token": "sbt_[^"]*"/, ''))) throw new Error('refusing to store something that looks like a Claude credential')
  fs.mkdirSync(homeDir(), { recursive: true, mode: 0o700 })
  fs.writeFileSync(configPath(), s + '\n', { mode: 0o600 })
  try { fs.chmodSync(configPath(), 0o600) } catch {}
  return clean
}

export function writeStatus(st) {
  try {
    fs.mkdirSync(homeDir(), { recursive: true, mode: 0o700 })
    fs.writeFileSync(statusPath(), JSON.stringify({ ...st, updated: new Date().toISOString() }, null, 2) + '\n')
  } catch {}
}

export function readStatus() {
  try { return JSON.parse(fs.readFileSync(statusPath(), 'utf8')) } catch { return null }
}
