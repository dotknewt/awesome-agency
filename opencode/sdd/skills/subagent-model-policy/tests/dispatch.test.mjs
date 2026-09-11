import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';

const path = new URL('../../../plugins/subagent-dispatch.ts', import.meta.url);
test('model-aware plugin exists', () => assert.ok(existsSync(path), 'missing dispatch plugin'));

if (existsSync(path)) {
  const { default: plugin } = await import(path.href);
  function deferred() {
    let resolve;
    let reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
  }
  /** @returns {import('@opencode-ai/sdk').UserMessage} */
  function userInfo({ id = 'user-1', agent = 'sdd-worker', modelID = 'gpt-6-astra', created = 1 } = {}) {
    return {
      id, sessionID: 'child', role: 'user', time: { created }, agent,
      model: { providerID: 'openai', modelID },
    };
  }
  /** @returns {import('@opencode-ai/sdk').AssistantMessage} */
  function assistantInfo({ id = 'assistant-1', parentID = 'user-1', modelID = 'gpt-6-astra', created = 2, error } = {}) {
    return {
      id, sessionID: 'child', role: 'assistant', time: { created, completed: created + 1 },
      error, parentID, modelID, providerID: 'openai', mode: 'sdd-worker',
      path: { cwd: '/tmp/opencode', root: '/tmp/opencode' }, cost: 0,
      tokens: { input: 1, output: 1, reasoning: 0, cache: { read: 0, write: 0 } },
      finish: error ? 'error' : 'stop',
    };
  }
  function completedHistory() {
    return [
      { info: userInfo(), parts: [] },
      { info: assistantInfo(), parts: [] },
    ];
  }
  function harness({
    actual,
    failure,
    parentID = 'parent',
    history = completedHistory(),
    childID = 'child',
    createDeferred,
    missingPromptResponse = false,
    promptDeferred,
    controller = new AbortController(),
  } = {}) {
    const calls = [];
    const createStarted = deferred();
    const promptStarted = deferred();
    const abortCalled = deferred();
    const client = {
      config: { providers: async () => ({ data: { providers: [{ id: 'openai', models: {
        'gpt-5.6-sol': {}, 'gpt-6-astra': {},
      } }] } }) },
      session: {
        create: async (x) => {
          calls.push(['create', x]);
          createStarted.resolve();
          if (createDeferred) await createDeferred.promise;
          return { data: { id: childID } };
        },
        get: async () => ({ data: { parentID } }),
        messages: async () => ({ data: history }),
        abort: async (x) => { calls.push(['abort', x]); abortCalled.resolve(); return { data: true }; },
        prompt: async (x) => {
          calls.push(['prompt', x]);
          promptStarted.resolve();
          if (promptDeferred) await promptDeferred.promise;
          if (missingPromptResponse) return { data: undefined };
          return { data: { info: { ...x.body.model, modelID: actual ?? x.body.model.modelID, error: failure }, parts: [{ type: 'text', text: 'DONE' }] } };
        },
      },
    };
    const context = { sessionID: 'parent', directory: '/tmp/opencode', abort: controller.signal,
      metadata() {}, ask: async (x) => calls.push(['ask', x]) };
    return { client, context, calls, controller, createStarted, promptStarted, abortCalled };
  }
  async function execute(h, args = {}) {
    const hooks = await plugin({ client: h.client });
    const output = await hooks.tool.subagent_dispatch.execute({ prompt: 'Do the task', description: 'Task', role: 'worker', ...args }, h.context);
    return JSON.parse(output);
  }
  async function run(args = {}, options) {
    const h = harness(options);
    return { ...h, result: await execute(h, args) };
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
    const history = [{ info: userInfo(), parts: [] }];
    const { result } = await run({ task_id: 'child', model: 'openai/gpt-5.6-sol' }, { history });
    assert.equal(result.model, 'openai/gpt-5.6-sol');
  });
  test('resume without a model rejects history with no assistant for the latest user', async () => {
    const history = [
      { info: userInfo({ id: 'user-old', modelID: 'gpt-5.6-sol' }), parts: [] },
      { info: assistantInfo({ id: 'assistant-old', parentID: 'user-old', modelID: 'gpt-5.6-sol' }), parts: [] },
      { info: userInfo({ id: 'user-latest', created: 4 }), parts: [] },
    ];
    await assert.rejects(run({ task_id: 'child' }, { history }), /assistant history.*model/i);
  });
  test('resume without a model rejects an aborted latest assistant', async () => {
    const history = [
      { info: userInfo(), parts: [] },
      { info: assistantInfo({ error: { name: 'MessageAbortedError', data: { message: 'cancelled' } } }), parts: [] },
    ];
    await assert.rejects(run({ task_id: 'child' }, { history }), /assistant history.*model/i);
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
  test('resume refuses a different role', async () => {
    await assert.rejects(run({ task_id: 'child', role: 'reviewer' }), /role mismatch/i);
  });
  test('malformed model is rejected before child creation', async () => {
    const h = harness();
    await assert.rejects(execute(h, { model: 'missing-provider' }), /provider\/model/);
    assert.equal(h.calls.some(([kind]) => kind === 'create'), false);
  });
  test('pre-aborted controller does not create a child', async () => {
    const controller = new AbortController();
    controller.abort();
    const h = harness({ controller });
    await assert.rejects(execute(h), /aborted/i);
    assert.equal(h.calls.some(([kind]) => kind === 'create'), false);
  });
  test('cancellation during child creation aborts it once its ID is available', async () => {
    const createDeferred = deferred();
    const h = harness({ createDeferred });
    const rejected = assert.rejects(execute(h), /aborted/i);
    await h.createStarted.promise;
    h.controller.abort();
    createDeferred.resolve();
    await rejected;
    assert.equal(h.calls.filter(([kind]) => kind === 'abort').length, 1);
    assert.equal(h.calls.some(([kind]) => kind === 'prompt'), false);
  });
  test('cancellation during an in-flight prompt aborts the child', async () => {
    const promptDeferred = deferred();
    const h = harness({ promptDeferred });
    const pending = execute(h);
    const rejected = assert.rejects(pending, /cancelled/i);
    await h.promptStarted.promise;
    h.controller.abort();
    await h.abortCalled.promise;
    promptDeferred.reject(new Error('cancelled'));
    await rejected;
    assert.equal(h.calls.filter(([kind]) => kind === 'abort').length, 1);
  });
  test('missing child ID is rejected', async () => {
    await assert.rejects(run({}, { childID: null }), /no ID/i);
  });
  test('missing prompt response is rejected', async () => {
    await assert.rejects(run({}, { missingPromptResponse: true }), /no response/i);
  });
  test('surfaces provider errors', async () => {
    await assert.rejects(run({}, { failure: { name: 'APIError', data: { message: 'unavailable upstream' } } }), /APIError/);
  });
}
