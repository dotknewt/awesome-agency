import { spawn } from "node:child_process"
import { existsSync } from "node:fs"
import path from "node:path"

const DEFAULT_TIMEOUT = 5000
const SECRET_PATTERNS = [
  /<private>[\s\S]*?<\/private>/gi,
  /<private>[\s\S]*$/gi,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
  /\bsk-ant-[A-Za-z0-9_-]{16,}/g,
  /\bsk-[A-Za-z0-9_-]{16,}/g,
  /\bgh[pousr]_[A-Za-z0-9]{20,}/g,
  /\bgithub_pat_[A-Za-z0-9_]{20,}/g,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /\bxox[abprs]-[A-Za-z0-9-]{10,}/g,
  /\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g,
  /\bbearer\s+[A-Za-z0-9._~+/=-]{16,}/gi,
  /:\/\/[^/\s:@]+:[^@\s]+@/g,
]
const SECRET_KV = /(password|passwd|secret|token|api[_-]?key|apikey|access[_-]?key)(\s*[:=]\s*)['"]?[^\s'"]{6,}['"]?/gi

export function redact(value) {
  if (value === undefined || value === null) return ""
  let output = String(value)
  for (const pattern of SECRET_PATTERNS) {
    output = output.replace(pattern, (match) => {
      if (match.toLowerCase().startsWith("<private>")) return ""
      if (match.startsWith("://")) return "://[REDACTED]@"
      return "[REDACTED]"
    })
  }
  output = output.replace(SECRET_KV, "[REDACTED]")
  return output.replace(/<!--\s*generated:(start|end)\s*-->/gi, "<!- - generated:$1 - ->")
}

function mcpToolName(tool) {
  if (tool.startsWith("mcp__")) return tool
  const match = /^(?:mcp[_-])?([^_]+)_(write_note|update_frontmatter|patch_note|move_note|move_file|delete_note|manage_tags)$/.exec(tool)
  if (!match) return null
  return `mcp__${match[1]}__${match[2]}`
}

export function normalizeToolInput({ tool, args = {} }) {
  const name = String(tool || "")
  if (name === "write") {
    const { filePath, ...rest } = args
    return { tool_name: "Write", tool_input: { ...rest, file_path: filePath ?? args.file_path } }
  }
  if (name === "edit") {
    const { filePath, ...rest } = args
    return { tool_name: "Edit", tool_input: { ...rest, file_path: filePath ?? args.file_path } }
  }
  if (name === "apply_patch") return { tool_name: "apply_patch", tool_input: { ...args } }
  const mcp = mcpToolName(name)
  if (mcp) return { tool_name: mcp, tool_input: { ...args } }
  return { tool_name: name, tool_input: { ...args } }
}

export function normalizeSessionMessages(messages) {
  if (!Array.isArray(messages)) return []
  return messages
    .filter((message) => message && typeof message === "object")
    .map((message) => ({
      info: message.info ?? message,
      parts: Array.isArray(message.parts) ? message.parts : [],
    }))
}

function parseHookOutput(stdout, { strict = false } = {}) {
  return String(stdout || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line)
      } catch (error) {
        if (strict) throw new Error(`vault helper returned malformed JSON: ${error.message}`)
        return null
      }
    })
    .filter(Boolean)
}

async function runScript(script, args, input, directory, timeout = DEFAULT_TIMEOUT) {
  const command = script.endsWith(".mjs") ? process.execPath : "/bin/bash"
  const commandArgs = [script, ...args]
  return await new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: directory,
      env: { ...process.env, CLAUDE_PROJECT_DIR: directory },
      stdio: ["pipe", "pipe", "pipe"],
    })
    let stdout = ""
    let stderr = ""
    const timer = setTimeout(() => {
      child.kill("SIGTERM")
      reject(new Error("vault helper timed out"))
    }, timeout)
    child.stdout.on("data", (chunk) => { stdout += chunk })
    child.stderr.on("data", (chunk) => { stderr += chunk })
    child.on("error", (error) => {
      clearTimeout(timer)
      reject(new Error(redact(`vault helper failed: ${error.message}`)))
    })
    child.on("close", (code) => {
      clearTimeout(timer)
      if (code !== 0) {
        reject(new Error(redact(`vault helper failed: ${stderr || `exit ${code}`}`)))
        return
      }
      resolve({ stdout, stderr })
    })
    child.stdin.end(input)
  })
}

function isVaultPath(value, directory) {
  if (typeof value !== "string" || !value) return false
  const vault = path.resolve(directory, "vault")
  const absolute = path.resolve(directory, value)
  return absolute === vault || absolute.startsWith(`${vault}${path.sep}`)
}

function mcpVaultPath(value, directory) {
  if (typeof value !== "string" || !value) return null
  const vault = path.resolve(directory, "vault")
  const normalized = value.replace(/\\/g, "/").replace(/^\/+/, "")
  const absolute = path.resolve(vault, normalized)
  return absolute === vault || absolute.startsWith(`${vault}${path.sep}`) ? absolute : null
}

function isVaultCandidate(value, directory, toolName) {
  return toolName.startsWith("mcp__obsidian__")
    ? Boolean(mcpVaultPath(value, directory))
    : isVaultPath(value, directory)
}

function patchTargets(patchText) {
  const targets = []
  let current
  for (const line of String(patchText || "").split(/\r?\n/)) {
    let match = /^\*\*\* (Add File|Update File|Delete File): (.+)$/.exec(line)
    if (match) {
      current = { operation: match[1], filePath: match[2], content: "" }
      targets.push(current)
      continue
    }
    match = /^\*\*\* Move to: (.+)$/.exec(line)
    if (match && current) current.movePath = match[1]
    else if (current?.operation === "Add File" && line.startsWith("+")) current.content += `${line.slice(1)}\n`
  }
  return targets
}

function vaultPackage(runtime, runtimeRoot) {
  const entry = (runtime.entries || []).find((item) => item.name === "vault-memory")
  if (!entry?.package_root) return null
  return path.resolve(runtimeRoot, "..", entry.package_root)
}

export function getVaultPackage(runtime, runtimePath) {
  return vaultPackage(runtime, path.dirname(runtimePath))
}

export async function briefing({ packageRoot, directory, sessionID, timeout = DEFAULT_TIMEOUT }) {
  if (!packageRoot) return ""
  const script = path.join(packageRoot, "hooks", "session-start.sh")
  const result = await runScript(script, [], JSON.stringify({ source: "startup", session_id: sessionID }), directory, timeout)
  return redact(result.stdout || "").trim()
}

export async function validateBefore({ packageRoot, directory, tool, args, timeout = DEFAULT_TIMEOUT }) {
  if (!packageRoot) return
  const normalized = normalizeToolInput({ tool, args })
  const targets = normalized.tool_name === "apply_patch" ? patchTargets(normalized.tool_input.patchText) : []
  if (normalized.tool_name === "apply_patch") {
    for (const target of targets) {
      if (target.operation === "Delete File" && isVaultCandidate(target.filePath, directory, "Edit") && /\.md$/i.test(target.filePath)) {
        throw new Error("vault-lint: native apply_patch cannot delete vault notes; use mcp__obsidian__delete_note with trashMode:\"local\" after explicit user confirmation")
      }
    }
  }
  const operations = normalized.tool_name === "apply_patch"
    ? targets.flatMap((target) => [
        { tool_name: target.operation === "Add File" ? "Write" : "Edit", tool_input: { file_path: target.filePath, content: target.content } },
        ...(target.movePath ? [{ tool_name: "Edit", tool_input: { file_path: target.movePath } }] : []),
      ])
    : [normalized]
  if (normalized.tool_name === "apply_patch" && operations.length === 0) throw new Error("vault-lint: apply_patch contains no file targets")

  for (const operation of operations) {
    const candidates = [operation.tool_input.file_path, operation.tool_input.path, operation.tool_input.oldPath, operation.tool_input.newPath]
    if (operation.tool_name.startsWith("mcp__obsidian__")) {
      for (const candidate of [operation.tool_input.path, operation.tool_input.oldPath, operation.tool_input.newPath]) {
        if (candidate !== undefined && !mcpVaultPath(candidate, directory)) throw new Error("vault-lint: MCP path is outside the vault")
      }
    }
    if (!candidates.some((candidate) => isVaultCandidate(candidate, directory, operation.tool_name))) continue
    const scriptInput = JSON.stringify({
      tool_name: operation.tool_name,
      tool_input: operation.tool_input,
      cwd: directory,
      session_id: "opencode",
    })
    const result = await runScript(path.join(packageRoot, "hooks", "vault-lint.mjs"), ["pre"], scriptInput, directory, timeout)
    if (result.stderr.trim()) throw new Error(redact(`vault helper wrote to stderr: ${result.stderr}`))
    for (const message of parseHookOutput(result.stdout, { strict: true })) {
      const output = message.hookSpecificOutput
      if (output?.permissionDecision === "deny") throw new Error(redact(output.permissionDecisionReason || "vault-lint denied the write"))
    }
  }
}

export async function validateAfter({ packageRoot, directory, tool, args, output, timeout = DEFAULT_TIMEOUT }) {
  if (!packageRoot) return
  const normalized = normalizeToolInput({ tool, args })
  const targets = normalized.tool_name === "apply_patch" ? patchTargets(normalized.tool_input.patchText) : []
  const operations = normalized.tool_name === "apply_patch"
    ? targets.flatMap((target) => [
        { target, tool_name: target.operation === "Add File" ? "Write" : "Edit", tool_input: { file_path: target.filePath, content: target.content } },
        ...(target.movePath ? [{ target, tool_name: "Edit", tool_input: { file_path: target.movePath, oldPath: target.filePath } }] : []),
      ])
    : [{ target: null, tool_name: normalized.tool_name, tool_input: normalized.tool_input }]

  for (const operation of operations) {
    if (operation.target?.operation === "Delete File" && !existsSync(path.resolve(directory, operation.tool_input.file_path))) continue
    const candidates = [operation.tool_input.file_path, operation.tool_input.path, operation.tool_input.oldPath, operation.tool_input.newPath]
    if (!candidates.some((candidate) => isVaultCandidate(candidate, directory, operation.tool_name))) continue
    const result = await runScript(
      path.join(packageRoot, "hooks", "vault-lint.mjs"),
      ["post"],
      JSON.stringify({ tool_name: operation.tool_name, tool_input: operation.tool_input, cwd: directory }),
      directory,
      timeout,
    )
    if (result.stderr.trim()) throw new Error(redact(`vault helper wrote to stderr: ${result.stderr}`))
    const warnings = parseHookOutput(result.stdout)
      .map((message) => message.hookSpecificOutput?.additionalContext)
      .filter(Boolean)
      .map(redact)
    if (warnings.length && output) output.output = `${output.output || ""}\n\n${warnings.join("\n")}`.trim()
  }
}

export async function capture({ packageRoot, directory, sessionID, messages, mode = "stop", compactSummary = "", timeout = DEFAULT_TIMEOUT }) {
  if (!packageRoot || process.env.VAULT_SESSION_CAPTURE === "0") return
  const normalized = normalizeSessionMessages(messages)
  if (!normalized.length && mode === "stop") return
  const result = await runScript(
    path.join(packageRoot, "hooks", "session-capture.mjs"),
    [mode],
    JSON.stringify({ session_id: sessionID, cwd: directory, messages: normalized, compact_summary: compactSummary }),
    directory,
    timeout,
  )
  if (result.stderr.trim()) throw new Error(redact(`vault helper wrote to stderr: ${result.stderr}`))
}

export { patchTargets }
