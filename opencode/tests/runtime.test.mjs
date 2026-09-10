import test from "node:test"
import assert from "node:assert/strict"
import { mkdtemp, mkdir, readFile, writeFile, cp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { AwesomeAgency } from "../runtime/agency.js"
import {
  normalizeToolInput,
  normalizeSessionMessages,
  redact,
} from "../runtime/vault.js"

const here = path.dirname(fileURLToPath(import.meta.url))
const runtimeDir = path.resolve(here, "../runtime")

async function tempProject() {
  const root = await mkdtemp(path.join(tmpdir(), "awesome-agency-runtime-"))
  await mkdir(path.join(root, "vault", "sessions"), { recursive: true })
  await writeFile(path.join(root, "vault", "INDEX.md"), "---\ntype: index\ntitle: Project memory\n---\n\n# Project memory\n\n- Keep the current task visible.\n")
  return root
}

async function writeRuntime(root, entries) {
  const target = path.join(root, ".opencode")
  await mkdir(path.join(target, "awesome-agency", "runtime"), { recursive: true })
  await mkdir(path.join(target, "plugins"), { recursive: true })
  await cp(runtimeDir, path.join(target, "awesome-agency", "runtime"), { recursive: true })
  await writeFile(
    path.join(target, "awesome-agency", "runtime.json"),
    JSON.stringify({ version: 1, project_context: "runtime", entries, mcp: {} }),
  )
  await writeFile(
    path.join(target, "plugins", "awesome-agency.js"),
    'export { AwesomeAgency } from "../awesome-agency/runtime/agency.js"\n',
  )
  return target
}

async function writeVaultRuntime(root, entries = []) {
  const packageRoot = path.join(root, "vault-package")
  await mkdir(path.join(packageRoot, "hooks"), { recursive: true })
  for (const name of ["session-start.sh", "session-capture.mjs", "vault-lint.mjs"]) {
    await cp(path.join(here, "../../plugins/vault-memory/hooks", name), path.join(packageRoot, "hooks", name))
  }
  return writeRuntime(root, [...entries, entry("vault-memory", "../vault-package")])
}

function sdk(messages, session = {}) {
  const calls = []
  return {
    calls,
    session: {
      async get(input) {
        calls.push(["get", input])
        return { data: session }
      },
      async messages(input) {
        calls.push(["messages", input])
        return { data: await (typeof messages === "function" ? messages() : messages) }
      },
    },
    app: {
      async log(input) {
        calls.push(["log", input])
      },
    },
  }
}

function entry(name, packageRoot) {
  return {
    name,
    kind: "bundle",
    version: "1.0.0",
    package_root: packageRoot,
    contribution: { mcp: {} },
  }
}

test("only selected Superpowers injects one system instruction", async () => {
  const root = await tempProject()
  try {
    const target = await writeRuntime(root, [entry("other", "awesome-agency/packages/bundles/other")])
    const inactive = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency", "runtime.json") })
    const inactiveOutput = { system: [] }
    await inactive["experimental.chat.system.transform"]({ sessionID: "s" }, inactiveOutput)
    assert.equal(inactiveOutput.system.length, 0)

    await writeFile(
      path.join(target, "awesome-agency", "runtime.json"),
      JSON.stringify({ version: 1, entries: [entry("superpowers", "awesome-agency/packages/bundles/superpowers")], mcp: {} }),
    )
    const active = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency", "runtime.json") })
    const output = { system: ["existing"] }
    await active["experimental.chat.system.transform"]({ sessionID: "s" }, output)
    await active["experimental.chat.system.transform"]({ sessionID: "s" }, output)
    assert.equal(output.system.filter((item) => item.includes("awesome-agency:superpowers")).length, 1)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("vault briefing uses the active project and is restored after compaction", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency", "runtime.json") })

    const first = { system: [] }
    await plugin["experimental.chat.system.transform"]({ sessionID: "s" }, first)
    assert.match(first.system.join("\n"), /<vault-briefing[^>]*>/)

    await plugin.event({ event: { type: "session.compacted", properties: { sessionID: "s" } } })
    const after = { system: [] }
    await plugin["experimental.chat.system.transform"]({ sessionID: "s" }, after)
    assert.match(after.system.join("\n"), /<vault-briefing[^>]*>/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("duplicate factories share capture state and prefer project-local bundle roots", async () => {
  const project = await tempProject()
  const globalRoot = await tempProject()
  try {
    const globalTarget = await writeRuntime(globalRoot, [entry("superpowers", "awesome-agency/packages/bundles/superpowers")])
    const projectTarget = await writeVaultRuntime(project)
    await mkdir(path.join(globalRoot, "vault-package", "hooks"), { recursive: true })
    await writeFile(path.join(globalRoot, "vault-package", "hooks", "session-start.sh"), "printf '<vault-briefing source=global>global</vault-briefing>\\n'")
    await writeFile(path.join(project, "vault-package", "hooks", "session-start.sh"), "printf '<vault-briefing source=project>project</vault-briefing>\\n'")
    const globalRuntime = path.join(globalTarget, "awesome-agency", "runtime.json")
    const localRuntime = path.join(projectTarget, "awesome-agency", "runtime.json")
    const firstClient = sdk([{ info: { role: "assistant", id: "a", sessionID: "s", time: { created: 1725840000000 }, providerID: "openai", modelID: "gpt", tokens: { input: 1, output: 1, cache: {} } }, parts: [{ type: "text", text: "answer" }] }])
    const secondClient = sdk([])
    const first = await AwesomeAgency({ directory: project, project: { id: "p" }, client: firstClient, runtimePath: globalRuntime })
    const second = await AwesomeAgency({ directory: project, project: { id: "p" }, client: secondClient, runtimePath: localRuntime })

    const firstSystem = { system: [] }
    await first["experimental.chat.system.transform"]({ sessionID: "s" }, firstSystem)
    assert.match(firstSystem.system.join("\n"), /source=project/)
    assert.match(firstSystem.system.join("\n"), /awesome-agency:superpowers/)
    await Promise.all([
      first.event({ event: { type: "session.idle", properties: { sessionID: "s" } } }),
      second.event({ event: { type: "session.idle", properties: { sessionID: "s" } } }),
    ])
    assert.equal(firstClient.calls.filter(([name]) => name === "messages").length + secondClient.calls.filter(([name]) => name === "messages").length, 2)

    await first.dispose()
    await second.dispose()
    const thirdClient = sdk([{ info: { role: "assistant", id: "a", sessionID: "s", time: { created: 1725840000000 }, providerID: "openai", modelID: "gpt", tokens: { input: 1, output: 1, cache: {} } }, parts: [{ type: "text", text: "answer" }] }])
    const third = await AwesomeAgency({ directory: project, project: { id: "p" }, client: thirdClient, runtimePath: localRuntime })
    await third.event({ event: { type: "session.idle", properties: { sessionID: "s" } } })
    assert.equal(thirdClient.calls.filter(([name]) => name === "messages").length, 1)
    await third.dispose()
  } finally {
    await rm(project, { recursive: true, force: true })
    await rm(globalRoot, { recursive: true, force: true })
  }
})

test("native and MCP vault writes are denied before execution and unrelated tools pass through", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const before = plugin["tool.execute.before"]
    await assert.rejects(
      before({ tool: "write", sessionID: "s", callID: "c" }, { args: { filePath: path.join(root, "vault", "bad note.md"), content: "secret: sk-ant-1234567890123456" } }),
      /vault-lint|kebab|filename/i,
    )
    await assert.rejects(
      before({ tool: "mcp__obsidian__write_note", sessionID: "s", callID: "c" }, { args: { path: "kb/new-note.md", content: "not frontmatter" } }),
      /frontmatter/i,
    )
    for (const filePath of ["./vault/bad name.md", `../${path.basename(root)}/vault/bad name.md`]) {
      await assert.rejects(
        before({ tool: "write", sessionID: "s", callID: "c" }, { args: { filePath, content: "not frontmatter" } }),
        /kebab|filename|frontmatter|root|taxonomy/i,
      )
    }
    await assert.rejects(
      before({ tool: "obsidian_write_note", sessionID: "s", callID: "c" }, { args: { path: "/kb/bad name.md", content: "not frontmatter" } }),
      /kebab|filename|frontmatter/i,
    )
    await assert.rejects(
      before({ tool: "obsidian_move_note", sessionID: "s", callID: "c" }, { args: { oldPath: "/kb/bad name.md", newPath: "../outside.md" } }),
      /kebab|filename|vault/i,
    )
    const unrelated = { args: { filePath: path.join(root, "vault", "bad note.md") } }
    await before({ tool: "read", sessionID: "s", callID: "c" }, unrelated)
    assert.equal(unrelated.args.filePath.endsWith("bad note.md"), true)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("apply_patch validates every file and rename target", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const validPatch = [
      "*** Begin Patch",
      "*** Add File: vault/kb/first-note.md",
      "+---",
      "+type: kb",
      "+title: First",
      "+---",
      "+body",
      "*** Add File: vault/kb/second-note.md",
      "+---",
      "+type: kb",
      "+title: Second",
      "+---",
      "+body",
      "*** End Patch",
    ].join("\n")
    await plugin["tool.execute.before"]({ tool: "apply_patch", sessionID: "s", callID: "c" }, { args: { patchText: validPatch } })
    const patch = [
      "*** Begin Patch",
      "*** Add File: vault/kb/good-note.md",
      "+---",
      "+type: kb",
      "+title: Good",
      "+description: Good",
      "+status: active",
      "+created: 2026-09-09",
      "+updated: 2026-09-09",
      "+tags: [good]",
      "+kind: fact",
      "+importance: 3",
      "+confidence: unverified",
      "+review_after: 2027-01-01",
      "+evidence: []",
      "+---",
      "+body",
      "*** Update File: vault/kb/good-note.md",
      "*** Move to: vault/kb/bad note.md",
      "@@",
      "-body",
      "+changed",
      "*** End Patch",
    ].join("\n")
    await assert.rejects(
      plugin["tool.execute.before"]({ tool: "apply_patch", sessionID: "s", callID: "c" }, { args: { patchText: patch } }),
      /vault-lint|kebab|filename|rename/i,
    )
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("apply_patch post validation checks additions, updates, and rename destinations", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const logPath = path.join(root, "post-patch.log")
    await writeFile(path.join(root, "vault-package", "hooks", "vault-lint.mjs"), [
      'import { readFileSync, appendFileSync } from "node:fs"',
      'const input = JSON.parse(readFileSync(0, "utf8"))',
      'appendFileSync(process.env.VAULT_POST_PATCH_LOG, JSON.stringify(input.tool_input) + "\\n")',
      'console.log(JSON.stringify({ hookSpecificOutput: { additionalContext: "post-patch warning" } }))',
    ].join("\n"))
    const previous = process.env.VAULT_POST_PATCH_LOG
    process.env.VAULT_POST_PATCH_LOG = logPath
    try {
      const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
      const patch = [
        "*** Begin Patch",
        "*** Add File: vault/kb/added-note.md",
        "*** Update File: vault/kb/updated-note.md",
        "*** Move to: vault/kb/renamed-note.md",
        "*** Delete File: vault/kb/missing-note.md",
        "*** End Patch",
      ].join("\n")
      const output = { output: "written" }
      await plugin["tool.execute.after"]({ tool: "apply_patch", args: { patchText: patch } }, output)
      const calls = (await readFile(logPath, "utf8")).trim().split("\n").map(line => JSON.parse(line))
      assert.deepEqual(calls.map(call => call.file_path), [
        "vault/kb/added-note.md",
        "vault/kb/updated-note.md",
        "vault/kb/renamed-note.md",
      ])
      assert.equal(calls[2].oldPath, "vault/kb/updated-note.md")
      assert.equal((output.output.match(/post-patch warning/g) || []).length, 3)
    } finally {
      if (previous === undefined) delete process.env.VAULT_POST_PATCH_LOG
      else process.env.VAULT_POST_PATCH_LOG = previous
    }
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("native apply_patch deletion of a vault note is denied with recoverable deletion guidance", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const patch = "*** Begin Patch\n*** Delete File: vault/kb/existing-note.md\n*** End Patch"
    await assert.rejects(
      plugin["tool.execute.before"]({ tool: "apply_patch" }, { args: { patchText: patch } }),
      /mcp__obsidian__delete_note|trashMode.*local/i,
    )
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("native apply_patch only validates paths resolved inside the vault", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const callsPath = path.join(root, "validator-calls.log")
    await writeFile(path.join(root, "vault-package", "hooks", "vault-lint.mjs"), [
      'import { appendFileSync } from "node:fs"',
      'appendFileSync(process.env.VAULT_VALIDATOR_CALLS, "called\\n")',
    ].join("\n"))
    const previous = process.env.VAULT_VALIDATOR_CALLS
    process.env.VAULT_VALIDATOR_CALLS = callsPath
    try {
      const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
      const outsidePatch = "*** Begin Patch\n*** Delete File: README.md\n*** Delete File: docs/note.md\n*** End Patch"
      await plugin["tool.execute.before"]({ tool: "apply_patch" }, { args: { patchText: outsidePatch } })
      await assert.rejects(
        plugin["tool.execute.before"]({ tool: "apply_patch" }, { args: { patchText: "*** Begin Patch\n*** Delete File: vault/kb/note.md\n*** End Patch" } }),
        /mcp__obsidian__delete_note|trashMode.*local/i,
      )
      await plugin["tool.execute.before"]({ tool: "write" }, { args: { filePath: "./vault/note.md", content: "not frontmatter" } })
      assert.equal(await readFile(callsPath, "utf8"), "called\n")
    } finally {
      if (previous === undefined) delete process.env.VAULT_VALIDATOR_CALLS
      else process.env.VAULT_VALIDATOR_CALLS = previous
    }
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("post validation appends warnings to OpenCode tool output", async () => {
  const root = await tempProject()
  try {
    await mkdir(path.join(root, "vault", "kb"), { recursive: true })
    await writeFile(path.join(root, "vault", "kb", "note.md"), "---\ntype: kb\ntitle: Note\ndescription: Note\nstatus: active\ncreated: 2026-09-09\nupdated: 2026-09-09\ntags: [note]\nkind: fact\nimportance: 3\nconfidence: unverified\nreview_after: 2027-01-01\nevidence: []\n---\n[[missing-note]]\n")
    const target = await writeVaultRuntime(root)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const output = { output: "written", title: "ok", metadata: {} }
    await plugin["tool.execute.after"]({ tool: "write", sessionID: "s", callID: "c", args: { filePath: path.join(root, "vault/kb/note.md") } }, output)
    assert.match(output.output, /vault-lint|missing-note/)
    assert.doesNotMatch(output.output, /sk-ant-|api[_-]?key/i)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("post validation surfaces redacted helper stderr as a warning", async () => {
  const root = await tempProject()
  try {
    await mkdir(path.join(root, "vault", "kb"), { recursive: true })
    await writeFile(path.join(root, "vault", "kb", "note.md"), "---\ntype: kb\ntitle: Note\n---\nbody\n")
    const target = await writeVaultRuntime(root)
    await writeFile(path.join(root, "vault-package", "hooks", "vault-lint.mjs"), "process.stderr.write('secret=sk-ant-1234567890123456\\n')\n")
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const output = { output: "written", title: "ok", metadata: {} }
    await plugin["tool.execute.after"]({ tool: "write", sessionID: "s", callID: "c", args: { filePath: path.join(root, "vault/kb/note.md") } }, output)
    assert.match(output.output, /awesome-agency warning|vault helper wrote to stderr/)
    assert.doesNotMatch(output.output, /sk-ant-|secret=/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("clean post validation preserves the original output", async () => {
  const root = await tempProject()
  try {
    await mkdir(path.join(root, "vault", "kb"), { recursive: true })
    await writeFile(path.join(root, "vault", "kb", "note.md"), "---\ntype: kb\ntitle: Note\ndescription: Note\nstatus: active\ncreated: 2026-09-09\nupdated: 2026-09-09\ntags: [note]\nkind: fact\nimportance: 3\nconfidence: unverified\nreview_after: 2027-01-01\nevidence: []\n---\nbody\n")
    const target = await writeVaultRuntime(root)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const output = { output: "written", title: "ok", metadata: {} }
    await plugin["tool.execute.after"]({ tool: "write", sessionID: "s", callID: "c", args: { filePath: path.join(root, "vault/kb/note.md") } }, output)
    assert.deepEqual(output, { output: "written", title: "ok", metadata: {} })
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("pre validation fails closed on helper stderr and malformed output", async () => {
  for (const helper of [
    "process.stderr.write('token=sk-ant-1234567890123456\\n')",
    "console.log('not json')",
  ]) {
    const root = await tempProject()
    try {
      const target = await writeVaultRuntime(root)
      await writeFile(path.join(root, "vault-package", "hooks", "vault-lint.mjs"), `${helper}\n`)
      const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk([]), runtimePath: path.join(target, "awesome-agency/runtime.json") })
      await assert.rejects(
        plugin["tool.execute.before"]({ tool: "write", sessionID: "s", callID: "c" }, { args: { filePath: "vault/kb/note.md", content: "---\ntype: kb\n---\n" } }),
        /helper|malformed|invalid|vault-lint/i,
      )
    } finally {
      await rm(root, { recursive: true, force: true })
    }
  }
})

test("SDK capture is project/session isolated, redacted, curated, and remains open on idle", async () => {
  const root = await tempProject()
  const other = await tempProject()
  try {
    const makeMessages = (sessionID) => [
      {
        info: { id: "u1", sessionID, role: "user", time: { created: 1725840000000 }, agent: "build", model: { providerID: "openai", modelID: "gpt" } },
        parts: [{ id: "p1", sessionID, messageID: "u1", type: "text", text: "Remember <private>hide me</private> token=super-secret" }],
      },
      {
        info: { id: "a1", sessionID, role: "assistant", time: { created: 1725840001000 }, modelID: "gpt", providerID: "openai", tokens: { input: 7, output: 3, reasoning: 0, cache: { read: 2, write: 1 } } },
        parts: [{ id: "p2", sessionID, messageID: "a1", type: "text", text: "captured" }],
      },
    ]
    let messages = makeMessages("s1")
    const client = sdk(() => messages)
    const target = await writeVaultRuntime(root)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p1" }, client, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const first = await plugin.event({ event: { type: "session.idle", properties: { sessionID: "s1" } } })
    assert.equal(first, undefined)
    const note = (await readFile(path.join(root, "vault/sessions/2024-09-09--session-s1.md"), "utf8"))
    assert.match(note, /status: open/)
    assert.match(note, /tokens_in: 8/)
    assert.doesNotMatch(note, /hide me|super-secret/)
    assert.match(note, /## Summary/)
    assert.equal(client.calls.filter(([name]) => name === "messages").length, 1)

    messages = [...messages,
      {
        info: { id: "u2", sessionID: "s1", role: "user", time: { created: 1725840002000 } },
        parts: [{ id: "p3", sessionID: "s1", messageID: "u2", type: "text", text: "Second turn" }],
      },
      {
        info: { id: "a2", sessionID: "s1", role: "assistant", time: { created: 1725840003000 }, modelID: "gpt", providerID: "openai", tokens: { input: 4, output: 2, cache: {} } },
        parts: [{ id: "p4", sessionID: "s1", messageID: "a2", type: "text", text: "second answer" }],
      },
    ]
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "s1" } } })
    const updatedNote = await readFile(path.join(root, "vault/sessions/2024-09-09--session-s1.md"), "utf8")
    assert.match(updatedNote, /prompts: 2/)
    assert.match(updatedNote, /second answer/)
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "s1" } } })
    assert.equal(client.calls.filter(([name]) => name === "messages").length, 3)

    const isolated = sdk(makeMessages("s1"))
    const otherTarget = await writeVaultRuntime(other)
    const otherPlugin = await AwesomeAgency({ directory: other, project: { id: "p2" }, client: isolated, runtimePath: path.join(otherTarget, "awesome-agency/runtime.json") })
    await otherPlugin.event({ event: { type: "session.idle", properties: { sessionID: "s1" } } })
    assert.equal(client.calls.filter(([name]) => name === "messages").length, 3)
    assert.equal(isolated.calls.filter(([name]) => name === "messages").length, 1)
  } finally {
    await rm(root, { recursive: true, force: true })
    await rm(other, { recursive: true, force: true })
  }
})

test("native apply_patch capture stamps added plan files", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    await mkdir(path.join(root, "vault", "plans"), { recursive: true })
    await writeFile(path.join(root, "vault", "plans", "new-plan.md"), "# New plan\n\nPlan body\n")
    const messages = [{
      info: { id: "patch", sessionID: "patch", role: "assistant", time: { created: 1725840000000 }, providerID: "openai", modelID: "gpt", tokens: { input: 1, output: 1, cache: {} } },
      parts: [{
        id: "tool", sessionID: "patch", messageID: "patch", type: "tool", tool: "apply_patch", state: {
          status: "completed",
          input: { patchText: "*** Begin Patch\n*** Add File: vault/plans/new-plan.md\n+# New plan\n*** End Patch" },
        },
      }],
    }]
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: sdk(messages), runtimePath: path.join(target, "awesome-agency/runtime.json") })
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "patch" } } })
    const note = await readFile(path.join(root, "vault/sessions/2024-09-09--session-patch.md"), "utf8")
    const plan = await readFile(path.join(root, "vault/plans/new-plan.md"), "utf8")
    assert.match(note, /vault\/plans\/new-plan\.md/)
    assert.match(note, /\[\[new-plan\]\]/)
    assert.match(plan, /^type: plan$/m)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("OpenCode MCP capture records both move endpoints and plan ownership", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const messages = [{
      info: { id: "m", sessionID: "mcp", role: "assistant", time: { created: 1725840000000 }, providerID: "openai", modelID: "gpt", tokens: { input: 1, output: 1, cache: {} } },
      parts: [
        { id: "w", sessionID: "mcp", messageID: "m", type: "tool", tool: "obsidian_write_note", state: { status: "completed", input: { path: "/plans/plan.md", content: "x" } } },
        { id: "mv", sessionID: "mcp", messageID: "m", type: "tool", tool: "obsidian_move_note", state: { status: "completed", input: { oldPath: "/plans/old-plan.md", newPath: "/plans/new-plan.md" } } },
      ],
    }]
    const client = sdk(messages)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "mcp" } } })
    const note = await readFile(path.join(root, "vault/sessions/2024-09-09--session-mcp.md"), "utf8")
    assert.match(note, /vault\/plans\/plan\.md/)
    assert.match(note, /vault\/plans\/old-plan\.md/)
    assert.match(note, /vault\/plans\/new-plan\.md/)
    assert.match(note, /\[\[plan\]\]/)
    assert.match(note, /\[\[old-plan\]\]/)
    assert.match(note, /\[\[new-plan\]\]/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("capture helper failure is logged and retried on the next idle event", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const capturePath = path.join(root, "vault-package", "hooks", "session-capture.mjs")
    await writeFile(capturePath, "process.stderr.write('secret=sk-ant-1234567890123456\\n'); process.exit(1)\n")
    const client = sdk([{ info: { id: "a", sessionID: "retry", role: "assistant", time: { created: 1725840000000 }, providerID: "openai", modelID: "gpt", tokens: { input: 1, output: 1, cache: {} } }, parts: [{ type: "text", text: "answer" }] }])
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "retry" } } })
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "retry" } } })
    assert.equal(client.calls.filter(([name]) => name === "messages").length, 2)
    const logs = client.calls.filter(([name]) => name === "log").map(([, value]) => JSON.stringify(value)).join("\n")
    assert.match(logs, /awesome-agency capture/)
    assert.doesNotMatch(logs, /sk-ant-|secret=/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("capture helper stderr with exit 0 is logged and retried on the next idle event", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const capturePath = path.join(root, "vault-package", "hooks", "session-capture.mjs")
    await writeFile(capturePath, "process.stderr.write('secret=sk-ant-1234567890123456\\n')\n")
    const client = sdk([{ info: { id: "a", sessionID: "retry-zero", role: "assistant", time: { created: 1725840000000 }, providerID: "openai", modelID: "gpt", tokens: { input: 1, output: 1, cache: {} } }, parts: [{ type: "text", text: "answer" }] }])
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "retry-zero" } } })
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "retry-zero" } } })
    assert.equal(client.calls.filter(([name]) => name === "messages").length, 2)
    const logs = client.calls.filter(([name]) => name === "log").map(([, value]) => JSON.stringify(value)).join("\n")
    assert.match(logs, /awesome-agency capture/)
    assert.doesNotMatch(logs, /sk-ant-|secret=/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("capture skips opt-out, empty sessions, and child sessions", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const emptyClient = sdk([], { id: "s", parentID: "parent" })
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client: emptyClient, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    await plugin.event({ event: { type: "session.idle", properties: { sessionID: "s" } } })
    assert.equal(emptyClient.calls.filter(([name]) => name === "messages").length, 0)
    assert.equal((await readFile(path.join(root, "vault/sessions"), { encoding: "utf8" }).catch(() => "")), "")
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("compaction capture keeps a checkpoint and opt-out skips SDK reads", async () => {
  const root = await tempProject()
  try {
    const target = await writeVaultRuntime(root)
    const messages = [
      {
        info: { id: "cu", sessionID: "compact", role: "user", time: { created: 1725840000000 }, agent: "build", model: { providerID: "openai", modelID: "gpt" } },
        parts: [{ id: "cp", sessionID: "compact", messageID: "cu", type: "compaction" }, { id: "ct", sessionID: "compact", messageID: "cu", type: "text", text: "Compaction checkpoint summary" }],
      },
      {
        info: { id: "ca", sessionID: "compact", role: "assistant", time: { created: 1725840001000 }, summary: true, modelID: "gpt", providerID: "openai", tokens: { input: 1, output: 1, reasoning: 0, cache: { read: 0, write: 0 } } },
        parts: [{ id: "cap", sessionID: "compact", messageID: "ca", type: "text", text: "Compaction checkpoint summary" }],
      },
    ]
    const client = sdk(messages)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    await plugin.event({ event: { type: "session.compacted", properties: { sessionID: "compact" } } })
    const note = await readFile(path.join(root, "vault/sessions/2024-09-09--session-compact.md"), "utf8")
    assert.match(note, /post-compact/)
    assert.match(note, /Compaction checkpoint summary/)

    messages.push({
      info: { id: "cu2", sessionID: "compact", role: "user", time: { created: 1725840002000 } },
      parts: [{ id: "cp2", sessionID: "compact", messageID: "cu2", type: "compaction" }, { id: "ct2", sessionID: "compact", messageID: "cu2", type: "text", text: "Second compaction checkpoint" }],
    })
    messages.push({
      info: { id: "ca2", sessionID: "compact", role: "assistant", time: { created: 1725840003000 }, summary: true, modelID: "gpt", providerID: "openai", tokens: { input: 1, output: 1, cache: {} } },
      parts: [{ id: "cap2", sessionID: "compact", messageID: "ca2", type: "text", text: "Second compaction checkpoint" }],
    })
    await plugin.event({ event: { type: "session.compacted", properties: { sessionID: "compact" } } })
    const updated = await readFile(path.join(root, "vault/sessions/2024-09-09--session-compact.md"), "utf8")
    assert.match(updated, /Second compaction checkpoint/)
    assert.equal((updated.match(/post-compact/g) || []).length, 2)

    const optOutClient = sdk(messages)
    const optOut = await AwesomeAgency({ directory: root, project: { id: "p2" }, client: optOutClient, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const previous = process.env.VAULT_SESSION_CAPTURE
    process.env.VAULT_SESSION_CAPTURE = "0"
    try {
      await optOut.event({ event: { type: "session.idle", properties: { sessionID: "optout" } } })
    } finally {
      if (previous === undefined) delete process.env.VAULT_SESSION_CAPTURE
      else process.env.VAULT_SESSION_CAPTURE = previous
    }
    assert.equal(optOutClient.calls.length, 0)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("vault adapters normalize OpenCode native and MCP tool payloads", () => {
  assert.deepEqual(normalizeToolInput({ tool: "write", args: { filePath: "vault/kb/note.md", content: "x" } }), {
    tool_name: "Write",
    tool_input: { file_path: "vault/kb/note.md", content: "x" },
  })
  assert.deepEqual(normalizeToolInput({ tool: "obsidian_write_note", args: { path: "kb/note.md", content: "x" } }), {
    tool_name: "mcp__obsidian__write_note",
    tool_input: { path: "kb/note.md", content: "x" },
  })
  assert.equal(redact("sk-ant-1234567890123456"), "[REDACTED]")
  assert.equal(normalizeSessionMessages([{ info: { role: "user" }, parts: [] }]).length, 1)
})

test("unchanged capture events do not rewrite, but a new message version does", async () => {
  const root = await tempProject()
  const previous = process.env.VAULT_CAPTURE_COUNT
  try {
    const target = await writeVaultRuntime(root)
    const countPath = path.join(root, "capture-count.log")
    process.env.VAULT_CAPTURE_COUNT = countPath
    await writeFile(path.join(root, "vault-package", "hooks", "session-capture.mjs"), [
      'import { appendFileSync } from "node:fs"',
      'appendFileSync(process.env.VAULT_CAPTURE_COUNT, "capture\\n")',
    ].join("\n"))
    let messages = [{ info: { id: "a", sessionID: "dedup", role: "assistant", time: { created: 1725840000000 } }, parts: [{ type: "text", text: "one" }] }]
    const client = sdk(() => messages)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const idle = () => plugin.event({ event: { type: "session.idle", properties: { sessionID: "dedup" } } })
    await idle()
    await idle()
    messages = [...messages, { info: { id: "b", sessionID: "dedup", role: "assistant", time: { created: 1725840001000 } }, parts: [{ type: "text", text: "two" }] }]
    await idle()
    await idle()
    assert.equal((await readFile(countPath, "utf8")).trim().split("\n").length, 2)
  } finally {
    if (previous === undefined) delete process.env.VAULT_CAPTURE_COUNT
    else process.env.VAULT_CAPTURE_COUNT = previous
    await rm(root, { recursive: true, force: true })
  }
})

test("a new idle event during capture is coalesced without losing the newest message list", async () => {
  const root = await tempProject()
  const previous = {
    started: process.env.VAULT_CAPTURE_STARTED,
    release: process.env.VAULT_CAPTURE_RELEASE,
    log: process.env.VAULT_CAPTURE_LOG,
  }
  try {
    const target = await writeVaultRuntime(root)
    const started = path.join(root, "capture-started")
    const release = path.join(root, "capture-release")
    const log = path.join(root, "capture-messages.log")
    Object.assign(process.env, { VAULT_CAPTURE_STARTED: started, VAULT_CAPTURE_RELEASE: release, VAULT_CAPTURE_LOG: log })
    await writeFile(path.join(root, "vault-package", "hooks", "session-capture.mjs"), [
      'import { readFileSync, appendFileSync, existsSync, writeFileSync } from "node:fs"',
      'const input = JSON.parse(readFileSync(0, "utf8"))',
      'writeFileSync(process.env.VAULT_CAPTURE_STARTED, "started")',
      'while (!existsSync(process.env.VAULT_CAPTURE_RELEASE)) await new Promise(resolve => setTimeout(resolve, 5))',
      'appendFileSync(process.env.VAULT_CAPTURE_LOG, `${input.messages.length}\\n`)',
    ].join("\n"))
    let messages = [
      { info: { id: "a", sessionID: "race", role: "assistant", time: { created: 1725840000000 } }, parts: [{ type: "text", text: "one" }] },
    ]
    const client = sdk(() => messages)
    const plugin = await AwesomeAgency({ directory: root, project: { id: "p" }, client, runtimePath: path.join(target, "awesome-agency/runtime.json") })
    const first = plugin.event({ event: { type: "session.idle", properties: { sessionID: "race" } } })
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { await readFile(started); break } catch { await new Promise(resolve => setTimeout(resolve, 5)) }
    }
    messages = [...messages, { info: { id: "b", sessionID: "race", role: "assistant", time: { created: 1725840001000 } }, parts: [{ type: "text", text: "two" }] }]
    const second = plugin.event({ event: { type: "session.idle", properties: { sessionID: "race" } } })
    await writeFile(release, "release")
    await Promise.all([first, second])
    assert.deepEqual((await readFile(log, "utf8")).trim().split("\n"), ["1", "2"])
  } finally {
    for (const [name, value] of Object.entries(previous)) {
      const key = `VAULT_CAPTURE_${name.toUpperCase()}`
      if (value === undefined) delete process.env[key]
      else process.env[key] = value
    }
    await rm(root, { recursive: true, force: true })
  }
})
