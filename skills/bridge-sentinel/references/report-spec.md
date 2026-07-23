# Bridge sentinel report specification

Spec version: report/v2.

This file is the durable normative home of the bridge sentinel's report
contract: the pinned input set, the closed report-state vocabulary and its
detection rules, the state ↔ sync-plan verb mapping, the per-surface
decision tables, the algorithm-independent diff shape, the closed
observation vocabulary, the fidelity tier rules, the skill portability lint
list, the report document format, and the deterministic
expectation-comparison rule. Its companion,
[`source-tree-spec.md`](source-tree-spec.md), owns the source-tree
conventions this file builds on: the unit model, the onboarding predicate,
the marker grammar, the rendering pipeline `render(u)`, the normalization
set N, the frontmatter schemas, the hook-intent entry format with its
ownership derivation and field normalization, and the skill portability
requirements. Together these two files are complete: an implementer or
sentinel-executing agent needs nothing else.

## Contents

- [Input set](#input-set)
- [Registry growth rule](#registry-growth-rule-binding-on-all-closed-sets)
- [States](#the-states-closed-set)
- [Decision tables](#per-surface-decision-tables)
- [Diff shape](#diff-shape-algorithm-independent-pinned)
- [Observations](#closed-observation-vocabulary)
- [Fidelity tiers](#fidelity-tiers-per-row-tier-column)
- [Skill portability lints](#skill-portability-lint-list-closed)
- [Report format](#report-document-format)
- [Expectation comparison](#expectation-files-and-the-deterministic-comparison-rule)

## Input set

**Repo bytes** := the worktree bytes of the files tracked by git
(`git ls-files`) under the scan root — in BOTH repo mode (scan root = repo
root) and fixture mode (scan root = a fixture directory such as
`fixtures/<name>/`, input = `git ls-files -- fixtures/<name>/` of the outer
repo). Every normative detection rule in this specification is a pure
function of repo bytes. Untracked files (e.g. an untracked
`.claude/settings.local.json`, `CLAUDE.local.md`, editor backups) never
enter normative output; they are reported only in the non-normative "Local
environment notes" section of the report.

**Scope excludes**: an expectation file (see "Expectation files and the
deterministic comparison rule" below) may declare exclude globs. Excludes
are a filter on the pinned input set, applied BEFORE every rule: a tracked
file matching any exclude glob is treated as absent for all unit
enumeration, detection rules, guards, and observations. Scope excludes are a
run parameter of a sentinel invocation, not a change to the three fixed scan
surfaces. Glob dialect (pinned): gitignore/git-pathspec semantics — patterns
are anchored at the scan root, `*` never crosses `/`, and `**` matches any
number of path segments and matches files as well as directories, so
`fixtures/**` matches every tracked file strictly under `fixtures/` and has
exactly one reading.

## Registry growth rule (binding on all closed sets)

Every token registry in this specification and its companion — states,
actions, tiers, lints, observations, annotations, finding details, surface
tokens, schema enums — is append-only. Future milestones may add tokens
under a new spec version; existing tokens are never repurposed, renamed, or
given new conditions. Unknown `bridge.*` sub-keys in rule-shard frontmatter
are reserved: the sentinel ignores them and never reports them as errors.

## The states (closed set)

A report row is keyed by `(surface, unit, host)`; the row key semantics,
unit enumeration, and the no-source-unit emission rule are the unit model in
`source-tree-spec.md`. Comparison machinery referenced below: raw-byte
equality (skills), normalized byte equality after rendering (agents-md),
field equality (hooks) — defined by the per-surface decision tables below
together with `render(u)`, normalization N, and the hook field normalization
in `source-tree-spec.md`. **Diff shape** is defined algorithm-independently
below. `onboarded` is the onboarding predicate of `source-tree-spec.md`,
evaluated once per run before any row.

| # | Token (canonical) | Chinese label | Definition | Detection rule (pure function of repo bytes) | Suggested action | Regime |
|---|---|---|---|---|---|---|
| 1 | `in-sync` | 一致 | Projection matches the source unit under the pinned comparison for its surface | skills: master and paired copy have identical relative file sets and every file pair is raw-byte identical. agents-md: a block with the unit's id exists, has no `mode` attribute, and its body equals the rendered body (`render(u)`, `source-tree-spec.md`) after normalization N. hooks: case H-OK below. Also the vacuous case H-DISABLED-OK. | `-` | onboarded (plus the vacuous `enabled: false` hooks case H-DISABLED-OK, reachable in either regime) |
| 2 | `drift` | 漂移 | Projection and source unit both exist in scope but the comparison fails, or exactly one side of an owned pairing is missing while the project is onboarded | Any failing comparison case in the decision tables below marked DRIFT. The suggested-action column is filled from the diff-shape rule below: additions-only → `adopt-to-source` (采纳回源); deletions-only → `reproject-from-source` (按源重投射); both → `conflict` (冲突). Intent-record and git evidence are cited in the evidence/notes only; they never change the state or suggested-action columns. | `adopt-to-source` \| `reproject-from-source` \| `conflict` | onboarded only (every DRIFT case either presupposes an onboarding trigger or carries an explicit not-onboarded branch mapping to states 3/4/5 — H-T4-PRESENT's not-onboarded branch keeps the state-4 declared-unsynced row) |
| 3 | `adoption-candidate` | 收编候选 | Unmanaged existing content sitting at an expected projection location | skills: a `.agents/skills/<name>/` unit with no master of the same name (both regimes; unit column = the path `.agents/skills/<name>`); or — not-onboarded regime only — a copy whose same-name master exists but is not whole-directory byte-identical (a diverged copy never onboards a project; without a covenant in force, divergence cannot be drift). agents-md: the project is not-onboarded, root `AGENTS.md` exists, contains zero well-formed managed blocks, and is not whitespace-only (unit column = `AGENTS.md`). (In the onboarded regime, AGENTS.md text outside managed blocks is the manual zone and produces no row.) | `annex-or-keep` (收编或保留) | both |
| 4 | `declared-unsynced` | 声明不同步 | A tier-4 declaration: the source unit explicitly declares no projection for this host | hooks only at M1: the entry's `targets.<host>` has `surface: none` and `tier: declared-unsynced`, and the H-T4-PRESENT exception does not fire. | `-` | both |
| 5 | `not-projected` | 未投射（待引导） | The source unit has no projection and the project has never been onboarded; NOT drift | The project is not-onboarded AND the unit's expected projection element is absent or non-identical (agents-md: no block with the unit's id; hooks: cases H-NOFILE / H-MISSING with regime not-onboarded; skills: master with no same-name byte-identical copy). | `onboard` (引导) | not-onboarded only |
| 6 | `no-source-unit` | 无源单元 | Explicit vacuous-surface row: the surface has nothing to check | Emitted per the no-source-unit emission rule (unit model, `source-tree-spec.md`). | `-` | both |
| 7 | `semantic-mode-block` | 语义映射区块（逐字校验不适用） | A managed block self-declares a non-verbatim render mode; byte verification does not apply | agents-md only: a well-formed block whose start marker carries a `mode` attribute with any value. No byte comparison is performed and no LLM judgment substitutes for it. | `defer-to-arbitration` (仲裁时按需核验) | onboarded only (a well-formed block fires onboarding trigger (a)). |

Project-level flag (not a row): `onboarded` (已接入) / `not-onboarded`
(未接入（待引导）), computed by the onboarding predicate in
`source-tree-spec.md`, printed in the report header line `- onboarding: …`
which is compared by the comparison rule below.

Annotations (not states; annotation grammar in the table rules below):
fidelity tier (the semantic tokens of the tier section below, printed in the
`tier` column); portability lints (`lint:<token>`, lint list below);
`awaiting-host-trust` (已写入、待 host 信任) — a STANDING HEDGE attached to
every row with host `codex`, state `in-sync`, on the `hooks` and `skills`
surfaces only. The v2 host profile treats `.codex/hooks.json` as trust-gated
and conservatively hedges `.agents/skills/` activation; root `AGENTS.md` is
outside this hedge, so `agents-md` rows never carry it. Trust state is not
observable from repo bytes, so this is never a fixture-detectable state —
always a per-row annotation, complemented by the pinned report-level hedge
sentence (the Codex activation hedge below). Dated host evidence lives in
`knowledge/hooks.md` and `knowledge/skills.md`.

## State ↔ sync-plan verb mapping (for docs traceability)

`in-sync` ↔ `unchanged`; `drift`→`reproject-from-source` ↔ `create`
(artifact absent) / `update` (artifact present); `drift`→`adopt-to-source` ↔
`adopt`; `drift`→`conflict` ↔ `conflict`; `adoption-candidate` ↔ 收编或保留;
`declared-unsynced` ↔ `unsupported`; `not-projected` ↔ (onboarding plan, no
verb — never `create`); `awaiting-host-trust` ↔ 已写入、待 host 信任
(annotation on both sides). From M2 the suggested-action column graduates
from "suggested" to "executed" without a row-format break; the create/update
refinement stays an evidence-line detail, never a compared column.

## Per-surface decision tables

All comparisons below read only repo bytes. "Absent" for a file means not in
the (scope-filtered) tracked set. Every case row states its regime behavior;
cases without an explicit not-onboarded branch are unreachable in the
not-onboarded regime because their condition fires a trigger of the
onboarding predicate in `source-tree-spec.md`.

**skills** (per name n in masters ∪ copies):

| Case | Condition | Result |
|---|---|---|
| S1 | master ∃, copy ∃, identical file sets, every file raw-byte equal | `in-sync` (this pair fires onboarding trigger (c), so the project is onboarded) |
| S2 | master ∃, copy ∃, any difference | onboarded: `drift`, shape per the diff-shape rule over the whole directory pair. not-onboarded: master row = `not-projected`; copy row = `adoption-candidate` (unit = `.agents/skills/<n>`) |
| S3 | master ∃, copy ∄ | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| S4 | master ∄, copy ∃ | `adoption-candidate` (unit = `.agents/skills/<n>`; both regimes) |

No normalization is applied on this surface (strict byte compare; the
projection mechanism is a byte copy, so normalization has no role). There is
no entrypoint exemption. Lints (see the lint list below) are computed on the
master only and attach to the master's row regardless of state.

**agents-md** (per source unit u, and per parsed block b):

| Case | Condition | Result |
|---|---|---|
| A1 | block(u.id) ∃, no `mode` attr, N(body) == N(render(u)) | `in-sync` |
| A2 | block(u.id) ∃, no `mode` attr, bodies differ | `drift`; shape per the diff-shape rule on the line sequences of N(render(u)) vs N(body) |
| A3 | block(u.id) ∄ | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| A4 | block b whose id derives (per the unit model) from a source file that does not exist | `drift`/`adopt-to-source`; unit = b.id; tier column `-` |
| A5 | block with a `mode` attribute present | `semantic-mode-block` (no byte check) |
| A6 | root AGENTS.md absent | every source unit hits A3's absent branch; no adoption-candidate row |
| A7 | not-onboarded, AGENTS.md ∃, zero well-formed blocks, not whitespace-only | one `adoption-candidate` row, unit `AGENTS.md`, plus one `not-projected` row per source unit |

Regime note: A1, A2, A4, A5 each require a well-formed block, which fires
onboarding trigger (a) — they are unreachable in the not-onboarded regime by
construction. Content outside well-formed blocks in the onboarded regime is
the manual zone: never compared, never reported as a row.

**hooks** (per entry e, per host h with declared surface s; file F =
`.claude/settings.json` top-level `hooks` object for claude,
`.codex/hooks.json` top-level `hooks` object for codex; "owned group" and "marked
handler" per the unit model and the declared-keys derivation in
`source-tree-spec.md`; "handler-equal" := every declared field equal per the
field normalization AND no undeclared keys per the allowed-key rule, both in
`source-tree-spec.md`):

| Case | Condition | Result |
|---|---|---|
| H-T4 | s = `none` (tier-4) and H-T4-PRESENT does not fire | `declared-unsynced` (both regimes) |
| H-T4-PRESENT | s = `none` but F contains a handler marked `[bridge:<e.id>]`, or the `(e.event, e.matcher)` group of F contains a command handler whose `command` equals e.command | onboarded: `drift`/`conflict` (replaces the declared-unsynced row). not-onboarded (possible only for the unmarked variant): the `declared-unsynced` row stands; the group falls to the `undeclared-hooks-key` observation channel |
| H-NOFILE | F absent, or not valid JSON (emit `json-parse-error` observation), or lacks the hooks object | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| H-MISSING | owned group for (e.event, e.matcher) absent, or present with zero command handlers | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| H-OK | e.enabled = true; the owned group contains exactly one command handler; it is handler-equal to e | `in-sync` (fires onboarding trigger (b), so onboarded) |
| H-EXTRA-KEYS | unique handler, declared fields all equal, handler has undeclared keys | `drift`/`adopt-to-source` |
| H-FIELD-ABSENT | unique handler, a declared field absent from the handler, no undeclared keys, all present fields equal | `drift`/`reproject-from-source` |
| H-FIELD-DIFF | unique handler, any declared field value differs (or both undeclared keys and missing/differing fields) | `drift`/`conflict` |
| H-MULTI | more than one command handler in the owned group | if at least one is handler-equal to e, the others are projection-only additions → `drift`/`adopt-to-source`; if none is handler-equal → `drift`/`conflict` |
| H-DISABLED-OK | e.enabled = false and no command handler exists in any owned group for e on F and no handler marked `[bridge:<e.id>]` exists in F | `in-sync` (vacuously consistent; reachable in either regime) |
| H-DISABLED-PRESENT | e.enabled = false and a matching command handler or `[bridge:<e.id>]`-marked handler exists in F | `drift`/`conflict` (source explicitly declares OFF; projection says ON — two different intents; never silently re-enabled) |
| H-MARKED-ORPHAN | a handler in F carries `statusMessage` beginning `[bridge:<id>]` where `<id>` has no schema-valid entry in the intent document | one row per (id, F): `drift`/`adopt-to-source`; unit = `hooks/<id>`, host = F's host, tier `-`. (The marker fires onboarding trigger (b), so the project is onboarded whenever this case exists.) |

Regime note: H-EXTRA-KEYS, H-FIELD-ABSENT, H-FIELD-DIFF, H-MULTI each
require a command handler inside an owned group, which fires onboarding
trigger (b) — they are unreachable in the not-onboarded regime by
construction.

Reverse direction: command handlers inside owned groups are covered above
(extras → adopt or conflict); marked handlers whose id resolves to a
schema-valid entry are evaluated under that entry's cases (the marker is
reinforcement, never compared beyond its id); marked handlers with no entry
are H-MARKED-ORPHAN rows. Hook groups that are neither owned by any entry
nor containing a marked handler are out of scope: they produce one
`undeclared-hooks-key` observation per (file, event, matcher) group and no
row (user-owned by default; the user may ask to list them as adoption
candidates — free-form, never a normative row at M1). Two schema-valid
entries declaring the same `(event, matcher)` pair for the same host make
BOTH entries schema-invalid per the duplicate-declaration guard in
`source-tree-spec.md` (`intent-doc-anomaly`, no rows) — ownership must be
unambiguous per group. Prose aspects (Trigger, Purpose, Environment, Failure
policy) never enter the consistency verdict.

## Diff shape (algorithm-independent, pinned)

For two line sequences A (rendered source) and B (projection), computed
after the surface's comparison preprocessing (raw lines for skills;
N-normalized lines for agents-md):

- **additions-only** := A is a proper subsequence of B (every line of A
  occurs in B in order; B ≠ A) → `adopt-to-source`.
- **deletions-only** := B is a proper subsequence of A →
  `reproject-from-source`.
- **both** := neither → `conflict`.

For multi-file units (skills): a file only in the copy contributes
additions; a file only in the master contributes deletions; a file present
on both sides with different bytes contributes its own line-level shape.
Unit shape = additions-only iff every contribution is additions-only;
deletions-only iff every contribution is deletions-only; otherwise both. The
subsequence definition makes the classification independent of any diff
algorithm — `git diff` is the mechanization, never the definition (a
re-implementation at M5 CI must reproduce the subsequence test, not any
particular hunk output). Consequence accepted by design: a one-byte
substitution inside a line is classified `both` → `conflict` (precision over
ergonomics; conflict is the safe verdict because it always asks the user).

## Closed observation vocabulary

Observations are normative report lines (format in the observations-section
rules below), each `- <token>: <repo-relative-path>` plus a pinned
parenthesized detail where noted. Sorted byte-wise ascending by the whole
line. If none: the single line `- (none)`. No M1 observation token is
environment-dependent (all fire on tracked bytes only); the registry may
mark future tokens environment-dependent, which the comparison rule below
then drops from both sides.

| Token | Emitted when | Detail |
|---|---|---|
| `surface-shadowed` | root `AGENTS.override.md` exists (first-class finding: the whole rules-projection surface is silently inactive) | none |
| `agents-md-size` | root `AGENTS.md` size ≥ floor(7 × B / 8), where B is the effective combined Codex project-document budget: a positive integer `project_doc_max_bytes` from tracked `.codex/config.toml`, otherwise the v2 pinned default 32768; do not emit when B = 0 because the surface is disabled | `(<n> bytes of <B>)` with n the exact byte size |
| `self-referential-import` | the entry source file contains a token matching `(?<=^|\s)@[A-Za-z0-9_./~-]+` whose path component ends with `AGENTS.md` — searched over the entire file INCLUDING code spans and fences (deliberate: determinism over false-positive avoidance; Claude itself skips code-span imports, so a fenced match is a false-positive hazard flag, which is acceptable) | none |
| `dual-project-entry` | both `CLAUDE.md` and `.claude/CLAUDE.md` exist at the scan root | none |
| `nested-claude-md` | a tracked `CLAUDE.md` exists at any non-root directory | one line per file |
| `nested-agents-md` | a tracked `AGENTS.md` or `AGENTS.override.md` exists at any non-root directory | one line per file |
| `nested-claude-skills` | a tracked `.claude/skills/` directory exists at any non-root directory | one line per directory |
| `nested-agents-skills` | a tracked `.agents/skills/` directory exists at any non-root directory | one line per directory |
| `legacy-commands-dir` | `.claude/commands/` contains ≥ 1 tracked `.md` file | none |
| `legacy-codex-skills` | a tracked `.codex/skills/` directory exists (outside the documented Codex skills profile, whose project location is `.agents/skills/`; the path is undocumented but may still be loaded by current CLIs) | none |
| `config-toml-budget` | `.codex/config.toml` is tracked, readable TOML, and sets `project_doc_max_bytes` to a non-negative integer (value 0 disables the whole surface) | `(project_doc_max_bytes=<value>)` |
| `undeclared-hooks-key` | see the hooks decision table's reverse direction above | `(<Event> matcher=<matcher or omitted>)` |
| `local-hooks-present` | a TRACKED `.claude/settings.local.json` carries a `hooks` key (untracked ones go to Local environment notes instead) | none |
| `json-parse-error` | a hooks projection file exists but is not valid JSON | none |
| `marker-anomaly` | any malformed/unpaired marker condition of the marker malformation rules in `source-tree-spec.md` | one line per offending line number: `(line <n>)` |
| `intent-doc-anomaly` | any hook-intent schema violation in `.claude/rules/hooks.md` (schema in `source-tree-spec.md`) | pinned priority rule: `(entry <id>)` when a level-2 heading matching the hook-intent entry grammar was recognized for the offending construct; otherwise `(line <n>)` where n is the 1-based line number of the first line of the offending construct |
| `unrepresentable-source-path` | a would-be source unit's path contains characters outside the source-path charset of the marker grammar in `source-tree-spec.md` | one line per file |

The nested-file observations carry the pinned hedge wording in the free-form
notes: "may take positional precedence over root content in subdirectory
sessions" (nested files cannot mechanically remove root managed blocks —
concatenation semantics — but can contradict them by position).

## Fidelity tiers (per row, `tier` column)

The tier column uses the four self-describing tokens end-to-end — the same
tokens hook intent entries declare in their `targets.<host>.tier` field
(schema in `source-tree-spec.md`); no numeric aliases, no mapping layer.

| Token | Chinese | Meaning |
|---|---|---|
| `native` | 原生等价 | isomorphic mechanism, mechanical transfer |
| `structural` | 结构降级 | content fully expressible, different carrier |
| `semantic` | 语义降级 | semantics reproduced in natural language |
| `declared-unsynced` | 声明不同步 | tier-4; no counterpart, prose would fake enforcement |
| `-` | — | no source unit behind the row (adoption, orphan, vacuous) |

Assignment rules (pure functions of the source unit):

| Row kind | Tier |
|---|---|
| agents-md `entry` unit | `structural` (block carrier replaces the CLAUDE.md organizing mechanism) |
| agents-md rule-shard unit WITHOUT non-empty `paths` frontmatter | `structural` |
| agents-md rule-shard unit WITH non-empty `paths` frontmatter | `semantic` (mechanical scoping becomes the applicability preamble = attention scoping) |
| agents-md orphan block (case A4) and marked-orphan hook rows | `-` |
| skills unit rows (any state except adoption-candidate) | `native` (mechanism tier: byte copy; behavioral degradation is expressed by lints, never by lowering the tier — bytes stay comparable) |
| hooks rows | the entry's declared `targets.<host>.tier` value, printed verbatim (`native` or `declared-unsynced` at M1; the hook-intent schema in `source-tree-spec.md` pins the M1-valid set). Cross-validating a declared tier against the knowledge tables is deferred to M4. |
| adoption-candidate and no-source-unit rows | `-` |

Every `in-sync` claim therefore rests on an explainable tier (the tier
column is never empty on a unit row that has a source unit).

## Skill portability lint list (closed)

Lints are deterministic checks computed on the MASTER
(`.claude/skills/<n>/`) only; they attach as annotations `lint:<token>` to
the master's row in any state; they never affect the state column. The
portability requirements they enforce are normative MUSTs in
`source-tree-spec.md`; a violation is a lint, not an error.

**BOM rule for lint computation (pinned)**: for LINT computation only,
frontmatter recognition skips a leading UTF-8 BOM — if `SKILL.md` begins
with bytes `EF BB BF`, drop those three bytes before testing whether the
first line is exactly `---` (and emit `lint:utf8-bom`). Everywhere else —
the rendering pipeline and the frontmatter schemas of
`source-tree-spec.md` — a leading BOM is NOT skipped: a BOM'd file has no
recognizable frontmatter there. This asymmetry is deliberate: lints diagnose
what each host would see (Codex's parser failure is the finding), while
rendering must stay byte-honest.

| Token | Condition (pure function of master bytes) | Pinned wording (used verbatim in the report's "Evidence and notes" section) |
|---|---|---|
| `missing-name` | SKILL.md has no YAML frontmatter block starting at line 1 (after the lint BOM-skip), or the `name` key is absent, or its value is empty/whitespace-only | "SKILL.md lacks a non-empty `name`; it does not satisfy the cross-host Agent Skills contract." |
| `invalid-name` | the directory name violates the 1–64 character, `[a-z0-9-]`, edge-hyphen, consecutive-hyphen, or reserved-word rules; or a present `name` value is not a string, differs from the directory, or violates the same grammar | "The skill name violates the cross-host name grammar or differs from its directory; discovery is not portable." |
| `missing-description` | SKILL.md has no YAML frontmatter block starting at line 1 (after the lint BOM-skip), or the `description` key is absent, or its value is empty/whitespace-only | "SKILL.md lacks a non-empty `description`; the skill does not satisfy the cross-host discovery contract." |
| `invalid-description` | a present `description` value is not a string, exceeds 1024 characters, or contains `<` or `>` | "The description violates the cross-host scalar, length, or no-angle-brackets constraint." |
| `implementation-specific-frontmatter` | the frontmatter contains a top-level key outside `name`, `description`, `license`, `metadata`, `allowed-tools`, and `compatibility` | "The frontmatter contains a host extension or unknown key; the skill is mechanically copied but is not behaviorally portable." |
| `codex-validator-gap` | the frontmatter contains the Agent Skills standard `compatibility` key, which the v2 Codex validator profile does not accept | "The standard `compatibility` key is outside the report/v2 Codex validator profile; verify the target Codex release before distribution." |
| `dynamic-content` | the SKILL.md body (bytes after the closing `---` line) contains any of these literal tokens: `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, a token matching `(?<=^|\s)\$[1-9]\b`, a line whose first non-space characters are backtick-exec (`!` immediately followed by a backtick), or a token matching `(?<=^|\s)@[A-Za-z0-9_./~-]+` — searched over the whole body including code fences (deliberate: determinism over false-positive avoidance) | "The body uses Claude dynamic-content features; in Codex they reach the model as inert literal text — never executed, never substituted. Consistent but degraded on Codex." |
| `utf8-bom` | any file in the master directory begins with bytes `EF BB BF` | "The master contains file(s) beginning with a UTF-8 BOM; a BOM before line-one frontmatter breaks portable skill recognition." |

Growth rule: new lints get new tokens; an existing token's condition never
changes within a spec version.

## Report document format

### Document skeleton

```markdown
# Bridge Sentinel Report

- project: <directory name of the scan root>
- scan root: <path as invoked>
- scope excludes: <comma+space-separated globs, or (none)>
- date: <YYYY-MM-DD>
- spec: report/v2
- scan surfaces: agents-md, hooks, skills
- onboarding: <onboarded|not-onboarded>

## Findings

| surface | unit | host | state | suggested action | tier | annotations |
|---|---|---|---|---|---|---|
<rows>

## Observations

<observation lines or "- (none)">

## Evidence and notes

<free-form>

## Local environment notes

<free-form; untracked files, trust caveats observed live, etc.>
```

**Hard read-only rule**: the sentinel MUST NOT create, modify, or delete any
file under the scanned project; scratch files for rendering and diff
mechanics go OUTSIDE the project (the session scratchpad). The report is
session output. The product writes nothing to disk.

Non-normative note (outside the sentinel's checklist, never part of the rule
above): when the scanned project is the agent-config-bridge repo itself, the
operating agent may save a copy of the session-output report under
`.debug-output/` under that repo's own debug-output convention — an agent
action governed by repo conventions, not a product write path; never
committed.

### Normative table rules

- Cell grammar: `| ` value ` |` — exactly one space padding each side, no
  column alignment padding. Header row and separator row exactly as shown in
  the skeleton.
- Empty cells use the single character `-`.
- Row sort: byte-wise ascending by (surface, unit, host).
- `annotations` cell: tokens sorted byte-wise ascending, joined by `; `.
  Tokens: `awaiting-host-trust`, `lint:<token>`. Lint wording sentences
  (pinned in the lint list above) go in "Evidence and notes", never in the
  cell.
- State, suggested-action, tier tokens: exactly the closed sets of this
  specification (actions: `-`, `adopt-to-source`, `reproject-from-source`,
  `conflict`, `annex-or-keep`, `onboard`, `defer-to-arbitration`; tiers:
  `-`, `native`, `structural`, `semantic`, `declared-unsynced`).

### Observations section

One line per observation per the observation vocabulary above, format
`- <token>: <repo-relative-path>` + optional pinned ` (<detail>)`; sorted
byte-wise by whole line; `- (none)` when empty.

## Expectation files and the deterministic comparison rule

**Expected-report file format**: each expectation (`expected-report.md`)
declares its own run parameters and its normative content, nothing else:

```markdown
- expectation: report/v2
- scan root: <path relative to the directory containing this file>
- scope excludes: <comma+space-separated globs, or (none)>
- onboarding: <onboarded|not-onboarded>

## Findings

<header row, separator row, and expected rows>

## Observations

<expected observation lines or "- (none)">
```

`scan root` is resolved relative to the expectation file's directory (`.` =
the fixture itself; `../..` = the repo root for the dogfood expectation);
`scope excludes` is passed to the sentinel as its run parameter (semantics
per the input-set definition above). This generalizes to any future
expectation target with no new machinery — there are no magic directory
names.

**Comparison rule (this IS the M1 acceptance check; parse-based so future
spec versions fail loudly instead of byte-breaking):**

1. Run the sentinel with scan root and scope excludes taken from the
   expectation header.
2. Read both documents and apply normalization N (`source-tree-spec.md`) to
   each before parsing.
3. Version gate: the produced `- spec:` value must equal the expectation's
   `- expectation:` value (both `report/v2`). A mismatch is FAIL — never a
   silent cross-version comparison.
4. Run-parameter echo: the produced `- scope excludes:` value must equal the
   expectation's (sanity check that the run parameters were honored).
5. `- onboarding:` values must be equal.
6. Findings table: the produced header row must byte-equal the expected
   header row (this keys the cell count to the header; a column change is a
   spec-version change). Parse each data row by splitting on `|`, dropping
   the empty first and last fields, and stripping exactly one leading and
   one trailing space per cell. Sort both row lists byte-wise and compare as
   SEQUENCES: equal length (duplicates count — multiset semantics) and
   pairwise byte-equal cells.
7. Observations: compare the two line lists as sorted sequences
   (byte-per-line, equal length), after first removing from BOTH sides any
   line whose token the observation registry marks environment-dependent
   (none at M1; the clause exists so future environment-dependent findings
   never destabilize expectations across machines).
8. Everything else — `project`, `scan root` (produced side), `date`,
   evidence, notes, local environment notes — is free-form and never
   compared.

PASS iff 3–7 all hold. Because rows are emitted sorted, a plain visual diff
is also meaningful to a human operator, but the normative check is the
parse-based comparison above.

## Codex activation hedge

Every report whose Findings contain at least one host=codex row includes
this sentence in "Evidence and notes":

> Codex-side surfaces are verified as written bytes only; activation is
> subject to host trust and configuration and is not observable from
> repository bytes.

This report-level sentence complements — never replaces — the per-row
`awaiting-host-trust` annotation.
