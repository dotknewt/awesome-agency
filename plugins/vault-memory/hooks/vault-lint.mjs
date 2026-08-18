#!/usr/bin/env node
/**
 * vault-lint.mjs — vault note guard + linter (stdlib only; never exits non-zero).
 *   pre    PreToolUse : reads hook JSON on stdin; DENIES only hard violations (location/taxonomy/depth/filename/duplicate or
 *                       reserved basename/full write without frontmatter or invalid type; manage_tags add|remove; delete_note
 *                       without trashMode "local").
 *   post   PostToolUse: re-reads the written note; prints additionalContext for schema/enum/date/link problems.
 *   --all [--json] [--due] [--prefix <vault-rel-dir>]  lint the whole vault; markdown (default) or JSON report.
 * Spec: .claude/skills/vault-conventions/SKILL.md
 */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, resolve, relative, basename, extname } from 'node:path';
import { homedir } from 'node:os';

const ROOT = resolve(process.env.CLAUDE_PROJECT_DIR || process.cwd());
const VAULT = join(ROOT, 'vault');
const localDate = d => { d = d || new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const TODAY = localDate();
const EXEMPT_TOP = new Set(['plans', 'sessions', '_templates', '_bases', '.obsidian', '.trash', 'node_modules', '.git']);
const ROOT_FILES = new Set(['INDEX.md', 'README.md']);
const TAXONOMY = { kb: ['kb', 'decision', 'moc'], docs: ['doc'], sources: ['source'], archive: ['kb', 'decision', 'moc', 'doc', 'source'] };
const ENUM = {
  type: ['kb', 'decision', 'moc', 'doc', 'source', 'plan', 'session', 'index'],
  status: {
    kb: ['draft', 'active', 'needs-review', 'superseded', 'archived'],
    doc: ['draft', 'active', 'needs-review', 'outdated', 'archived'],
    moc: ['active', 'archived'], index: ['active'],
    decision: ['proposed', 'accepted', 'rejected', 'deprecated', 'superseded'],
    source: ['active', 'stale', 'dead-link', 'archived'],
    plan: ['draft', 'approved', 'in-progress', 'done', 'abandoned', 'superseded'],
    session: ['open', 'closed'],
  },
  kind: { kb: ['fact', 'convention', 'gotcha', 'pattern', 'concept'], doc: ['tutorial', 'howto', 'reference', 'explanation'] },
  confidence: ['verified', 'likely', 'unverified'],
  reliability: ['primary', 'official-docs', 'peer-reviewed', 'secondary', 'community', 'unknown'],
  audience: ['agent', 'human', 'both'],
};
const REQ = {
  common: ['type', 'title', 'description', 'status', 'created', 'updated', 'tags'],
  kb: ['kind', 'importance', 'confidence', 'review_after'], decision: ['decided', 'review_after'], doc: ['kind', 'review_after'],
  source: ['url', 'retrieved', 'reliability'], plan: ['session_id'], session: ['session_id'], moc: [], index: [],
};
const LIMITS = { kbLines: 120, bytes: 25 * 1024, index: 150, description: 160 };
const ARCHIVE_OK = new Set(['archived', 'superseded', 'deprecated', 'rejected', 'outdated', 'done', 'abandoned', 'closed', 'dead-link', 'stale']);
const LINK_RE = /\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]/g;

// ---------- fs helpers ----------
const isMd = p => extname(p).toLowerCase() === '.md';
const walk = (dir, out = []) => {
  if (!existsSync(dir)) return out;
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith('.') || EXEMPT_TOP.has(e.name)) continue;
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, out); else if (isMd(e.name)) out.push(p);
  }
  return out;
};
const relOf = abs => relative(VAULT, abs).split('\\').join('/');
function vaultContext(excludeAbs) {
  const all = walk(VAULT).filter(p => p !== excludeAbs);
  const byBase = new Map();
  for (const f of all) { const b = basename(f, extname(f)); byBase.set(b, [...(byBase.get(b) || []), 'vault/' + relOf(f)]); }
  // plans/sessions are outside the taxonomy but share the [[basename]] namespace → reserved names + linkable targets
  const reserved = new Map();
  for (const d of ['plans', 'sessions']) { const dd = join(VAULT, d); if (existsSync(dd)) for (const f of readdirSync(dd)) if (isMd(f)) reserved.set(basename(f, extname(f)), `vault/${d}/${f}`); }
  const linkable = new Set([...byBase.keys(), ...reserved.keys(), 'INDEX', 'README']);
  return { all, byBase, reserved, dupes: new Map([...byBase].filter(([, v]) => v.length > 1)), linkable };
}
// Mirror mcpvault 0.16.0 normalizePath: '~' → $HOME; in-vault absolute path kept; anything else is vault-relative (leading '/' stripped).
function mcpToAbs(p) {
  if (!p || typeof p !== 'string') return null;
  let s = p.trim().replace(/\\/g, '/');
  if (s === '~' || s.startsWith('~/')) s = homedir() + s.slice(1);
  if (s === VAULT) return VAULT;
  if (s.startsWith(VAULT + '/')) return resolve(s);
  s = s.replace(/^\/+/, '');
  const abs = resolve(VAULT, s);
  return relative(VAULT, abs).startsWith('..') ? null : abs;   // traversal → mcpvault throws; nothing to guard
}
function target(input) {
  const name = input.tool_name || ''; const ti = input.tool_input || {};
  let abs = null, oldAbs = null;
  if (name.startsWith('mcp__obsidian__')) { abs = mcpToAbs(ti.newPath || ti.path); oldAbs = mcpToAbs(ti.oldPath); }
  else { const p = ti.file_path || ti.notebook_path || null; abs = p ? resolve(p) : null; }
  return { name, ti, abs, oldAbs };
}
const inVault = abs => !!abs && abs.startsWith(VAULT + '/');

// ---------- frontmatter ----------
function parseFM(text) {
  const m = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)([\s\S]*)$/.exec(text);
  if (!m) return { has: false, fm: {}, raw: '', body: text };
  const fm = {}; let key = null;
  const unq = s => s.replace(/^["']|["']$/g, '');
  for (const line0 of m[1].split('\n')) {
    const line = line0.replace(/\r$/, '');
    const kv = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(line);
    if (kv) {
      key = kv[1]; const v = kv[2].trim();
      if (v.startsWith('[') && v.endsWith(']')) fm[key] = v.slice(1, -1).split(',').map(s => unq(s.trim())).filter(Boolean);
      else if (v === '') fm[key] = [];               // block list follows, or empty value
      else fm[key] = unq(v);
    } else if (key && /^\s*-\s*/.test(line) && (Array.isArray(fm[key]) || fm[key] === '')) {
      if (!Array.isArray(fm[key])) fm[key] = [];
      fm[key].push(unq(line.replace(/^\s*-\s*/, '').trim()));
    }
  }
  return { has: true, fm, raw: m[1], body: m[2] };
}
const isDate = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v);
const inList = (v, list) => list.includes(String(v));
const empty = v => v === undefined || v === '' || (Array.isArray(v) && v.length === 0);
const looksLikeRepoPath = e => typeof e === 'string' && !/^(https?:|cmd:|\[\[|"?\[\[|~)/.test(e) && /^[A-Za-z0-9_./-]+(#.*)?$/.test(e) && e.includes('/') === true;

// ---------- per-note lint ----------
function lintOne(abs, ctx) {
  const rel = relOf(abs); const top = rel.split('/')[0];
  const issues = []; const warn = m => issues.push('WARN ' + m); const err = m => issues.push('ERR ' + m);
  const rec = { path: 'vault/' + rel, top, base: basename(rel, extname(rel)), fm: {}, issues, lines: 0, bytes: 0, due: false };
  let text; try { text = readFileSync(abs, 'utf8'); } catch { err('unreadable'); return rec; }
  rec.lines = text.split('\n').length; rec.bytes = Buffer.byteLength(text);
  const { has, fm, raw, body } = parseFM(text);
  rec.fm = fm;
  if (!has) { err('no frontmatter block (--- on line 1)'); return rec; }
  if (text.includes('\r\n')) warn('CRLF line endings (mcpvault search/info cannot see this frontmatter) — convert to LF');
  const type = fm.type;
  if (!rel.includes('/')) {                              // INDEX.md (README is exempt upstream)
    if (type !== 'index') err(`type '${type}' must be 'index'`);
    if (rec.lines > LIMITS.index) warn(`INDEX has ${rec.lines} lines (>${LIMITS.index}); move detail into kb/moc-* notes`);
    return rec;
  }
  for (const k of REQ.common) if (empty(fm[k])) err(`missing ${k}`);
  if (type && !inList(type, ENUM.type)) err(`type '${type}' not in ${ENUM.type.join('|')}`);
  if (TAXONOMY[top] && type && !TAXONOMY[top].includes(type)) err(`type '${type}' not allowed under ${top}/ (allowed: ${TAXONOMY[top].join('|')})`);
  for (const k of REQ[type] || []) if (empty(fm[k])) err(`missing ${k} (required for type ${type})`);
  if (ENUM.status[type] && fm.status && !inList(fm.status, ENUM.status[type])) err(`status '${fm.status}' not in ${ENUM.status[type].join('|')}`);
  if (ENUM.kind[type] && fm.kind && !inList(fm.kind, ENUM.kind[type])) err(`kind '${fm.kind}' not in ${ENUM.kind[type].join('|')}`);
  if (fm.confidence && !inList(fm.confidence, ENUM.confidence)) err(`confidence '${fm.confidence}' not in ${ENUM.confidence.join('|')}`);
  if (fm.reliability && !inList(fm.reliability, ENUM.reliability)) err(`reliability '${fm.reliability}' not in ${ENUM.reliability.join('|')}`);
  if (fm.audience && !inList(fm.audience, ENUM.audience)) err(`audience '${fm.audience}' not in ${ENUM.audience.join('|')}`);
  if (fm.importance !== undefined && !empty(fm.importance) && !/^[1-5]$/.test(String(fm.importance))) err('importance must be 1-5');
  for (const k of ['created', 'updated', 'reviewed', 'review_after', 'decided', 'retrieved', 'date']) if (!empty(fm[k]) && !isDate(fm[k])) err(`${k} must be YYYY-MM-DD`);
  if (fm.tags !== undefined && !Array.isArray(fm.tags)) err('tags must be a YAML list');
  if (Array.isArray(fm.tags)) for (const t of fm.tags) if (!/^[a-z0-9][a-z0-9/-]*$/.test(t)) warn(`tag '${t}' is not lowercase kebab-case`);
  if (typeof fm.description === 'string' && fm.description.length > LIMITS.description) warn(`description ${fm.description.length} chars (>${LIMITS.description})`);
  if (fm.status === 'superseded' && empty(fm.superseded_by)) err('status superseded requires superseded_by');
  if (fm.confidence === 'verified' && empty(fm.evidence)) warn('confidence verified but no evidence entries');
  if (/\{\{[^}]*\}\}|^[A-Za-z0-9_-]+:\s*"?<[^>]+>"?\s*$/m.test(raw)) warn('template placeholder left in frontmatter ({{…}} or <…>) — replace with real values');
  // unquoted wikilinks in YAML: value or list item starting with [[ without a quote
  if (/^[A-Za-z0-9_-]+:\s*\[\[|^\s*-\s*\[\[|^[A-Za-z0-9_-]+:\s*\[\s*\[\[/m.test(raw)) warn('unquoted [[link]] inside frontmatter — quote it ("[[x]]")');
  const bodyNoCode = body.replace(/```[\s\S]*?```/g, '').replace(/`[^`\n]*`/g, '');
  if (/(^|\s)#[a-zA-Z][\w/-]*/m.test(bodyNoCode)) warn('inline #hashtag in body (mcpvault manage_tags would promote it into YAML tags) — use tags:');
  if (type === 'kb' && rec.lines > LIMITS.kbLines) warn(`kb note has ${rec.lines} lines (>${LIMITS.kbLines}); split it`);
  if (rec.bytes > LIMITS.bytes) warn(`note is ${rec.bytes} bytes (>25 KB); split it`);
  if (top === 'archive' && !ARCHIVE_OK.has(String(fm.status))) warn(`in archive/ but status '${fm.status}'`);
  if (top !== 'archive' && ['archived', 'superseded'].includes(String(fm.status))) issues.push(`NOTE status '${fm.status}' but not moved yet — patch referrers (Grep "\\[\\[${rec.base}" vault/) then move_note to archive/${top}/${rec.base}.md, or leave it for /vault-review`);
  if (Array.isArray(fm.evidence)) for (const e of fm.evidence) { if (looksLikeRepoPath(e)) { const p = e.split('#')[0]; if (!existsSync(resolve(ROOT, p))) warn(`stale evidence path '${p}' (file not found) — re-verify or mark status: needs-review`); } }
  if (!empty(fm.review_after) && isDate(fm.review_after) && fm.review_after <= TODAY && top !== 'archive') rec.due = true;
  if (ctx) {
    const seen = new Set();
    for (const m of bodyNoCode.matchAll(LINK_RE)) { const tgt = m[1].trim(); const b = (tgt.includes('/') ? basename(tgt) : tgt).replace(/\.md$/, ''); if (!ctx.linkable.has(b) && !seen.has(b)) { seen.add(b); warn(`unresolved link [[${tgt}]] — create that note or fix the basename`); } }
    if (ctx.dupes.has(rec.base)) err(`duplicate basename '${rec.base}' (also: ${ctx.dupes.get(rec.base).filter(p => p !== rec.path).join(', ')})`);
  }
  return rec;
}

// ---------- pre (deny) ----------
function pre() {
  let input = {}; try { input = JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch { return; }
  const { name, ti, abs, oldAbs } = target(input);
  const deny = reason => console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: `vault-lint: ${reason}. See skill vault-conventions §1–3.` } }));
  if (name === 'mcp__obsidian__manage_tags' && ['add', 'remove'].includes(ti.operation)) return deny('manage_tags add/remove promotes body #tokens into YAML tags — edit tags with update_frontmatter instead');
  if (name === 'mcp__obsidian__delete_note' && ti.trashMode !== 'local') return deny(`delete_note requires trashMode:"local" (recoverable, hidden from the index) and explicit user confirmation — got trashMode "${ti.trashMode || 'none'}"`);
  if (!inVault(abs) || !isMd(abs)) return;
  const rel = relOf(abs); const segs = rel.split('/'); const top = segs[0]; const file = segs[segs.length - 1];
  if (segs.length === 1) { if (!ROOT_FILES.has(file)) deny(`'${rel}' — only INDEX.md and README.md may live at the vault root; put notes under kb/, docs/, sources/`); return; }
  if (EXEMPT_TOP.has(top)) return;
  if (!TAXONOMY[top]) return deny(`'${rel}' — top-level folder '${top}/' is not part of the vault taxonomy (kb|docs|sources|archive|plans|sessions)`);
  if (segs.length - 1 > 2) return deny(`'${rel}' — more than 2 folder levels (max: kb/decisions/x.md, archive/kb/x.md)`);
  if (top === 'archive' && !(segs.length === 3 && ['kb', 'docs', 'sources'].includes(segs[1]))) return deny(`'${rel}' — archived notes live at archive/<kb|docs|sources>/<same-basename>.md`);
  if (!/^[a-z0-9][a-z0-9-]*\.md$/.test(file)) return deny(`'${file}' — filenames must be lowercase kebab-case [a-z0-9-].md`);
  const isMove = name === 'mcp__obsidian__move_note' || name === 'mcp__obsidian__move_file';
  const isNew = !existsSync(abs);
  if (isNew && !(isMove && oldAbs && basename(oldAbs) === basename(abs))) {
    const ctx = vaultContext(oldAbs);
    const b = basename(abs, extname(abs));
    if (ctx.byBase.has(b)) return deny(`basename '${b}' already exists (${ctx.byBase.get(b).join(', ')}) — basenames must be unique vault-wide`);
    if (ctx.reserved.has(b)) return deny(`basename '${b}' collides with ${ctx.reserved.get(b)} — [[${b}]] would resolve ambiguously; pick another name`);
  }
  const fullWrite = name === 'Write' || (name === 'mcp__obsidian__write_note' && (!ti.mode || ti.mode === 'overwrite' || isNew));
  if (fullWrite && top !== 'archive') {
    let type = null; const content = typeof ti.content === 'string' ? ti.content : '';
    const contentFM = /^---\r?\n/.test(content);
    if (name === 'Write') {
      if (!contentFM) return deny(`'${rel}' — full write without a frontmatter block; start the file with --- and the required keys (LF line endings)`);
      type = parseFM(content).fm.type;
    } else {
      let fmArg = ti.frontmatter; if (typeof fmArg === 'string') { try { fmArg = JSON.parse(fmArg); } catch { fmArg = null; } }
      if (fmArg && contentFM) return deny(`'${rel}' — frontmatter passed both as argument and inside content; pass it once (frontmatter argument)`);
      if (!fmArg && !contentFM) return deny(`'${rel}' — write_note ${ti.mode && ti.mode !== 'overwrite' ? `mode ${ti.mode} on a new file ` : ''}without frontmatter; pass frontmatter:{type,title,description,status,created,updated,tags,…}`);
      type = fmArg ? fmArg.type : parseFM(content).fm.type;
    }
    if (!type || !inList(type, ENUM.type)) return deny(`'${rel}' — frontmatter type '${type}' missing or not in ${ENUM.type.join('|')}`);
    if (!TAXONOMY[top].includes(String(type))) return deny(`'${rel}' — type '${type}' is not allowed under ${top}/ (allowed: ${TAXONOMY[top].join('|')})`);
  }
}

// ---------- post (warn) ----------
function post() {
  let input = {}; try { input = JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch { return; }
  const { name, abs, oldAbs } = target(input);
  if (!inVault(abs) || !isMd(abs) || !existsSync(abs)) return;
  const rel = relOf(abs); const top = rel.split('/')[0];
  if (EXEMPT_TOP.has(top)) return;
  if (!rel.includes('/') && rel !== 'INDEX.md') return;   // README.md exempt
  const ctx = vaultContext(null);
  const rec = lintOne(abs, ctx);
  const problems = rec.issues.filter(i => i.startsWith('ERR') || i.startsWith('WARN'));   // NOTE-level hints stay in --all
  if ((name === 'mcp__obsidian__move_note' || name === 'mcp__obsidian__move_file') && oldAbs && basename(oldAbs) !== basename(abs)) {
    const ob = basename(oldAbs, extname(oldAbs)); const refs = [];
    for (const f of ctx.all) { try { if (readFileSync(f, 'utf8').includes(`[[${ob}`)) refs.push('vault/' + relOf(f)); } catch {} }
    if (refs.length) problems.push(`WARN renamed '${ob}' but ${refs.length} note(s) still link to it: ${refs.slice(0, 5).join(', ')} — patch them with patch_note`);
  }
  if (!problems.length) return;
  const msg = `vault-lint ${rec.path}: ${problems.join('; ')}. (Schema: skill vault-conventions §3; ERR items must be fixed now — update_frontmatter {merge:true} or Edit.)`;
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PostToolUse', additionalContext: msg.slice(0, 1500) } }));
}

// ---------- --all ----------
function all(prefixArg, asJson, dueOnly) {
  const ctx = vaultContext(null);
  let prefix = (prefixArg || '').replace(/\\/g, '/').replace(/^vault\//, '').replace(/^\/+|\/+$/g, '');
  if (prefix && relative(VAULT, resolve(VAULT, prefix)).startsWith('..')) { console.log(`vault-lint: --prefix '${prefixArg}' is outside the vault`); return; }
  let files = prefix ? walk(join(VAULT, prefix)) : [...ctx.all];
  const idx = join(VAULT, 'INDEX.md'); if (!prefix && existsSync(idx) && !files.includes(idx)) files.push(idx);
  files = files.filter(f => basename(f) !== 'README.md');
  let notes = files.map(f => lintOne(f, ctx));
  const inbound = new Map();
  for (const f of ctx.all.concat(existsSync(idx) ? [idx] : [])) { let t = ''; try { t = readFileSync(f, 'utf8'); } catch {} for (const m of t.matchAll(LINK_RE)) { const b = m[1].trim().split('/').pop().replace(/\.md$/, ''); if (b !== basename(f, extname(f))) inbound.set(b, (inbound.get(b) || 0) + 1); } }
  for (const n of notes) if (['kb', 'docs'].includes(n.top) && n.fm.type !== 'moc' && !inbound.get(n.base)) n.issues.push('INFO no inbound [[link]] (orphan) — link it from INDEX, a MOC or a related note');
  const summary = {
    total: notes.length,
    errors: notes.filter(n => n.issues.some(i => i.startsWith('ERR'))).length,
    warnings: notes.filter(n => n.issues.some(i => i.startsWith('WARN'))).length,
    due: notes.filter(n => n.due).map(n => n.path),
    needsReview: notes.filter(n => n.fm.status === 'needs-review').map(n => n.path),
    duplicates: Object.fromEntries(ctx.dupes),
  };
  if (dueOnly) notes = notes.filter(n => n.due || n.fm.status === 'needs-review' || n.issues.some(i => i.startsWith('ERR')));
  if (asJson) {
    console.log(JSON.stringify({ today: TODAY, summary, notes: notes.map(n => ({ path: n.path, type: n.fm.type, kind: n.fm.kind, title: n.fm.title, description: n.fm.description, status: n.fm.status,
      importance: n.fm.importance === undefined || n.fm.importance === '' ? undefined : Number(n.fm.importance), confidence: n.fm.confidence, updated: n.fm.updated, reviewed: n.fm.reviewed, review_after: n.fm.review_after, due: n.due, lines: n.lines, issues: n.issues })) }, null, 1));
    return;
  }
  console.log(`# vault lint ${TODAY} — ${summary.total} notes, ${summary.errors} with errors, ${summary.warnings} with warnings, ${summary.due.length} past review_after, ${summary.needsReview.length} needs-review${dueOnly ? ' (showing due/needs-review/ERR only)' : ''}`);
  for (const [b, ps] of ctx.dupes) console.log(`- ERR duplicate basename '${b}': ${ps.join(', ')}`);
  for (const n of notes) if (n.issues.length || n.due) console.log(`- ${n.path}${n.due ? ' [DUE ' + n.fm.review_after + ']' : ''}${n.issues.length ? '\n' + n.issues.map(i => '  - ' + i).join('\n') : ''}`);
  if (!ctx.dupes.size && !notes.some(n => n.issues.length || n.due)) console.log('- no issues');
}

try {
  const a = process.argv.slice(2);
  if (a[0] === 'pre') pre();
  else if (a[0] === 'post') post();
  else if (a.includes('--all')) all(a.includes('--prefix') ? a[a.indexOf('--prefix') + 1] || '' : '', a.includes('--json'), a.includes('--due'));
  else console.log('usage: vault-lint.mjs pre | post | --all [--json] [--due] [--prefix kb]');
} catch (e) { process.stderr.write(`vault-lint: ${e?.message || e}\n`); }
process.exit(0);
