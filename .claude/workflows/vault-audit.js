export const meta = {
  name: 'vault-audit',
  description: 'Sweep vault/kb and vault/docs for stale, contradicting or duplicate notes; verify each note against code/sources; report (and optionally apply safe) revise/supersede/archive actions',
  whenToUse: 'When the SessionStart briefing reports many notes past review_after, or for a periodic knowledge review. Proposes only unless args.apply is true; never deletes.',
  phases: [
    { title: 'Select', detail: 'vault-librarian runs the linter and picks candidates by scope' },
    { title: 'Verify', detail: 'one read-only verdict per note (pipeline)' },
    { title: 'Apply', detail: 'vault-curator applies safe actions when args.apply is true' },
  ],
}

// args: { scope?: 'due' | 'all' | '<vault-relative prefix such as kb/decisions>', limit?: number, apply?: boolean }
const scope = (args && args.scope) || 'due'
const limit = (args && args.limit) || 40
const apply = !!(args && args.apply)

const SELECT_SCHEMA = { type: 'object', required: ['notes'], properties: { notes: { type: 'array', items: { type: 'object', required: ['path'], properties: {
  path: { type: 'string' }, type: { type: 'string' }, kind: { type: 'string' }, title: { type: 'string' }, description: { type: 'string' },
  status: { type: 'string' }, importance: { type: ['number', 'string'] }, updated: { type: 'string' }, review_after: { type: 'string' },
  lint_issues: { type: 'array', items: { type: 'string' } } } } } } }

const VERDICT_SCHEMA = { type: 'object', required: ['path', 'verdict', 'confidence', 'rationale'], properties: {
  path: { type: 'string' },
  verdict: { type: 'string', enum: ['keep', 'revise', 'supersede', 'merge', 'archive', 'delete', 'needs-human'] },
  confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  rationale: { type: 'string' },
  evidence_checked: { type: 'array', items: { type: 'string' } },
  duplicate_of: { type: 'string' },
  contradicts: { type: 'array', items: { type: 'string' } },
  proposed_change: { type: 'string' } } }

phase('Select')
const sel = await agent(
  `From the project root run: node .claude/hooks/vault-lint.mjs --all --json${scope === 'due' ? ' --due' : ''}${scope !== 'due' && scope !== 'all' ? ' --prefix ' + scope : ''}  (JSON with "summary" and "notes").
Select notes to review for scope="${scope}": "due" = notes with due:true OR status needs-review OR issues starting with ERR;
"all" = every note whose path starts with vault/kb/ or vault/docs/; anything else = notes whose path starts with vault/${scope}/.
Never include vault/archive, vault/sessions, vault/plans, vault/_templates, vault/_bases, INDEX.md or type moc notes.
Cap at ${limit}, prioritising overdue review_after and importance >= 4. Do NOT modify anything.
Return {notes:[{path,type,kind,title,description,status,importance,updated,review_after,lint_issues}]} — nothing else.`,
  { label: 'select candidates', phase: 'Select', agentType: 'vault-librarian', effort: 'low', schema: SELECT_SCHEMA })
const notes = (sel && sel.notes) || []
log(`vault-audit: ${notes.length} candidate note(s) for scope=${scope}`)

phase('Verify')
const verdicts = (await pipeline(notes, n =>
  agent(`Review ONE vault note for continued validity. Note: ${n.path} (type ${n.type || '?'}${n.kind ? '/' + n.kind : ''}, status ${n.status || '?'}, importance ${n.importance || '?'}, updated ${n.updated || '?'}, review_after ${n.review_after || '?'}). Lint issues: ${(n.lint_issues || []).join('; ') || 'none'}.
Steps: (1) read the note (frontmatter + body); (2) verify each evidence / verifies / sources item: Grep cited code paths and symbols, open cited [[src-…]] notes, run cheap read-only commands; (3) search for near-duplicates and contradictions: mcp__obsidian__search_notes with 2–3 variants of the title's key terms, pathPrefix "kb" then "docs", excludePaths ["archive","sessions","plans","_templates","_bases"], limit 10, then get_frontmatter on the top hits; (4) decide with the lifecycle table in the vault-conventions skill §8.
Do NOT modify anything. Return the structured verdict; rationale <= 60 words; list contradicting/duplicate paths in native form (vault/...).`,
    { label: n.path, phase: 'Verify', agentType: 'vault-librarian', schema: VERDICT_SCHEMA }))).filter(Boolean)

const actionable = verdicts.filter(v => v.verdict !== 'keep')
const keep = verdicts.filter(v => v.verdict === 'keep')

let applied = null
if (apply && verdicts.length) {
  phase('Apply')
  applied = await agent(`Apply these vault review verdicts following the vault-conventions skill §6 and §8.
Allowed: keep -> bump reviewed/review_after + Review-log line; revise -> edit in place + bump updated; supersede/merge/archive -> write the replacement or merged note, set superseded_by/status, patch inbound [[links]] first (Grep + patch_note), move the old note to vault/archive/<kb|docs|sources>/<same-basename>.md, update MOC/INDEX lines.
NOT allowed: delete (leave as a proposal with the exact delete_note call), needs-human, anything outside vault/.
Verdicts (JSON): ${JSON.stringify(verdicts, null, 1)}
Return markdown: "## Applied" (path — action) and "## Still proposed" (path — verdict — why).`,
    { label: 'apply safe actions', phase: 'Apply', agentType: 'vault-curator' })
}

return [
  `# vault-audit · scope=${scope} · reviewed=${verdicts.length}/${notes.length} · apply=${apply}`,
  `## Proposed actions (${actionable.length})`,
  ...actionable.map(v => `- **${v.verdict}** ${v.path} (${v.confidence}) — ${v.rationale}` +
    (v.duplicate_of ? ` · duplicate of ${v.duplicate_of}` : '') +
    (v.contradicts && v.contradicts.length ? ` · contradicts ${v.contradicts.join(', ')}` : '') +
    (v.proposed_change ? `\n  - change: ${v.proposed_change}` : '')),
  `## Verified OK (${keep.length})`, ...keep.map(v => `- ${v.path}`),
  applied ? `## Applied\n${applied}` : '## Applied\nnothing — rerun with args {apply:true} to let vault-curator apply the safe actions',
  'Next: confirm deletions / needs-human items explicitly (delete_note only with trashMode "local"); then /vault-session.',
].join('\n')
