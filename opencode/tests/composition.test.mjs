import test from "node:test"
import assert from "node:assert/strict"
import { mkdtemp, mkdir, readFile, rm, lstat } from "node:fs/promises"
import { spawnSync } from "node:child_process"
import path from "node:path"
import { pathToFileURL, fileURLToPath } from "node:url"

const here = path.dirname(fileURLToPath(import.meta.url))
const opencodeRoot = path.resolve(here, "..")
const repositoryRoot = path.resolve(opencodeRoot, "..")

test("generated plugin composes runtime hooks with the model-aware dispatcher", async () => {
  // Keep the temporary target below opencode/ so the repository's pinned test SDK
  // is available to tsx. The generated artifacts themselves are copied files and
  // use only target-relative imports.
  const root = await mkdtemp(path.join(opencodeRoot, ".composition-"))
  const project = path.join(root, "project")
  let hooks
  await mkdir(project)
  try {
    const installed = spawnSync(
      process.env.PYTHON || "python3",
      [path.join(opencodeRoot, "install.py"), "install", "doublecheck", "--project", project],
      {
        cwd: repositoryRoot,
        encoding: "utf8",
        env: {
          ...process.env,
          HOME: path.join(root, "home"),
          XDG_CONFIG_HOME: path.join(root, "config"),
          XDG_DATA_HOME: path.join(root, "data"),
          XDG_CACHE_HOME: path.join(root, "cache"),
          XDG_STATE_HOME: path.join(root, "state"),
        },
      },
    )
    assert.equal(installed.status, 0, installed.stderr)

    const target = path.join(project, ".opencode")
    const artifacts = [
      "plugins/awesome-agency.js",
      "awesome-agency/runtime/agency.js",
      "awesome-agency/runtime/vault.js",
      "awesome-agency/runtime/subagent-dispatch.ts",
    ]
    for (const relative of artifacts) {
      const artifact = path.join(target, relative)
      assert.equal((await lstat(artifact)).isSymbolicLink(), false, `${relative} must be copied`)
      assert.equal((await readFile(artifact, "utf8")).includes(repositoryRoot), false, `${relative} must not import the source checkout`)
    }

    const { default: factory } = await import(pathToFileURL(path.join(target, "plugins/awesome-agency.js")))
    const calls = []
    const client = {
      app: { log: async () => {} },
      config: {
        providers: async () => ({ data: { providers: [{ id: "openai", models: { "gpt-5.6-sol": {} } }] } }),
      },
      session: {
        create: async (input) => { calls.push(["create", input]); return { data: { id: "child-task" } } },
        abort: async () => ({ data: true }),
        prompt: async (input) => {
          calls.push(["prompt", input])
          return {
            data: {
              info: { providerID: input.body.model.providerID, modelID: input.body.model.modelID },
              parts: [{ type: "text", text: "done" }],
            },
          }
        },
      },
    }
    hooks = await factory({ directory: project, project: { id: "project" }, client })
    assert.equal(typeof hooks.config, "function")
    assert.equal(typeof hooks["tool.execute.before"], "function")
    assert.deepEqual(Object.keys(hooks.tool), ["subagent_dispatch"])

    const result = JSON.parse(await hooks.tool.subagent_dispatch.execute(
      { prompt: "Do the task", description: "Task", role: "worker" },
      {
        sessionID: "parent",
        directory: project,
        abort: new AbortController().signal,
        ask: async (input) => calls.push(["ask", input]),
        metadata: (input) => calls.push(["metadata", input]),
      },
    ))
    assert.equal(result.model, "openai/gpt-5.6-sol")
    assert.equal(result.task_id, "child-task")
    assert.deepEqual(calls.find(([kind]) => kind === "prompt")[1].body.model, {
      providerID: "openai",
      modelID: "gpt-5.6-sol",
    })
  } finally {
    await hooks?.dispose?.()
    await rm(root, { recursive: true, force: true })
  }
})
