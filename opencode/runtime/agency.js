import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import {
  briefing,
  capture,
  getVaultPackage,
  validateAfter,
  validateBefore,
} from "./vault.js"

const DEFAULT_RUNTIME_PATH = fileURLToPath(new URL("../runtime.json", import.meta.url))
const SUPERPOWERS_MARKER = "<!-- awesome-agency:superpowers -->"
const BRIEFING_MARKER = "<vault-briefing"
const REGISTRY_KEY = Symbol.for("awesome-agency.opencode.registry")

function registry() {
  return globalThis[REGISTRY_KEY] || (globalThis[REGISTRY_KEY] = new Map())
}

function deepEqual(left, right) {
  if (left === right) return true
  if (!left || !right || typeof left !== "object" || typeof right !== "object") return false
  if (Array.isArray(left) !== Array.isArray(right)) return false
  const leftKeys = Object.keys(left).sort()
  const rightKeys = Object.keys(right).sort()
  if (leftKeys.length !== rightKeys.length || leftKeys.some((key, index) => key !== rightKeys[index])) return false
  return leftKeys.every((key) => deepEqual(left[key], right[key]))
}

function stableSerialize(value) {
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(",")}]`
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key])}`).join(",")}}`
  }
  return JSON.stringify(value)
}

function resolveValue(value, runtimeRoot, directory) {
  if (Array.isArray(value)) return value.map((item) => resolveValue(item, runtimeRoot, directory))
  if (!value || typeof value !== "object") {
    if (typeof value !== "string") return value
    let resolved = value.replace(/\{env:([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, name) => process.env[name] ?? "")
    resolved = resolved.replaceAll("{project}", directory)
    resolved = resolved.replace(/\{package_root:([^}]+)\}/g, (_, relative) => path.resolve(runtimeRoot, "..", relative))
    return resolved
  }
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, resolveValue(item, runtimeRoot, directory)]))
}

function readRuntime(runtimePath) {
  if (!existsSync(runtimePath)) return { version: 1, entries: [], mcp: {} }
  const runtime = JSON.parse(readFileSync(runtimePath, "utf8"))
  return runtime && typeof runtime === "object" ? runtime : { version: 1, entries: [], mcp: {} }
}

function mergedRuntime(directory, runtimePath) {
  const localPath = path.join(directory, ".opencode", "awesome-agency", "runtime.json")
  const paths = [...new Set([runtimePath, localPath])].filter((candidate) => existsSync(candidate))
  const entries = new Map()
  const mcp = {}
  for (const candidate of paths) {
    const root = path.dirname(candidate)
    const current = readRuntime(candidate)
    for (const entry of current.entries || []) {
      entries.set(entry.name, {
        ...entry,
        package_root: entry.package_root && path.isAbsolute(entry.package_root)
          ? entry.package_root
          : path.resolve(root, "..", entry.package_root || ""),
      })
    }
    for (const [name, value] of Object.entries(current.mcp || {})) mcp[name] = resolveValue(value, root, directory)
  }
  return { version: 1, entries: [...entries.values()], mcp }
}

function selected(runtime, name) {
  return (runtime.entries || []).some((entry) => entry.name === name)
}

function safeMessage(error) {
  return String(error instanceof Error ? error.message : error).replace(/[\r\n]+/g, " ").slice(0, 500)
}

export async function AwesomeAgency(context) {
  const directory = path.resolve(context.directory)
  const runtimePath = context.runtimePath || DEFAULT_RUNTIME_PATH
  const runtimeRoot = path.dirname(runtimePath)
  const key = directory
  const shared = registry()
  let state = shared.get(key)
  if (!state) {
    const runtime = mergedRuntime(directory, runtimePath)
    state = {
      runtime,
      packageRoot: getVaultPackage(runtime, runtimePath),
      briefed: new Set(),
      captures: new Map(),
      references: 0,
    }
    shared.set(key, state)
  } else {
    state.runtime = mergedRuntime(directory, runtimePath)
    state.packageRoot = getVaultPackage(state.runtime, runtimePath)
  }
  state.references += 1
  const { runtime, packageRoot, briefed } = state

  async function log(level, error) {
    const message = `awesome-agency ${level}: ${safeMessage(error)}`
    try {
      await context.client?.app?.log?.({ body: { service: "awesome-agency", level: "error", message } })
    } catch {
      process.stderr.write(`${message}\n`)
    }
  }

  async function sessionData(sessionID) {
    const session = await context.client.session.get({ path: { id: sessionID }, query: { directory } })
    const info = session?.data ?? session
    if (info?.parentID) return null
    const result = await context.client.session.messages({ path: { id: sessionID }, query: { directory } })
    return { info, messages: result?.data ?? result ?? [] }
  }

  async function captureOnce(sessionID, mode, compactSummary = "") {
    if (!state.packageRoot || process.env.VAULT_SESSION_CAPTURE === "0") return
    const key = `${directory}\u0000${sessionID}\u0000${mode}`
    const captureState = state.captures.get(key) || { lastVersion: null, pending: false, task: null }
    state.captures.set(key, captureState)
    if (captureState.task) {
      captureState.pending = true
      return captureState.task
    }
    const task = (async () => {
      while (true) {
        captureState.pending = false
        const data = await sessionData(sessionID)
        if (!data) return
        const version = stableSerialize({ messages: data.messages, compactSummary })
        if (version !== captureState.lastVersion) {
          await capture({
            packageRoot: state.packageRoot,
            directory,
            sessionID,
            messages: data.messages,
            mode,
            compactSummary,
          })
          captureState.lastVersion = version
        }
        if (!captureState.pending) return
      }
    })().catch((error) => log("capture", error)).finally(() => { captureState.task = null })
    captureState.task = task
    return task
  }

  async function addBriefing(sessionID, output) {
    const key = sessionID || "__no-session__"
    if (!packageRoot || briefed.has(key)) return
    const text = await briefing({ packageRoot, directory, sessionID })
    if (text && !output.system.some((item) => String(item).includes(BRIEFING_MARKER))) output.system.push(text)
    briefed.add(key)
  }

  return {
    async config(config) {
      config.mcp ??= {}
      for (const [name, value] of Object.entries(runtime.mcp || {})) {
        const resolved = resolveValue(value, runtimeRoot, directory)
        if (config.mcp[name] !== undefined) {
          deepEqual(config.mcp[name], resolved)
          continue
        }
        config.mcp[name] = resolved
      }
    },

    async event({ event }) {
      if (event.type === "session.idle") {
        await captureOnce(event.properties.sessionID, "stop")
        return
      }
      if (event.type === "session.compacted") {
        const sessionID = event.properties.sessionID
        briefed.delete(sessionID)
        await captureOnce(sessionID, "postcompact")
      }
    },

    async "experimental.chat.system.transform"(input, output) {
      if (selected(runtime, "superpowers") && !output.system.some((item) => String(item).includes(SUPERPOWERS_MARKER))) {
        output.system.push(`${SUPERPOWERS_MARKER}\nUse the selected Superpowers skills when their trigger conditions apply.`)
      }
      if (!packageRoot) return
      try {
        await addBriefing(input.sessionID, output)
      } catch (error) {
        await log("briefing", error)
      }
    },

    async "experimental.session.compacting"(input, output) {
      if (!packageRoot) return
      try {
        const text = await briefing({ packageRoot, directory, sessionID: input.sessionID })
        if (text && !output.context.some((item) => String(item).includes(BRIEFING_MARKER))) output.context.push(text)
      } catch (error) {
        await log("compaction", error)
      }
    },

    async "tool.execute.before"(input, output) {
      try {
        await validateBefore({ packageRoot, directory, tool: input.tool, args: output.args })
      } catch (error) {
        throw new Error(safeMessage(error))
      }
    },

    async "tool.execute.after"(input, output) {
      try {
        await validateAfter({ packageRoot, directory, tool: input.tool, args: input.args, output })
      } catch (error) {
        output.output = `${output.output || ""}\n\n[awesome-agency warning] ${safeMessage(error)}`.trim()
      }
    },

    async dispose() {
      state.references -= 1
      if (state.references <= 0) shared.delete(key)
    },
  }
}
