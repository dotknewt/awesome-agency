---
name: wayfinder
description: Charts a huge, foggy chunk of work — bigger than one agent session can hold — as a shared map of investigation tickets on the repo's issue tracker, then resolves them one at a time until the way to the goal is clear. Use when the user has a project, epic, redesign, or migration too large to plan or finish in one sitting and wants it tracked as issues, even if they don't say "wayfinder" or "map" explicitly — e.g. "we need to redo onboarding but I don't know where to start," "this is a huge overhaul, help me break it into trackable pieces over time," or "let's keep working through that redesign issue." Also use when the user names an existing map (by issue number, URL, or title) to resume charting or resolve its next ticket. Do not use for scoping or filing a single already-understood issue, or a generic "open a GitHub issue for X" request with no larger multi-session effort behind it.
---

A loose idea has arrived — too big for one agent session, and wrapped in fog: the route from here to a plan isn't visible yet. This skill charts it as a **shared map** on the repo's issue tracker, then works its tickets one at a time. The map is domain-agnostic — engineering work, course content, whatever fits the shape.

## Refer by name

Every map and ticket is an issue, so it has a **name** — its title. In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The id and URL don't vanish — a name wraps its link — but they ride *inside* the name, never stand in for it.

## The Map

The map is a single issue on this repo's issue tracker, labelled `wayfinder:map` — the canonical artifact. Its tickets are child issues of the map.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place — its ticket — so the map never restates it, only gists it and links.

**Where the map, its child tickets, blocking, and frontier queries physically live is tracker-specific.** Consult `docs/agents/issue-tracker.md` (the "Wayfinding operations" section) for how _this_ repo expresses them. If that doc is absent, default to the local-markdown tracker.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed — they are open child issues, found by query.

```markdown
## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Decisions so far

<!-- the index — one line per closed ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [<closed ticket title>](link) — <one-line gist of the answer>

## Fog

<!-- see "Fog of war" for what belongs here -->
```

### Tickets

Each ticket is a **child issue** of the map; the tracker's issue id is its identity. Its body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Two label families:

- `wayfinder:<type>` — one of `research`, `prototype`, `grilling`, `task` (see [Ticket Types](#ticket-types)).
- `wayfinder:claimed` — a session sets this **first**, before any work, so concurrent sessions skip it.

Blocking uses the tracker's **native** dependency relationship — essential because it renders the frontier _visually_ in the tracker's own UI, so the human sees what's takeable without opening the map. Only a tracker that lacks native blocking falls back to a body convention. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed children — the edge of the known.

The answer isn't part of the body — it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a ticket are linked from the issue, not pasted in.

## Ticket Types

- **Research**: Reading documentation, third-party APIs, or local resources like knowledge bases. Creates a markdown summary as a linked asset. Use when knowledge outside the current working directory is required.
- **Prototype**: Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to — an outline, a rough take, a stub, or UI/logic code via the /prototype skill. Links the prototype as an asset. Use when "how should it look" or "how should it behave" is the key question.
- **Grilling**: Conversation with the agent. Uses the /grilling and /domain-modeling skills. Asks one question at a time. The default case.
- **Task**: Literal manual work that must be done before the discussion can move forward — nothing to decide, prototype, or research. Moving data, signing up for a service, provisioning access. The agent automates it where it can; otherwise it hands the human a precise checklist. Resolved when the work is done; the answer records what was done and any resulting facts (credentials location, new URLs, row counts) later tickets depend on.

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the tickets lies fog — the dim view of decisions and investigations you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets — one at a time, until the way to the goal is clear and no tickets remain.

The map's **Fog** section is where that dim view is written down: the suspected question, the area to revisit later, the risk you're deferring. Write as loosely or as fully as the view allows; it doubles as a signpost for collaborators reading where the effort is headed.

**Fog or ticket?** The test is whether you can state the question precisely now — _not_ whether you can answer it now.

- **Ticket when** the question is already sharp — even if it's blocked and you can't act on it yet.
- **Fog when** you can't yet phrase it that sharply. Don't pre-slice fog into ticket-sized pieces: it's coarser than a ticket, and one patch may graduate into several tickets, or none, once the frontier reaches it.

Fog excludes only what's already decided (that's Decisions so far) and what's already a ticket.

## Available scripts

- **`scripts/claim_ticket.py claim`** — Claims a ticket for this session without losing the race against a concurrent session doing the same thing. Prefer this over manually setting `wayfinder:claimed` (see "Work through the map", step 2).
- **`scripts/claim_ticket.py verify-refs`** — Confirms a list of issue numbers actually exist (and are open) before you wire blocking edges between them in a second pass (see "Chart the map", step 3).

Both subcommands talk to the real tracker via the GitHub REST API (`GITHUB_TOKEN` env var, or `--token`) or run fully offline against a local JSON file (`--offline-store PATH`) for testing. Run `python3 scripts/claim_ticket.py --help` or `python3 scripts/claim_ticket.py <subcommand> --help` for full usage.

## Invocation

Two modes. Either way, **never resolve more than one ticket per session.**

### Chart the map

User invokes with a loose idea.

1. Run a `/grilling` and `/domain-modeling` session to surface the open decisions.
2. **Create the map** (label `wayfinder:map`): Notes filled in, Decisions-so-far empty, Fog sketched.
3. **Create the tickets you can specify now** as child issues of the map — then wire blocking edges in a **second pass** (issues need ids before they can reference each other). Before wiring, run `scripts/claim_ticket.py verify-refs` on the ids you're about to connect so a stale or mistyped id doesn't produce a blocking edge to nothing. Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the Fog.
4. Stop — charting the map is one session's work; do not also resolve tickets.

### Work through the map

User invokes with a map (URL or number). A ticket is **optional** — without one, you pick the next decision, not the user.

1. Load the **map** — the low-res view, not every ticket body.
2. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order. **Claim it** before any work: run `scripts/claim_ticket.py claim` to set `wayfinder:claimed`. It closes the race window against a concurrent session claiming the same ticket (see "The user may run unblocked tickets in parallel" below) — if it reports the ticket is already claimed, drop it and pick the next frontier ticket instead.
3. Resolve it — **zoom as needed**: fetch the full body of any related or closed ticket on demand; invoke the skills the `## Notes` block names. If in doubt, use `/grilling` and `/domain-modeling`.
4. Record the resolution: post the answer as a **resolution comment**, **close** the issue, and **append a context pointer** to the map's Decisions-so-far.
5. Add newly-surfaced tickets (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from the Fog so it lives only as its new ticket. If the decision invalidates other parts of the map, update or delete those tickets.

The user may run unblocked tickets in parallel, so expect other sessions to be editing the tracker concurrently.
