import { tool } from '@opencode-ai/plugin/tool';
import type { Plugin } from '@opencode-ai/plugin';

const DEFAULT_MODEL = 'openai/gpt-5.6-sol';

export default (async ({ client }) => ({
  tool: {
    subagent_dispatch: tool({
      description: 'Dispatch or resume an SDD child agent with an explicit model. Defaults to openai/gpt-5.6-sol; returns actual model and task_id. Use for model-controlled subagent work.',
      args: {
        description: tool.schema.string().min(1),
        prompt: tool.schema.string().min(1),
        role: tool.schema.enum(['worker', 'reviewer']).default('worker'),
        model: tool.schema.string().regex(/^[^/\s]+\/\S+$/).optional()
          .describe('Explicit provider/model override. On resume, omission preserves the previous model.'),
        task_id: tool.schema.string().optional().describe('Child session ID to resume; must belong to this controller.'),
      },
      async execute(args, context) {
        const agent = `sdd-${args.role}`;
        await context.ask({ permission: 'task', patterns: [agent], always: [agent], metadata: { description: args.description } });
        if (context.abort.aborted) throw new Error('Dispatch aborted');
        const query = { directory: context.directory };
        let selected = args.model;
        if (args.task_id) {
          const existing = await client.session.get({ path: { id: args.task_id }, query, throwOnError: true });
          if (existing.data?.parentID !== context.sessionID) throw new Error('Resume requires a direct child of this controller');
          const history = await client.session.messages({ path: { id: args.task_id }, query, throwOnError: true });
          const messages = history.data?.map(x => x.info) ?? [];
          const previousUserIndex = messages.findLastIndex(x => x.role === 'user');
          const previousUser = messages[previousUserIndex];
          if (!previousUser || previousUser.role !== 'user') throw new Error('Resume requires child user history');
          if (previousUser.agent !== agent) throw new Error('Resume role mismatch: create a fresh child for a different role');
          if (!selected) {
            const previousAssistant = messages.slice(previousUserIndex + 1).findLast(
              x => x.role === 'assistant' && x.parentID === previousUser.id,
            );
            if (!previousAssistant || previousAssistant.role !== 'assistant' || previousAssistant.error) {
              throw new Error('Resume without a model requires completed assistant history; specify model explicitly');
            }
            selected = `${previousAssistant.providerID}/${previousAssistant.modelID}`;
          }
        }
        selected ??= DEFAULT_MODEL;
        const slash = selected.indexOf('/');
        if (slash <= 0 || slash === selected.length - 1 || /\s/.test(selected)) throw new Error('Model must be provider/model');
        const model = { providerID: selected.slice(0, slash), modelID: selected.slice(slash + 1) };
        const catalog = await client.config.providers({ query, throwOnError: true });
        const provider = catalog.data?.providers.find(x => x.id === model.providerID);
        if (!provider || !Object.hasOwn(provider.models, model.modelID)) throw new Error(`Model unavailable: ${selected}`);
        const id = args.task_id ?? (await client.session.create({
          query, body: { parentID: context.sessionID, title: args.description }, throwOnError: true,
        })).data?.id;
        if (!id) throw new Error('Child session creation returned no ID');
        context.metadata({ title: args.description, metadata: { sessionId: id, model: selected, agent } });
        let abortSent = false;
        const abort = () => {
          if (abortSent) return;
          abortSent = true;
          void client.session.abort({ path: { id }, query }).catch(() => {});
        };
        context.abort.addEventListener('abort', abort, { once: true });
        try {
          if (context.abort.aborted) {
            abort();
            throw new Error('Dispatch aborted');
          }
          const result = await client.session.prompt({
            path: { id }, query, throwOnError: true, signal: context.abort,
            body: { agent, model, parts: [{ type: 'text', text: args.prompt }] },
          });
          if (!result.data) throw new Error('Child returned no response');
          if (result.data.info.error) throw new Error(JSON.stringify(result.data.info.error));
          const actual = `${result.data.info.providerID}/${result.data.info.modelID}`;
          if (actual !== selected) throw new Error(`Model mismatch: requested ${selected}, received ${actual}`);
          return JSON.stringify({ task_id: id, model: actual, agent,
            output: result.data.parts.filter(x => x.type === 'text').map(x => x.text).join('\n') });
        } catch (error) {
          throw new Error(`Child ${id} (${selected}): ${error instanceof Error ? error.message : String(error)}`);
        } finally {
          context.abort.removeEventListener('abort', abort);
        }
      },
    }),
  },
})) satisfies Plugin;
