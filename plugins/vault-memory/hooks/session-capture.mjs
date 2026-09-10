#!/usr/bin/env node
/**
 * session-capture.mjs — upserts vault/sessions/<YYYY-MM-DD>--<slug>.md from the Claude Code transcript.
 * Modes (argv[2]): stop | postcompact | sessionend       (wired in .claude/settings.json → hooks)
 * Robust: never throws, always exits 0, works when transcript_path is missing (writes what the hook input knows).
 * Only the block between the generated markers and the hook-owned frontmatter keys are rewritten; curated text is preserved.
 * Redacts common secret patterns and drops <private>…</private> spans. Skips subagents (agent_id) and empty sessions.
 * Dates are LOCAL calendar dates (same basis as session-start.sh and vault-lint.mjs). Opt out per shell: VAULT_SESSION_CAPTURE=0
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join, basename, resolve, relative } from 'node:path';
import { homedir } from 'node:os';

const MODE = process.argv[2] || 'stop';
const ROOT = resolve(process.env.CLAUDE_PROJECT_DIR || process.cwd());
const VAULT = join(ROOT, 'vault');
const DIR = join(VAULT, 'sessions');
const LIM = { prompts: 12, promptChars: 240, files: 40, lastMsg: 800, compact: 4000 };
const GEN_START = '<!-- generated:start -->', GEN_END = '<!-- generated:end -->';
const GEN_KEYS = new Set(['type', 'session_id', 'title', 'slug', 'date', 'started', 'updated', 'ended', 'status', 'model', 'cwd', 'git_branch', 'prompts', 'tools_used', 'files_touched', 'plans', 'tokens_in', 'tokens_out', 'tokens_cache_read']);
const CURATED = ['## Summary', '## Decisions', '## Knowledge written', '## Open questions', '## Next step', '## Checkpoints'];
const WRITE_TOOLS = new Set(['Write', 'Edit', 'write', 'edit', 'apply_patch', 'MultiEdit', 'NotebookEdit', 'mcp__obsidian__write_note', 'mcp__obsidian__update_frontmatter', 'mcp__obsidian__patch_note', 'mcp__obsidian__move_note', 'mcp__obsidian__move_file']);
const SKIP = ['<local-command', '<command-name>', '<system-reminder>', '<task-notification>', '<bash-input>', '<bash-stdout>', '<bash-stderr>'];
const normalizeTool = name => {
  if (name === 'write') return 'Write';
  if (name === 'edit') return 'Edit';
  const m = /^(?:mcp[_-])?([^_]+)_(write_note|update_frontmatter|patch_note|move_note|move_file|delete_note|manage_tags)$/.exec(String(name || ''));
  return m ? `mcp__${m[1]}__${m[2]}` : name;
};
const projectAbs = p => (typeof p === 'string' && p ? resolve(ROOT, p) : null);

// ---------- dates (local) ----------
const pad = n => String(n).padStart(2, '0');
const toDate = s => (s ? new Date(s) : new Date());
const day = s => { const d = toDate(s); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
const hm = s => { const d = toDate(s); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const stampLocal = s => { const d = toDate(s); const off = -d.getTimezoneOffset(); const sign = off >= 0 ? '+' : '-'; return `${day(s)}T${hm(s)}:${pad(d.getSeconds())}${sign}${pad(Math.floor(Math.abs(off) / 60))}:${pad(Math.abs(off) % 60)}`; };

// ---------- redaction ----------
const REDACT = [
  /<private>[\s\S]*?<\/private>/gi,
  /<private>[\s\S]*$/gi,                                   // unterminated span → drop to end
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
];
const KV = /(password|passwd|secret|token|api[_-]?key|apikey|access[_-]?key)(\s*[:=]\s*)['"]?[^\s'"]{6,}['"]?/gi;
function redact(s) {
  if (!s) return '';
  let out = String(s);
  for (const re of REDACT) out = out.replace(re, m => (m.toLowerCase().startsWith('<private>') ? '' : m.startsWith('://') ? '://[REDACTED]@' : '[REDACTED]'));
  out = out.replace(KV, (_m, k, sep) => `${k}${sep}[REDACTED]`);
  return out.replace(/<!--\s*generated:(start|end)\s*-->/gi, '<!- - generated:$1 - ->');   // never let captured text forge our markers
}

// ---------- helpers ----------
const j = v => JSON.stringify(v ?? '');
const slugify = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, '');
const ylist = a => '[' + [...a].map(j).join(', ') + ']';
const relToRoot = fp => (fp && fp.startsWith(ROOT + '/') ? fp.slice(ROOT.length + 1) : 'external:' + fp);
// Mirror mcpvault 0.16.0 normalizePath: '~' → $HOME; in-vault absolute kept; else vault-relative (leading '/' stripped)
function mcpToAbs(p) {
  if (!p || typeof p !== 'string') return null;
  let s = p.trim().replace(/\\/g, '/');
  if (s === '~' || s.startsWith('~/')) s = homedir() + s.slice(1);
  if (s.startsWith(VAULT + '/')) return resolve(s);
  const abs = resolve(VAULT, s.replace(/^\/+/, ''));
  return relative(VAULT, abs).startsWith('..') ? null : abs;
}

function parseTranscript(path) {
  const t = { slug: null, title: null, branch: null, model: null, first: null, last: null, prompts: [], tools: {}, files: new Set(),
    plans: new Set(), plansWritten: new Set(), usage: new Map(), turnIds: new Set(), lastAssistant: null, compactSummaries: [] };
  if (!path || !existsSync(path)) return t;
  let text; try { text = readFileSync(path, 'utf8'); } catch { return t; }
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    let o; try { o = JSON.parse(line); } catch { continue; }
    if (o.slug && !t.slug) t.slug = o.slug;
    if (o.gitBranch && !t.branch) t.branch = o.gitBranch;
    if (o.timestamp) { t.first ??= o.timestamp; t.last = o.timestamp; }
    if (o.type === 'ai-title' && o.aiTitle) t.title = o.aiTitle;
    if (o.isSidechain) continue;
    if (o.type === 'user' && !o.isMeta) {
      const c = o.message?.content;
      let s = typeof c === 'string' ? c : Array.isArray(c) ? c.filter(b => b?.type === 'text').map(b => b.text).join('\n') : '';
      s = (s || '').trim();
      if (!s || SKIP.some(p => s.startsWith(p))) continue;
      if (o.isCompactSummary || /^This session is being continued from a previous conversation/.test(s)) { t.compactSummaries.push(s.slice(0, LIM.compact)); continue; }
      t.prompts.push({ ts: o.timestamp || '', text: redact(s).replace(/\s+/g, ' ').slice(0, LIM.promptChars) });
    } else if (o.type === 'assistant') {
      const m = o.message || {}; t.model ??= m.model || null;
      if (m.usage && m.id) t.usage.set(m.id, m.usage);          // one record per content block shares message-level usage → dedupe by id
      for (const b of m.content || []) {
        if (b.type === 'text' && b.text?.trim()) { t.lastAssistant = b.text.trim(); if (m.id) t.turnIds.add(m.id); }
        if (b.type === 'tool_use') {
          t.tools[b.name] = (t.tools[b.name] || 0) + 1;
          const name = normalizeTool(b.name);
          if (!WRITE_TOOLS.has(name)) continue;
          const i = b.input || {};
          const paths = name.startsWith('mcp__obsidian__')
            ? [i.path, i.oldPath, i.newPath].map(mcpToAbs).filter(Boolean)
            : [i.file_path || i.notebook_path].map(projectAbs).filter(Boolean);
          for (const fp of paths) {
            const rel = relToRoot(fp);
            t.files.add(rel);
            if (rel.startsWith('vault/plans/') && rel.endsWith('.md')) {
              t.plans.add(rel);
              if (['Write', 'Edit', 'MultiEdit', 'mcp__obsidian__write_note', 'mcp__obsidian__update_frontmatter', 'mcp__obsidian__patch_note'].includes(name)) t.plansWritten.add(rel);
            }
          }
        }
      }
    }
  }
  return t;
}

// OpenCode exposes persisted messages through its SDK rather than a Claude transcript.
// Keep the downstream note serializer unchanged by adapting the SDK shape here.
function parseMessages(messages) {
  const t = { slug: null, title: null, branch: null, model: null, first: null, last: null, prompts: [], tools: {}, files: new Set(),
    plans: new Set(), plansWritten: new Set(), usage: new Map(), turnIds: new Set(), lastAssistant: null, compactSummaries: [] };
  const stamp = value => value ? new Date(value).toISOString() : '';
  for (const item of messages || []) {
    const info = item?.info || {};
    const parts = Array.isArray(item?.parts) ? item.parts : [];
    const timestamp = stamp(info.time?.created);
    if (timestamp) { t.first ??= timestamp; t.last = timestamp; }
    if (info.role === 'user') {
      const text = parts.filter(p => p?.type === 'text' && !p.ignored).map(p => p.text).filter(Boolean).join('\n').trim();
      if (parts.some(p => p?.type === 'compaction') && text) t.compactSummaries.push(redact(text).slice(0, LIM.compact));
      if (text && !parts.some(p => p?.type === 'compaction')) t.prompts.push({ ts: timestamp, text: redact(text).replace(/\s+/g, ' ').slice(0, LIM.promptChars) });
      continue;
    }
    if (info.role !== 'assistant') continue;
    t.model ??= info.providerID && info.modelID ? `${info.providerID}/${info.modelID}` : null;
    if (info.tokens && info.id) t.usage.set(info.id, {
      input_tokens: info.tokens.input || 0,
      output_tokens: info.tokens.output || 0,
      cache_read_input_tokens: info.tokens.cache?.read || 0,
      cache_creation_input_tokens: info.tokens.cache?.write || 0,
    });
    if (info.summary) {
      const summary = parts.filter(p => p?.type === 'text').map(p => p.text).filter(Boolean).join('\n').trim();
      if (summary) t.compactSummaries.push(redact(summary).slice(0, LIM.compact));
    }
    for (const part of parts) {
      if (part?.type === 'text' && part.text?.trim()) { t.lastAssistant = part.text.trim(); t.turnIds.add(info.id); }
      if (part?.type !== 'tool') continue;
       const name = normalizeTool(part.tool || 'unknown');
      t.tools[name] = (t.tools[name] || 0) + 1;
      if (!WRITE_TOOLS.has(name)) continue;
      const input = part.state?.input || {};
       let filePath = input.filePath || input.file_path || input.notebook_path || null;
       const paths = name.startsWith('mcp__obsidian__')
         ? [input.path, input.oldPath, input.newPath].map(mcpToAbs).filter(Boolean)
         : [filePath].map(projectAbs).filter(Boolean);
        for (const fp of paths) t.files.add(relToRoot(fp));
        if (name === 'apply_patch' && typeof input.patchText === 'string') {
          let operation = null;
          for (const line of input.patchText.split(/\r?\n/)) {
            const file = /^\*\*\* (Add|Update|Delete) File: (.+)$/.exec(line);
            if (file) {
              operation = file[1];
              const rel = relToRoot(projectAbs(file[2]));
              t.files.add(rel);
              if (rel.startsWith('vault/plans/') && rel.endsWith('.md')) {
                t.plans.add(rel);
                if (operation !== 'Delete') t.plansWritten.add(rel);
              }
              continue;
            }
            const move = /^\*\*\* Move to: (.+)$/.exec(line);
            if (!move) continue;
            const rel = relToRoot(projectAbs(move[1]));
            t.files.add(rel);
            if (rel.startsWith('vault/plans/') && rel.endsWith('.md')) {
              t.plans.add(rel);
              if (operation !== 'Delete') t.plansWritten.add(rel);
            }
          }
        }
       for (const candidate of (name.startsWith('mcp__obsidian__') ? [input.path, input.oldPath, input.newPath] : [filePath, input.movePath])) {
         const absolute = name.startsWith('mcp__obsidian__') ? mcpToAbs(candidate) : projectAbs(candidate);
         if (!absolute) continue;
         const rel = relToRoot(absolute);
         if (rel.startsWith('vault/plans/') && rel.endsWith('.md')) {
           t.plans.add(rel);
           if (['Write', 'Edit', 'write', 'edit', 'mcp__obsidian__write_note', 'mcp__obsidian__update_frontmatter', 'mcp__obsidian__patch_note'].includes(name)) t.plansWritten.add(rel);
         }
       }
    }
  }
  return t;
}

function splitNote(text) {
  const m = /^---\n([\s\S]*?)\n---\n?([\s\S]*)$/.exec(text || '');
  if (!m) return { entries: [], body: text || '' };
  const entries = []; let cur = null;
  for (const line of m[1].split('\n')) {
    const k = /^([A-Za-z0-9_-]+):/.exec(line);
    if (k) { cur = { key: k[1], raw: line }; entries.push(cur); } else if (cur) cur.raw += '\n' + line;
  }
  return { entries, body: m[2] };
}
function fmGet(entries, key) { const e = entries.find(x => x.key === key); if (!e) return null; const v = e.raw.slice(key.length + 1).trim(); try { return JSON.parse(v); } catch { return v; } }
const escRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function findNote(sid) {
  if (!existsSync(DIR)) return null;
  const re = new RegExp(`^session_id: *["']?${escRe(sid)}["']?\\s*$`, 'm');
  for (const f of readdirSync(DIR)) {
    if (!f.endsWith('.md')) continue;
    try { if (re.test(readFileSync(join(DIR, f), 'utf8').slice(0, 1200))) return join(DIR, f); } catch {}
  }
  return null;
}
function appendUnder(body, heading, line) {                 // append a line at the end of a `## Heading` section (created if missing)
  const idx = body.indexOf('\n' + heading);
  if (idx < 0) return body.trimEnd() + `\n\n${heading}\n${line}\n`;
  const start = idx + 1 + heading.length;
  const rest = body.slice(start);
  const next = rest.search(/\n## /);
  const endOfSection = next < 0 ? body.length : start + next;
  return body.slice(0, endOfSection).trimEnd() + '\n' + line + '\n' + body.slice(endOfSection).replace(/^\n?/, '\n');
}

function stampPlans(t, input, sid) {
  // Stamp `type: plan` frontmatter onto plan files this session wrote — never while plan mode is active
  // (the YAML would show up in the plan-approval dialog).
  if (input.permission_mode === 'plan') return;
  const TODAY = day();
  for (const rel of t.plansWritten) {
    const abs = join(ROOT, rel);
    try {
      if (!existsSync(abs)) continue;
      const text = readFileSync(abs, 'utf8');
      if (/^---\r?\n/.test(text)) continue;
      const h1 = /^#\s+(.+)$/m.exec(text);
      const title = (h1 ? h1[1] : basename(abs, '.md')).replace(/"/g, "'").slice(0, 120);
      const fm = ['---', 'type: plan', `title: ${j(title)}`, 'description: ""', 'status: draft', `created: ${TODAY}`, `updated: ${TODAY}`,
        'tags: [plan]', `session_id: ${j(sid)}`, `slug: ${j(t.slug || '')}`, 'outcome: ""', 'produced: []', '---', ''].join('\n');
      writeFileSync(abs, fm + text);
    } catch {}
  }
}

function main() {
  let input = {}; try { input = JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch {}
  if (process.env.VAULT_SESSION_CAPTURE === '0' || input.agent_id) return;
  const sid = input.session_id; if (!sid) return;
  const t = Array.isArray(input.messages) ? parseMessages(input.messages) : parseTranscript(input.transcript_path);
  if (MODE === 'stop' && typeof input.last_assistant_message === 'string' && input.last_assistant_message.trim()) t.lastAssistant = input.last_assistant_message.trim(); // stdin is authoritative (transcript may lag)
  t.lastAssistant = redact(t.lastAssistant);

  if (MODE === 'stop' || MODE === 'sessionend') stampPlans(t, input, sid);

  let notePath = findNote(sid);
  if (!notePath) {
     if (t.prompts.length === 0 && !t.lastAssistant && Object.keys(t.tools).length === 0) return;      // no note for empty sessions
    mkdirSync(DIR, { recursive: true });
    const base = `${day(t.first)}--${t.slug || slugify(t.title) || 'session-' + sid.slice(0, 8)}`;
    notePath = join(DIR, base + '.md');
    if (existsSync(notePath)) notePath = join(DIR, `${base}-${sid.slice(0, 8)}.md`);
  }
  const existing = existsSync(notePath) ? readFileSync(notePath, 'utf8') : '';
  const { entries, body } = splitNote(existing);
  const kept = entries.filter(e => !GEN_KEYS.has(e.key));
  const title = t.title || fmGet(entries, 'title') || `Session ${sid.slice(0, 8)}`;
  const toolsSorted = Object.entries(t.tools).sort((a, b) => b[1] - a[1]);
  const plans = [...t.plans].map(p => `[[${basename(p, '.md')}]]`);
  let tokIn = 0, tokOut = 0, tokCache = 0;
  for (const u of t.usage.values()) { tokIn += (u.input_tokens || 0) + (u.cache_creation_input_tokens || 0); tokOut += u.output_tokens || 0; tokCache += u.cache_read_input_tokens || 0; }
  const closed = MODE === 'sessionend';
  const gen = [
    'type: session', `session_id: ${j(sid)}`, `title: ${j(title)}`, `slug: ${j(t.slug || '')}`,
    `date: ${day(t.first)}`, `started: ${j(stampLocal(t.first))}`, `updated: ${day()}`,
    ...(closed ? [`ended: ${j(stampLocal())}`] : (fmGet(entries, 'ended') ? [`ended: ${j(fmGet(entries, 'ended'))}`] : [])),
    `status: ${closed ? 'closed' : 'open'}`, `model: ${j(t.model || input.model || '')}`,
    `cwd: ${j(input.cwd || ROOT)}`, `git_branch: ${j(t.branch || '')}`, `prompts: ${t.prompts.length}`,
    `tools_used: ${ylist(toolsSorted.map(([k, v]) => `${k}×${v}`))}`,
    `files_touched: ${ylist([...t.files].slice(0, LIM.files))}`, `plans: ${ylist(plans)}`,
    `tokens_in: ${tokIn}`, `tokens_out: ${tokOut}`, `tokens_cache_read: ${tokCache}`,
  ];
  const keptRaw = kept.map(e => e.raw);
  if (!kept.some(e => e.key === 'tags')) keptRaw.push('tags: [session]');
  if (!kept.some(e => e.key === 'description')) keptRaw.push('description: ""');
  if (!kept.some(e => e.key === 'promoted')) keptRaw.push('promoted: false');

  const generated = [GEN_START,
    '## Activity',
    `- Prompts: ${t.prompts.length} · Assistant turns: ${t.turnIds.size} · Tools: ${toolsSorted.slice(0, 8).map(([k, v]) => `${k}×${v}`).join(', ') || 'none'}`,
    `- Files touched: ${[...t.files].slice(0, LIM.files).map(f => '`' + f + '`').join(', ') || 'none'}`,
    `- Plans: ${plans.join(', ') || 'none'}`,
    '### Prompts (trimmed, most recent last)',
    ...t.prompts.slice(-LIM.prompts).map((p, i) => `${i + 1}. [${p.ts ? hm(p.ts) : '--:--'}] ${p.text}`),
    '### Last assistant message',
    ...(t.lastAssistant ? t.lastAssistant.slice(0, LIM.lastMsg).split('\n').map(l => '> ' + l) : ['> (none)']),
    GEN_END].join('\n');

  let newBody;
  const s0 = body.indexOf(GEN_START), e0 = body.lastIndexOf(GEN_END);
  if (s0 >= 0 && e0 > s0) {
    newBody = body.slice(0, s0) + generated + body.slice(e0 + GEN_END.length);
  } else if (body.trim()) {                                    // pre-existing note (e.g. created by /vault-session): insert after H1, add only missing headings
    const h1 = /^# .*$/m.exec(body);
    const at = h1 ? h1.index + h1[0].length : 0;
    newBody = body.slice(0, at) + (h1 ? '\n\n' : '') + generated + body.slice(at).replace(/^\n*/, '\n\n');
    const missing = CURATED.filter(h => !new RegExp('^' + h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*$', 'm').test(newBody));
    if (missing.length) newBody = newBody.trimEnd() + '\n\n' + missing.map(h => h + '\n').join('\n');
  } else {
    newBody = `# ${title}\n\n${generated}\n\n## Summary\n\n## Decisions\n\n## Knowledge written\n\n## Open questions\n\n## Next step\n\n## Checkpoints\n`;
  }
  const stamp = stampLocal();
  if (MODE === 'postcompact') {
    const s = redact(typeof input.compact_summary === 'string' ? input.compact_summary : (t.compactSummaries.at(-1) || ''));
    newBody = appendUnder(newBody, '## Checkpoints', `- ${stamp} post-compact (${input.trigger || '?'})${s ? ' · summary in ## Compaction summaries' : ''}`);
    if (s) newBody = appendUnder(newBody, '## Compaction summaries', `### ${stamp}\n` + s.slice(0, LIM.compact).split('\n').map(l => '> ' + l).join('\n'));
  }
  if (closed) newBody = appendUnder(newBody, '## Checkpoints', `- ${stamp} session ended (${input.reason || 'unknown'})`);

  writeFileSync(notePath, `---\n${[...gen, ...keptRaw].join('\n')}\n---\n${newBody.replace(/^\n+/, '')}`);
}

try { main(); } catch (e) { process.stderr.write(`session-capture(${MODE}): ${e?.message || e}\n`); }
process.exit(0);
