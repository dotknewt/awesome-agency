export const meta = {
  name: 'vault-research',
  description: 'Research a question across web sources: one vault-researcher per URL writes a vault/sources note with provenance and claims; the vault-curator merges verified claims into vault/kb (search-before-create) and links the sources',
  whenToUse: 'When a question needs several external sources captured with provenance, or to (re)ingest a list of URLs into vault/sources.',
  phases: [
    { title: 'Discover', detail: 'find authoritative URLs (skipped when args.urls is given)' },
    { title: 'Ingest', detail: 'one source note per URL (pipeline)' },
    { title: 'Synthesize', detail: 'vault-curator promotes verified claims into kb' },
  ],
}

// args: { question?: string, urls?: string[], maxSources?: number, writeKb?: boolean }  (or a plain question string)
const question = typeof args === 'string' ? args : ((args && args.question) || '')
const max = (args && args.maxSources) || 6
const writeKb = !(args && args.writeKb === false)
let urls = (args && Array.isArray(args.urls)) ? args.urls.slice(0, max) : []
if (!question && !urls.length) return 'vault-research: pass args {question} and/or {urls:[...]}'

if (!urls.length) {
  phase('Discover')
  const plan = await agent(`Find the ${max} most authoritative sources for: "${question}". Prefer primary/official docs, specs, source code, papers; then reputable secondary sources. Use WebSearch with several phrasings.
Also check what the vault already has: mcp__obsidian__search_notes {query:"<key terms>", pathPrefix:"sources", limit:10} and list those paths in already_ingested (skip their URLs). Do not write anything.
Return {urls:[{url, why}], already_ingested:[paths]}.`,
    { label: 'discover sources', phase: 'Discover', agentType: 'vault-researcher',
      schema: { type: 'object', required: ['urls'], properties: { urls: { type: 'array', items: { type: 'object', required: ['url'], properties: { url: { type: 'string' }, why: { type: 'string' } } } }, already_ingested: { type: 'array', items: { type: 'string' } } } } })
  urls = ((plan && plan.urls) || []).map(u => u.url).slice(0, max)
  log(`vault-research: ${urls.length} URL(s) to ingest`)
}

const SOURCE_SCHEMA = { type: 'object', required: ['path', 'claims'], properties: {
  path: { type: 'string' }, title: { type: 'string' }, reliability: { type: 'string' },
  claims: { type: 'array', items: { type: 'object', required: ['claim', 'confidence'], properties: {
    claim: { type: 'string' }, confidence: { type: 'string', enum: ['verified', 'likely', 'unverified'] }, quote: { type: 'string' }, location: { type: 'string' } } } } } }

phase('Ingest')
const sources = (await pipeline(urls, url =>
  agent(`Ingest ONE source for the research question "${question}": ${url}
Follow your source-note procedure: dedupe against vault/sources, fetch, write sources/src-<domain>-<topic>.md via mcp__obsidian__write_note with full provenance frontmatter, verbatim excerpts with locations, 3–8 project-relevant claims with confidence, and add the INDEX "Sources" line.
Return {path (native form vault/sources/...), title, reliability, claims}.`,
    { label: url, phase: 'Ingest', agentType: 'vault-researcher', schema: SOURCE_SCHEMA }))).filter(Boolean)

let merged = 'skipped (writeKb=false)'
if (writeKb && sources.length) {
  phase('Synthesize')
  merged = await agent(`Research question: "${question}". Ingested sources (JSON): ${JSON.stringify(sources, null, 1)}
Apply the "Applying research claims" procedure from your instructions and the vault-save rules: group claims by topic; drop project-irrelevant, ephemeral or single-source-unverified claims; search-before-create (pathPrefix "kb", default excludePaths); ADD/UPDATE/SUPERSEDE kb notes with sources:["[[src-…]]"] links and evidence; set used_by on the source notes; update MOC/INDEX lines.
Return markdown: "## KB notes" (path — ADD|UPDATE|SUPERSEDE — description) and "## Not promoted" (claim — why).`,
    { label: 'merge into kb', phase: 'Synthesize', agentType: 'vault-curator' })
}

return [
  `# vault-research · ${question || urls.join(', ')}`,
  `## Sources (${sources.length})`,
  ...sources.map(s => `- ${s.path} — ${s.title || ''} (${s.reliability || '?'}) · ${s.claims.length} claim(s)`),
  '', String(merged), '', 'Next: /vault-find <topic> to check the result; /vault-session to record.',
].join('\n')
