# Host facts: entry instructions and rules

Host facts and the fidelity mapping for the entry/rules unit class: the
project entry file (`CLAUDE.md` on the Claude side, root `AGENTS.md` on the
Codex side) and the rule shards under `.claude/rules/`. Facts only — the
bridge's normative conventions for this unit class (marker grammar,
rendering pipeline, `pv2` applicability preamble, strict control comments,
and `paths` schema) live in
[`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md);
report states, tier-assignment rules, and annotations live in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md).
Write-side ownership and plans are governed by
[`reconciliation/v3`](../skills/bridge-sync/references/reconciliation-spec.md)
and [`sync-plan/v3`](../skills/bridge-sync/references/sync-plan-spec.md).

Evidence labels in this file are deliberate:

- **host contract**: behavior stated in current official host documentation;
- **implementation observation**: behavior verified in a pinned official
  source commit, but not promoted to a public contract;
- **empirical observation**: behavior observed in a dated live host run;
- **Bridge policy**: a project-owned consequence or choice, never a host fact.

## Current Bridge contract boundary

The only current tuple is `covenant/v3`, `source-tree/v5`, `report/v5`,
`reconciliation/v3`, and `sync-plan/v3`. The exact former
`covenant/v1` / `source-tree/v3` and `covenant/v2` / `source-tree/v4`
templates are archived migration evidence only; they form a closed
two-member set, each one hop from the current tuple, and neither is an
alternate runtime interpretation. A legacy v3 managed start containing `mode=`
is a blocking migration/repair input, not a current semantic mode. The
entry/rules facts in this file are unchanged by the current tuple; the tuple
bump adds the hook unit class recorded in [`hooks.md`](hooks.md).

## Fidelity mapping (entry/rules unit class)

| Source unit | Codex counterpart | Tier | Grounding host fact |
|---|---|---|---|
| Project entry (`CLAUDE.md`) with no active shared import | Managed block in root `AGENTS.md` | `structural` | Codex has no counterpart of the CLAUDE.md organizing mechanism; the block carrier replaces that structure |
| Rule shard without frontmatter | Managed block in root `AGENTS.md` | `structural` | Same carrier substitution |
| Rule shard with valid scoped `paths` frontmatter | Managed block with the exact `pv2` applicability preamble | `semantic` | Codex has no mechanical path-scoped rule trigger; mechanical scoping degrades to natural-language attention scoping |

The normative tier-column rules and the preamble template are defined in the
two sentinel specs linked above. A dual project entry, active shared import,
or invalid/no-op/duplicate/over-budget `paths` is blocked before ordinary tier
assignment; it does not select a fallback render.

## Comment-stripping asymmetry

- collected: 2026-07-07; official boundary reconfirmed 2026-07-24; rule-file
  observation last confirmed 2026-07-21
- source: official Claude Code docs; pinned Codex source; dated notes in
  [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled host contract for `CLAUDE.md`; settled pinned implementation
  observation for Codex; empirical watch for Claude rule files

| Host | Behavior for HTML comments in project docs |
|---|---|
| Claude Code | Officially strips block-level HTML comments from `CLAUDE.md` files before context injection; comments inside code blocks are preserved. The official wording does not explicitly cover `.claude/rules/*.md`; stripping there is a 2026-07-21 empirical observation |
| Codex | The pinned implementation performs no comment preprocessing; for valid UTF-8, comments — including bridge marker lines — reach the model verbatim and count against the project-doc byte budget |

Marker byte cost on the Codex side (marker grammar in the source-tree spec):

Per managed block, marker overhead on the Codex budget =
`41 + len(id) + len(source)` bytes for the v4 start line + `27` bytes for the
end line + 2 EOL bytes (LF). The v4 start grammar has exactly `id` and
`source`; it admits no other attribute. Example: the covenant block
(`id=rules/bridge-covenant`, 21 bytes;
`source=.claude/rules/bridge-covenant.md`, 32 bytes) costs 41+21+32+27+2 =
123 bytes of the 32768-byte combined budget. The claude-only pair costs 33 +
31 bytes + 2 EOL where it appears. Its runtime cost is contractually zero in
`CLAUDE.md`; zero cost in a Claude rule file is only the dated empirical
observation above.

## AGENTS.md budget mechanics

- collected: 2026-07-08; reconfirmed 2026-07-24
- source: official
  [AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md);
  openai/codex
  [`agents_md.rs` at `0dfa778`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/core/src/agents_md.rs);
  dated notes in
  [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled host contract for a combined default budget; pinned
  implementation observation for truncation, decoding, and multi-environment
  details

- `project_doc_max_bytes` defaults to a COMBINED 32768-byte budget over one
  project root→cwd chain of project docs, not a per-file limit. The effective
  configured value may differ or be zero.
- The budget is consumed root-first.
- In the pinned implementation, each selected environment gets its own
  root→cwd combined budget. The file that crosses the remaining budget is
  truncated MID-FILE by bytes; files after it are skipped entirely.
- The pinned implementation emits a tracing warning, but the public UI
  contract does not promise a visible truncation indicator.
- The global `~/.codex/AGENTS.md` / `~/.codex/AGENTS.override.md` layer is
  independently loaded, trimmed, prepended, and NOT counted against the
  project budget.
- Project files are byte-budgeted and then decoded with
  `String::from_utf8_lossy`; valid UTF-8 receives no frontmatter, import, or
  HTML-comment preprocessing. A truncation that splits a multi-byte code point
  produces U+FFFD. “Raw bytes reach the prompt unchanged” is therefore not an
  accurate general statement.
- The current Advanced Configuration page still describes this knob as how
  much to read “from each AGENTS.md file.” That wording conflicts with the
  specialized AGENTS.md guide and the pinned implementation; this baseline
  follows the latter two and keeps the documentation conflict on watch.

## AGENTS.override.md shadowing

- collected: 2026-07-08; worktree scope reconfirmed 2026-07-24
- source: official Codex
  [AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
  and
  [worktree guide](https://learn.chatgpt.com/docs/environments/git-worktrees#copy-ignored-local-files-into-managed-worktrees);
  dated notes in
  [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled host contract, with surface-specific worktree scope

- Per-directory, first-match-wins: an `AGENTS.override.md` completely
  replaces the `AGENTS.md` of the same directory in the discovery chain.
- Consequence: a root `AGENTS.override.md` makes the entire root `AGENTS.md`
  — and with it the whole rules-projection surface — silently inactive.
- Local ChatGPT desktop managed worktrees automatically copy an ignored
  `AGENTS.override.md`; it does not need a `.worktreeinclude` entry.
- That copy guarantee does not apply to remote worktrees or worktrees created
  by the user from the CLI. The docs do not establish a general rule that an
  override should be gitignored in ordinary repositories.

## Discovery chain

- collected: 2026-07-08; reconfirmed 2026-07-24
- source: official Codex docs; openai/codex
  [`AgentsMdManager` at `0dfa778`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/core/src/agents_md_manager.rs);
  dated notes in
  [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled host contract for startup discovery; pinned implementation
  observation for environment-selection caching

- The project root is located by root markers (default: `.git`).
- `project_root_markers = []` disables parent traversal and makes the current
  cwd the project root.
- One project-doc file per directory.
- Candidate order is `AGENTS.override.md`, `AGENTS.md`, then configured
  fallback filenames. Creating `AGENTS.md` can therefore shadow a previously
  active same-directory fallback.
- Project files concatenate root→cwd; deeper guidance has soft positional
  precedence.
- No downward scanning below cwd; no sibling scanning.
- The public contract says the chain is built once per run (usually once per
  launched TUI session), so an edit requires a new run/session for dependable
  activation.
- Pinned-main observation: session initialization loads the chain; each turn
  calls refresh, but an unchanged environment-selection list reuses the cache.
  A changed list rebuilds one chain per selected environment cwd. This is not
  a public rebuild guarantee and never follows the file being edited.
- The same pinned implementation excludes project config layers when deriving
  root markers. This is an implementation observation; public docs do not
  promise that a project's own `.codex/config.toml` can redefine discovery of
  that project root.

## Claude project entry locations

- collected: 2026-07-08; reconfirmed 2026-07-24; `AGENTS.md` reading re-checked
  2026-10-19 against Claude Code 2.1.303
- source: official Claude Code docs; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled for supported locations and imports; precedence for two
  simultaneous project-entry locations is undocumented

- `CLAUDE.md` and `.claude/CLAUDE.md` are both official project-entry
  locations, documented as alternatives. Official docs do not define load
  order or precedence when both exist.
- `source-tree/v5` assigns neither path precedence. Both files present emits
  `dual-project-entry` and blocks the entry unit until the user resolves the
  divergence. This is Bridge policy derived from the undocumented host
  precedence, not a claim about which file Claude would load.
- `@path` imports expand at session launch; at most 4 hops; imports inside
  code spans and fenced code blocks are skipped; relative paths resolve from
  the containing file; paths outside the project require one-time approval.
- Since Claude Code 2.1.277 (re-checked 2026-10-19 on 2.1.303) Claude also
  reads `AGENTS.md` natively, conditionally. The default mode
  `claude-md-or-agents-md` reads `AGENTS.md` only when no `CLAUDE.md`,
  `.claude/CLAUDE.md`, or `CLAUDE.local.md` exists at the cwd or any parent.
  The mode `claude-md-and-agents-md` reads both and can be set only in
  user-level settings, `--settings`, or managed settings (ignored in project
  and local settings), so repository bytes cannot show whether it is on; it
  deduplicates only an `AGENTS.md` that the `CLAUDE.md` already imports or
  symlinks. `.claude/rules/` keep loading in both modes, nothing under
  `.agents/` is read as instructions, and a subdirectory `AGENTS.md` loads on
  demand when Claude reads a file there. The 2026-07-24 claim "Claude reads
  `CLAUDE.md`, not `AGENTS.md`" is withdrawn.
- After v5 control comments and Claude-only regions are subtracted, any active
  shared `@path` import blocks M3 projection: Claude expands it, while Codex
  has no equivalent preprocessing, and Bridge does not inline another file
  implicitly. `@AGENTS.md` is the high-risk self-referential case, not the
  only blocker. Imports inside closed code spans, fenced code blocks, or
  Claude-only regions are inert.

## Claude `/init` boundary

- collected: 2026-07-24
- source: official Claude Code docs; dated notes in
  [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled host contract

- Default `/init` reads Cursor rules and Copilot instructions.
- Only the new flow enabled by `CLAUDE_CODE_NEW_INIT=1` additionally reads
  `AGENTS.md`, Devin, Windsurf, and Cline rules.
- Bridge onboarding from an existing Codex project must not rely on default
  `/init` to ingest `AGENTS.md`.

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

## Rule discovery and `paths`

- collected: 2026-07-08; official mechanics reconfirmed 2026-07-24
- source: official Claude Code rules docs; dated notes in
  [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled host contract for documented mechanics; v5 validation is
  Bridge policy

- `.claude/rules/**` is discovered recursively; symlinked rule files are
  supported.
- Claude documents `paths` as the rule-frontmatter key. A path-scoped rule
  triggers when Claude READS a matching file, not on every tool use.
- One rule's whole `paths` list shares Claude's limits of 1,000 expanded
  patterns and 4 MiB of expanded UTF-8 pattern bytes. A pattern that would
  exceed the host budget remains unexpanded and its literal braces match no
  files. An invalid bracket expression matches no files while other patterns
  continue to work.
- `source-tree/v5` narrows this host surface to a deterministic portable
  schema: a rule has no frontmatter and is unscoped, or has a YAML map whose
  only key is `paths`; the value is a non-empty ordered list of unique strings.
  Bridge metadata never appears in YAML.
- Every v5 pattern must be non-empty, valid UTF-8, repo-relative, slash-based,
  and free of NUL, CR/LF, backticks, backslashes, empty/dot/dot-dot segments,
  leading slash, and unclosed brackets. Exact universal scopes `**` and
  `**/*`, plus duplicate patterns, are defined no-ops; an unscoped rule must
  omit frontmatter instead.
- Invalid, empty, no-op, duplicate, unrepresentable, or not-provably
  within-budget `paths` blocks the unit. It never falls back to an unscoped
  render.
- A valid scoped rule renders the exact reversible `pv2` applicability
  preamble. That preamble is natural-language attention scoping, not native
  Codex path enforcement, so the unit remains `semantic`.

## Bridge intent control comments

- collected: current contract adopted 2026-07-24
- source:
  [`source-tree/v5`](../skills/bridge-sentinel/references/source-tree-spec.md)
  and
  [`reconciliation/v3`](../skills/bridge-sync/references/reconciliation-spec.md)
- status: current Bridge policy

- Entry and rule intent uses only the strict single-line control grammar
  `<!-- bridge:intent <YYYY-MM-DD> <note> -->`. Dates must be valid; notes are
  1–120 Unicode scalar values, have no leading/trailing ASCII whitespace, and
  contain neither `--` nor NUL. Records remain oldest first.
- Entry records form one contiguous header from byte zero. Scoped-rule records
  immediately follow the closing `paths` frontmatter delimiter; unscoped-rule
  records start at byte zero.
- The v5 renderer strips the complete valid intent header before composing the
  Codex managed block. The carrier therefore never receives Bridge intent
  comments, independent of Codex's lack of comment preprocessing.
- Unknown `bridge:*` control comments, misplaced intent records, or any YAML
  frontmatter key named `bridge` blocks the unit. Intent is arbitration
  evidence, not ownership; a managed source requires a valid record from its
  first confirmed onboarding or annexation onward.
- **Archived observation only:** a 2026-07-21 Claude run tolerated an unknown
  YAML `bridge` key and stripped rule-file block comments. `source-tree/v5`
  deliberately does not depend on that undocumented tolerance. The old YAML
  intent form is not current syntax; rule-file comment stripping remains an
  empirical host observation, not a Bridge correctness dependency.

## Current v5 Bridge-policy consequences

The following are current Bridge rules derived from the host facts, not host
behavior:

- Dual Claude entries, any active shared import, and invalid/no-op/duplicate/
  over-budget `paths` block the affected unit. v5 defines no root-entry winner,
  implicit import expansion, or unscoped fallback for these cases.
- Root `AGENTS.md` eligibility is resolved from live activation inputs,
  separate from repo ownership bytes. Apply blocks when effective Codex
  configuration or carrier safety is unresolved; a root override shadows the
  target; root-marker evidence cannot prove the intended root; creating
  `AGENTS.md` would shadow an active fallback; the effective budget is zero;
  or planned UTF-8 bytes exceed a positive budget.
- The seven-eighths point of a positive budget is a confirmation warning, not
  a blocker by itself. Bridge reports activation facts and never edits Codex
  config, root markers, overrides, or fallback files to manufacture
  loadability.
- Live activation carriers must be safe regular files at exact root-child
  paths. Symlinks, reparse points, special types, or path escapes cannot
  supply trusted activation evidence.
- All selected changes sharing root `AGENTS.md` are one composed full-file
  write-protocol closure. Every manual-zone byte and untouched block is
  preserved in the complete planned pre/post images. An attested strict
  replace may bind the full preimage; otherwise an eligible text carrier may
  use one explicitly non-CAS `guarded-patch/v1` unique exact-region
  replacement with complete-file preflight and postverification. Marker
  malformation that prevents a trustworthy region map blocks the whole
  carrier.
- Repository bytes, host discoverability, and model adherence remain separate
  claims. After an actual root `AGENTS.md` write, v5 attaches
  `restart-may-be-required` and requires a new Codex run/session before testing
  activation.
- The Codex projection into root `AGENTS.md` assumes a project with a
  `CLAUDE.md` whose Claude runs in the default `claude-md-or-agents-md` mode.
  v5 cannot see the `claude-md-and-agents-md` mode from repository bytes and
  no longer claims that Claude ignores `AGENTS.md`; the report does not yet
  carry a hedge for managed `AGENTS.md` blocks loading twice on Claude under
  that mode.
