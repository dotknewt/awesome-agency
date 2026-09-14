import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';

const path = new URL('../../../plugins/subagent-dispatch.ts', import.meta.url);
test('model-aware plugin exists', () => assert.ok(existsSync(path), 'missing dispatch plugin'));

if (existsSync(path)) {
  const { default: plugin } = await import(path.href);
  function harness({ actual, failure, parentID = 'parent' } = {}) {
    const calls = [];
    const client = {
      config: { providers: async () => ({ data: { providers: [{ id: 'openai', models: {
        'gpt-5.6-sol': {}, 'gpt-6-astra': {},
      } }] } }) },
      session: {
        create: async (x) => { calls.push(['create', x]); return { data: { id: 'child' } }; },
        get: async () => ({ data: { parentID } }),
        messages: async () => ({ data: [{ info: { role: 'assistant', agent: 'sdd-worker', providerID: 'openai', modelID: 'gpt-6-astra' } }] }),
        abort: async () => ({ data: true }),
        prompt: async (x) => {
          calls.push(['prompt', x]);
          return { data: { info: { ...x.body.model, modelID: actual ?? x.body.model.modelID, error: failure }, parts: [{ type: 'text', text: 'DONE' }] } };
        },
      },
    };
    const context = { sessionID: 'parent', directory: '/tmp/opencode', abort: new AbortController().signal,
      metadata() {}, ask: async (x) => calls.push(['ask', x]) };
    return { client, context, calls };
  }
  async function run(args = {}, options) {
    const h = harness(options);
    const hooks = await plugin({ client: h.client });
    const output = await hooks.tool.subagent_dispatch.execute({ prompt: 'Do the task', description: 'Task', role: 'worker', ...args }, h.context);
    return { ...h, result: JSON.parse(output) };
  }
  test('default dispatch sends Sol to SDK and reports actual identity', async () => {
    const { result, calls } = await run();
    assert.equal(result.model, 'openai/gpt-5.6-sol');
    assert.equal(result.task_id, 'child');
    assert.equal(result.output, 'DONE');
    assert.equal(calls.find(([k]) => k === 'create')[1].body.parentID, 'parent');
    assert.equal(calls.find(([k]) => k === 'prompt')[1].body.model.modelID, 'gpt-5.6-sol');
    assert.equal(calls[0][0], 'ask');
  });
  test('explicit model and reviewer role reach SDK', async () => {
    const { result, calls } = await run({ model: 'openai/gpt-6-astra', role: 'reviewer' });
    assert.equal(result.model, 'openai/gpt-6-astra');
    assert.equal(calls.find(([k]) => k === 'prompt')[1].body.agent, 'sdd-reviewer');
  });
  test('resume preserves previous model when override omitted', async () => {
    const { result, calls } = await run({ task_id: 'child' });
    assert.equal(result.model, 'openai/gpt-6-astra');
    assert.equal(calls.some(([k]) => k === 'create'), false);
  });
  test('resume accepts explicit model override', async () => {
    const { result } = await run({ task_id: 'child', model: 'openai/gpt-5.6-sol' });
    assert.equal(result.model, 'openai/gpt-5.6-sol');
  });
  test('unavailable model cannot silently fall back', async () => {
    await assert.rejects(run({ model: 'openai/missing' }), /unavailable/i);
  });
  test('rejects model identity mismatch', async () => {
    await assert.rejects(run({}, { actual: 'gpt-6-astra' }), /mismatch/i);
  });
  test('rejects unrelated session resume', async () => {
    await assert.rejects(run({ task_id: 'foreign' }, { parentID: 'someone-else' }), /child/i);
  });
  test('surfaces provider errors', async () => {
    await assert.rejects(run({}, { failure: { name: 'APIError', data: { message: 'unavailable upstream' } } }), /APIError/);
  });
}
