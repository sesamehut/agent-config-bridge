# Host facts: entry instructions and rules

Host facts and the fidelity mapping for the entry/rules unit class: the
project entry file (`CLAUDE.md` on the Claude side, root `AGENTS.md` on the
Codex side) and the rule shards under `.claude/rules/`. Facts only — the
bridge's normative conventions for this unit class (marker grammar,
rendering pipeline, applicability-preamble template, frontmatter schemas)
live in
[`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md);
report states, tier-assignment rules, and annotations live in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md).

## Fidelity mapping (entry/rules unit class)

| Source unit | Codex counterpart | Tier | Grounding host fact |
|---|---|---|---|
| Project entry (`CLAUDE.md`) | Managed block in root `AGENTS.md` | `structural` | Codex has no counterpart of the CLAUDE.md organizing mechanism; the block carrier replaces it, with the content itself fully expressible |
| Rule shard without path scoping | Managed block in root `AGENTS.md` | `structural` | Same carrier substitution |
| Rule shard with `paths` scoping | Managed block with a leading applicability preamble | `semantic` | Codex has no mechanical path-scoped rule trigger; mechanical scoping degrades to a natural-language preamble — attention scoping |

The normative tier-column rules and the preamble template are defined in the
two spec files linked above.

## Comment-stripping asymmetry

- collected: 2026-07-07, reconfirmed 2026-07-08
- source: official Claude Code and Codex docs; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled

| Host | Behavior for HTML comments in project docs |
|---|---|
| Claude Code | Strips block-level HTML comments from CLAUDE.md-family files (including `.claude/rules/*.md`) before context injection; comments inside code blocks are preserved |
| Codex | Strips nothing; comments — including bridge marker lines — reach the model verbatim and count against the project-doc byte budget |

Marker byte cost on the Codex side (marker grammar in the source-tree spec):

Per managed block, marker overhead on the Codex budget =
`41 + len(id) + len(source)` bytes for the start line (`+ 6 + len(mode)` when
a mode attribute is present) + `27` bytes for the end line + 2 EOL bytes
(LF). Example: the covenant block (`id=rules/bridge-covenant`, 21 bytes;
`source=.claude/rules/bridge-covenant.md`, 32 bytes) costs 41+21+32+27+2 =
123 bytes of the 32768-byte combined budget. The claude-only pair costs 33 +
31 bytes + 2 EOL where it appears (Claude-side files only — where stripping
makes runtime cost zero). Claude-side cost of all markers is zero (comments
stripped before context injection).

## AGENTS.md budget mechanics

- collected: 2026-07-08
- source: official Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled

- `project_doc_max_bytes` is a COMBINED 32768-byte budget over the whole
  project root→cwd chain of project docs, not a per-file limit.
- The budget is consumed root-first.
- The file that crosses the remaining budget is truncated MID-FILE,
  silently; the TUI shows no truncation indicator.
- Files after the crossing file are skipped entirely.
- The global `~/.codex/AGENTS.md` / `~/.codex/AGENTS.override.md` layer is
  NOT counted against the budget and is prepended to the chain.

## AGENTS.override.md shadowing

- collected: 2026-07-08
- source: official Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: watch

- Per-directory, first-match-wins: an `AGENTS.override.md` completely
  replaces the `AGENTS.md` of the same directory in the discovery chain.
- Consequence: a root `AGENTS.override.md` makes the entire root `AGENTS.md`
  — and with it the whole rules-projection surface — silently inactive.
- Watch item: official docs are silent on how gitignore positioning
  interacts with the override file.

## Discovery chain

- collected: 2026-07-08
- source: official Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled (wording), watch (rebuild timing)

- The project root is located by root markers (default: `.git`).
- One project-doc file per directory.
- Files concatenate root→cwd, joined by `\n\n`.
- No downward scanning below cwd; no sibling scanning.
- Deeper files take soft positional precedence (they appear later in the
  concatenated context).
- The chain is built per environment cwd (multi-environment support on
  current main); it never follows the file being edited. Rebuild timing is
  the open watch item.

## Claude project entry locations

- collected: 2026-07-08
- source: official Claude Code docs; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled

- Both `CLAUDE.md` and `.claude/CLAUDE.md` are official project entry
  locations; they can coexist (a coexistence hazard).
- `@path` imports expand at session launch; at most 4 hops; imports inside
  code spans are skipped; paths outside the project require one-time
  approval.
- Claude reads `CLAUDE.md`, not `AGENTS.md`.

## `claudeMdExcludes`

- collected: 2026-07-08
- source: official Claude Code settings docs; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled

- Accepted in any settings layer.
- Globs match absolute paths; relative patterns need a `**/` prefix.
- Arrays merge across settings layers.
- Covers CLAUDE.md-family memory files AND rules files under excluded globs.
- Documented as memory-only: it does NOT cover nested `.claude/skills/`.
- Project settings load only from the session's starting directory.

## Rules mechanics + `bridge` key tolerance

- collected: 2026-07-08 (in-milestone empirical observation added 2026-07-21)
- source: official Claude Code rules docs; live in-session load observation; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled (frontmatter form tolerated, observed live 2026-07-21); watch (host-version drift only)

- `.claude/rules/**` is discovered recursively; symlinked rule files are
  supported.
- `paths` is the only documented rules frontmatter key: a list of globs,
  brace expansion supported; path-scoped rules trigger on READ of matching
  files.
- Tolerance of unknown keys in rules frontmatter — such as the bridge's
  intent-record key `bridge` — is officially unspecified.
- Empirical result (2026-07-21): a live Claude Code session loaded this
  repo's `.claude/rules/fixtures.md` — which carries both `paths` and the
  extra `bridge` intent-record frontmatter key — as active rule context: the
  post-frontmatter body was injected and applied, the frontmatter block was
  stripped normally, and no parse or load error occurred. Claude tolerates
  the extra `bridge` key in rules frontmatter. The frontmatter form is
  therefore in force (confirmed, not merely defaulted): intent records are
  carried in the `bridge` frontmatter key. The comment fallback form (pinned
  in the source-tree spec) stays reserved for a future host regression only.
- Watch item: this observation is a single host version; re-confirm if the
  Claude Code rules loader changes its frontmatter handling, and update this
  entry with a new date.
