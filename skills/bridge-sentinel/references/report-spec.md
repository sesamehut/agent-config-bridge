# Bridge sentinel report specification

Spec version: report/v2.

This file defines sentinel inputs, findings, observations, serialization, and
expectation comparison. Its companion,
[`source-tree-spec.md`](source-tree-spec.md), defines source units,
onboarding, rendering, hook ownership, and portability requirements.

## Contents

- [Input set](#input-set)
- [Registry growth rule](#registry-growth-rule-binding-on-all-closed-sets)
- [States](#the-states-closed-set)
- [Decision tables](#per-surface-decision-tables): [skills](#skills),
  [agents-md](#agents-md), [hooks](#hooks)
- [Diff shape](#diff-shape-algorithm-independent-pinned)
- [Observations](#closed-observation-vocabulary)
- [Fidelity tiers](#fidelity-tiers-per-row-tier-column)
- [Skill portability lints](#skill-portability-lint-list-closed)
- [Report format](#report-document-format)
- [Expectation comparison](#expectation-files-and-the-deterministic-comparison-rule)
- [Codex activation hedge](#codex-activation-hedge)

## Input set

**Repo bytes** are worktree bytes selected by `git ls-files` under the scan
root. Repo mode uses the repository root. Fixture mode uses the fixture path
within the outer repository's tracked set. Untracked files appear only in
Local environment notes.

Filter repo bytes by expectation scope excludes before applying any rule.
Patterns are scan-root-anchored gitignore/pathspec globs: `*` does not cross
`/`; `**` crosses any number of segments and matches files and directories.

## Registry growth rule (binding on all closed sets)

Closed token registries in both specifications are append-only within a
version. Additions require a new spec version; existing tokens retain their
names and conditions. Ignore reserved unknown `bridge.*` frontmatter subkeys.

## The states (closed set)

A row uses the `(surface, unit, host)` model in `source-tree-spec.md`.
Evaluate onboarding once before emitting rows.

| Token | Meaning | Suggested action | Regime |
|---|---|---|---|
| `in-sync` | Projection matches its source, including H-DISABLED-OK absence | `-` | onboarded; H-DISABLED-OK in either regime |
| `drift` | An onboarded owned pairing differs or is incomplete | derived from diff shape or its decision case | onboarded |
| `adoption-candidate` | Unmanaged content occupies a projection location | `annex-or-keep` | both |
| `declared-unsynced` | A hook target declares `surface: none` and tier `declared-unsynced` | `-` | both |
| `not-projected` | A source unit lacks an equivalent projection before onboarding | `onboard` | not-onboarded |
| `no-source-unit` | The surface has no source unit | `-` | both |
| `semantic-mode-block` | A managed block carries a `mode` attribute; deterministic byte comparison is inapplicable | `defer-to-arbitration` | onboarded |

The unit model's `no-source-unit` rule and the decision tables are the sole
detection rules. Intent records and Git evidence may appear in notes but do
not override the resulting state or action. Print the project-level predicate as
`- onboarding: <onboarded|not-onboarded>`.

Annotations are `lint:<token>` and `awaiting-host-trust`. Attach
`awaiting-host-trust` to `in-sync` Codex rows on `hooks` and `skills`, never
to `agents-md`. Repository bytes do not determine live trust; also emit the
report-level activation hedge below.

## State ↔ sync-plan verb mapping (for docs traceability)

| Finding | Sync-plan equivalent |
|---|---|
| `in-sync` | `unchanged` |
| `drift` / `reproject-from-source` | `create` if absent; `update` if present |
| `drift` / `adopt-to-source` | `adopt` |
| `drift` / `conflict` | `conflict` |
| `adoption-candidate` | annex or keep |
| `declared-unsynced` | `unsupported` |
| `not-projected` | onboarding plan, without a sync verb |

`awaiting-host-trust` maps to the same annotation in a sync plan. The
create/update refinement belongs in evidence, not the compared action column.

## Per-surface decision tables

“Absent” means absent from scope-filtered repo bytes. Results marked for both
regimes are exceptions; otherwise, a case without a not-onboarded branch
triggers onboarding.

### Skills

Evaluate each name `n` in masters ∪ copies.

| Case | Condition | Result |
|---|---|---|
| S1 | master ∃, copy ∃, identical file sets, every file raw-byte equal | `in-sync` (this pair fires onboarding trigger (c), so the project is onboarded) |
| S2 | master ∃, copy ∃, any difference | onboarded: `drift`, shape per the diff-shape rule over the whole directory pair. not-onboarded: master row = `not-projected`; copy row = `adoption-candidate` (unit = `.agents/skills/<n>`) |
| S3 | master ∃, copy ∄ | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| S4 | master ∄, copy ∃ | `adoption-candidate` (unit = `.agents/skills/<n>`; both regimes) |

Use raw bytes for all files, with no entrypoint exemption. Compute lints on
the master and attach them to its row in any state.

### Agents-md

Evaluate each source unit `u` and parsed block `b`.

| Case | Condition | Result |
|---|---|---|
| A1 | block(u.id) ∃, no `mode` attr, N(body) == N(render(u)) | `in-sync` |
| A2 | block(u.id) ∃, no `mode` attr, bodies differ | `drift`; shape per the diff-shape rule on the line sequences of N(render(u)) vs N(body) |
| A3 | block(u.id) ∄ | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| A4 | block b is unattributable because its id derives from a missing source or it is a later duplicate of an already paired id | `drift`/`adopt-to-source`; unit = b.id for a missing-source orphan, otherwise `<b.id>#<ordinal>` in file order; tier `-` |
| A5 | block with a `mode` attribute present | `semantic-mode-block`; no byte or LLM comparison |
| A6 | root AGENTS.md absent | every source unit hits A3's absent branch; no adoption-candidate row |
| A7 | not-onboarded, AGENTS.md ∃, zero well-formed blocks, not whitespace-only | one `adoption-candidate` row, unit `AGENTS.md`, plus one `not-projected` row per source unit |

A4 governs unattributable blocks even when they carry `mode`; A5 applies only
to a paired block. A1, A2, A4, and A5 trigger onboarding. In an onboarded
project, content outside well-formed blocks is an unreported manual zone.

### Hooks

Evaluate each entry `e` and declared host `h`. Let `s` be its
surface and `F` the host's top-level `hooks` object. “handler-equal” means all
host-applicable declared fields match and no undeclared handler keys exist,
using `source-tree-spec.md`.

| Case | Condition | Result |
|---|---|---|
| H-T4-PRESENT | s = `none` and (F contains a handler marked `[bridge:<e.id>]`, or e.command is declared and the `(e.event, e.matcher)` group of F contains a command handler whose `command` equals e.command) | onboarded: `drift`/`conflict` (replaces the declared-unsynced row). not-onboarded (possible only for the unmarked variant): the `declared-unsynced` row stands; the group falls to the `undeclared-hooks-key` observation channel |
| H-T4 | s = `none` and H-T4-PRESENT does not fire | `declared-unsynced` (both regimes) |
| H-DISABLED-PRESENT | s ≠ `none`; e.enabled = false; a command handler exists in any owned group for e on F, or a `[bridge:<e.id>]`-marked handler exists in F | `drift`/`conflict` (source off, projection on) |
| H-DISABLED-OK | s ≠ `none`; e.enabled = false; no command handler exists in any owned group for e on F and no handler marked `[bridge:<e.id>]` exists in F | `in-sync` (vacuously consistent; reachable in either regime) |
| H-NOFILE | F absent, or not valid JSON (emit `json-parse-error` observation), or lacks the hooks object | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| H-MISSING | owned group for (e.event, e.matcher) absent, or present with zero command handlers | onboarded: `drift`/`reproject-from-source`; not-onboarded: `not-projected` |
| H-OK | e.enabled = true; the owned group contains exactly one command handler; it is handler-equal to e | `in-sync` (fires onboarding trigger (b), so onboarded) |
| H-EXTRA-KEYS | unique handler, declared fields all equal, handler has undeclared keys | `drift`/`adopt-to-source` |
| H-FIELD-ABSENT | unique handler, a declared field absent from the handler, no undeclared keys, all present fields equal | `drift`/`reproject-from-source` |
| H-FIELD-DIFF | unique handler, any declared field value differs (or both undeclared keys and missing/differing fields) | `drift`/`conflict` |
| H-MULTI | more than one command handler in the owned group | if at least one is handler-equal to e, the others are projection-only additions → `drift`/`adopt-to-source`; if none is handler-equal → `drift`/`conflict` |
| H-MARKED-ORPHAN | a handler in F carries `statusMessage` beginning `[bridge:<id>]` where `<id>` has no schema-valid entry in the intent document | one row per (id, F): `drift`/`adopt-to-source`; unit = `hooks/<id>`, host = F's host, tier `-`. (The marker fires onboarding trigger (b), so the project is onboarded whenever this case exists.) |

For each valid entry/host, apply the first matching case in table order.
Evaluate H-MARKED-ORPHAN afterward over marked handlers without valid entries.
H-EXTRA-KEYS, H-FIELD-ABSENT, H-FIELD-DIFF, and H-MULTI trigger onboarding.
Handlers in owned groups use the table. A marked handler with a valid id uses
that entry's cases; one without a valid entry uses H-MARKED-ORPHAN. A group
that is neither owned nor marked emits one `undeclared-hooks-key` per
`(file, event, matcher)` and no row. Duplicate ownership declarations make
all involved entries invalid, emitting `intent-doc-anomaly` and no rows.
Hook prose does not affect consistency.

## Diff shape (algorithm-independent, pinned)

For source lines A and projection lines B after surface preprocessing:

- **additions-only** := A is a proper subsequence of B (every line of A
  occurs in B in order; B ≠ A) → `adopt-to-source`.
- **deletions-only** := B is a proper subsequence of A →
  `reproject-from-source`.
- **both** := neither → `conflict`.

For skills, a copy-only file contributes additions, a master-only file
contributes deletions, and a changed pair contributes its line shape. The
unit is additions-only or deletions-only only when every contribution has
that shape; otherwise it is both. The subsequence test, not diff hunk output,
is normative. A within-line substitution is `both`.

## Closed observation vocabulary

Emit each observation as `- <token>: <repo-relative-path>` plus the specified
detail. All v2 observations derive from repo bytes; none is
environment-dependent.

| Token | Emitted when | Detail |
|---|---|---|
| `surface-shadowed` | root `AGENTS.override.md` exists | none |
| `agents-md-size` | root `AGENTS.md` size ≥ floor(7 × B / 8), where B is the effective combined Codex project-document budget: a positive integer `project_doc_max_bytes` from tracked `.codex/config.toml`, otherwise the v2 pinned default 32768; do not emit when B = 0 because the surface is disabled | `(<n> bytes of <B>)` with n the exact byte size |
| `self-referential-import` | anywhere in the entry source, including code spans and fences, a token matches `(?<!\S)@[A-Za-z0-9_./~-]+` and its path component ends `AGENTS.md` | none |
| `dual-project-entry` | both `CLAUDE.md` and `.claude/CLAUDE.md` exist at the scan root | none |
| `nested-claude-md` | a tracked `CLAUDE.md` exists at any non-root directory | one line per file |
| `nested-agents-md` | a tracked `AGENTS.md` or `AGENTS.override.md` exists at any non-root directory | one line per file |
| `nested-claude-skills` | a tracked `.claude/skills/` directory exists at any non-root directory | one line per directory |
| `nested-agents-skills` | a tracked `.agents/skills/` directory exists at any non-root directory | one line per directory |
| `legacy-commands-dir` | `.claude/commands/` contains ≥ 1 tracked `.md` file | none |
| `legacy-codex-skills` | a tracked `.codex/skills/` directory exists | none |
| `config-toml-budget` | `.codex/config.toml` is tracked, readable TOML, and sets `project_doc_max_bytes` to a non-negative integer (value 0 disables the whole surface) | `(project_doc_max_bytes=<value>)` |
| `undeclared-hooks-key` | see the hooks decision table's reverse direction above | `(<Event> matcher=<matcher or omitted>)` |
| `local-hooks-present` | a TRACKED `.claude/settings.local.json` carries a `hooks` key (untracked ones go to Local environment notes instead) | none |
| `json-parse-error` | a hooks projection file exists but is not valid JSON | none |
| `marker-anomaly` | any malformed/unpaired marker condition of the marker malformation rules in `source-tree-spec.md` | one line per offending line number: `(line <n>)` |
| `intent-doc-anomaly` | a hook-intent schema violation | `(entry <id>)` when the offending construct is in a recognized entry; otherwise `(line <n>)` for its 1-based first line |
| `unrepresentable-source-path` | a would-be source path violates the marker source-path grammar | one line per file |

For nested-file observations, notes must include: “may take positional
precedence over root content in subdirectory sessions”.

## Fidelity tiers (per row, `tier` column)

Use these tokens directly, without numeric aliases:

| Token | Meaning |
|---|---|
| `native` | isomorphic mechanism, mechanical transfer |
| `structural` | content fully expressible, different carrier |
| `semantic` | semantics reproduced in natural language |
| `declared-unsynced` | no counterpart |
| `-` | no source unit behind the row (adoption, orphan, vacuous) |

| Row kind | Tier |
|---|---|
| agents-md `entry` unit | `structural` |
| agents-md rule-shard unit WITHOUT non-empty `paths` frontmatter | `structural` |
| agents-md rule-shard unit WITH non-empty `paths` frontmatter | `semantic` |
| agents-md orphan block (case A4) and marked-orphan hook rows | `-` |
| skills unit rows except adoption-candidate | `native`; express behavioral degradation with lints |
| hooks rows | entry `targets.<host>.tier`, verbatim |
| adoption-candidate and no-source-unit rows | `-` |

## Skill portability lint list (closed)

Compute lints on the master only. Attach `lint:<token>` to its row in any
state without changing the state.

For lint frontmatter recognition only, remove a leading `EF BB BF` from
`SKILL.md` and emit `lint:utf8-bom`. Rendering and schema recognition retain
the BOM as content.

| Token | Condition (pure function of master bytes) | Pinned wording (used verbatim in the report's "Evidence and notes" section) |
|---|---|---|
| `missing-name` | SKILL.md has no YAML frontmatter block starting at line 1 (after the lint BOM-skip), or the `name` key is absent, or its value is empty/whitespace-only | "SKILL.md lacks a non-empty `name`; it does not satisfy the cross-host Agent Skills contract." |
| `invalid-name` | the directory name violates the 1–64 character, `[a-z0-9-]`, edge-hyphen, consecutive-hyphen, or reserved-word rules; or a present `name` value is not a string, differs from the directory, or violates the same grammar | "The skill name violates the cross-host name grammar or differs from its directory; discovery is not portable." |
| `missing-description` | SKILL.md has no YAML frontmatter block starting at line 1 (after the lint BOM-skip), or the `description` key is absent, or its value is empty/whitespace-only | "SKILL.md lacks a non-empty `description`; the skill does not satisfy the cross-host discovery contract." |
| `invalid-description` | a present `description` value is not a string, exceeds 1024 characters, or contains `<` or `>` | "The description violates the cross-host scalar, length, or no-angle-brackets constraint." |
| `implementation-specific-frontmatter` | the frontmatter contains a top-level key outside `name`, `description`, `license`, `metadata`, `allowed-tools`, and `compatibility` | "The frontmatter contains a host extension or unknown key; the skill is mechanically copied but is not behaviorally portable." |
| `codex-validator-gap` | the frontmatter contains the Agent Skills standard `compatibility` key, which the v2 Codex validator profile does not accept | "The standard `compatibility` key is outside the report/v2 Codex validator profile; verify the target Codex release before distribution." |
| `dynamic-content` | the SKILL.md body (bytes after the closing `---` line) contains any of these literal tokens: `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, a token matching `(?<!\S)\$[1-9]\b`, a line whose first non-space characters are backtick-exec (`!` immediately followed by a backtick), or a token matching `(?<!\S)@[A-Za-z0-9_./~-]+` — searched over the whole body including code fences | "The body uses Claude dynamic-content features; in Codex they reach the model as inert literal text — never executed, never substituted. Consistent but degraded on Codex." |
| `utf8-bom` | any file in the master directory begins with bytes `EF BB BF` | "The master contains file(s) beginning with a UTF-8 BOM; a BOM before line-one frontmatter breaks portable skill recognition." |

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

Keep the scanned project unchanged. Put scratch files outside it and return
the report as session output.

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
- Use registered state and tier tokens. Actions are `-`, `adopt-to-source`,
  `reproject-from-source`, `conflict`, `annex-or-keep`, `onboard`, and
  `defer-to-arbitration`.
- Observation lines use `- <token>: <repo-relative-path>` plus optional
  ` (<detail>)`, sorted byte-wise by the whole line; emit `- (none)` when
  empty.

## Expectation files and the deterministic comparison rule

An expectation contains:

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

Resolve `scan root` relative to the expectation file (`.` means its
directory) and pass `scope excludes` as the run parameter.

Comparison rule:

1. Run the sentinel with scan root and scope excludes taken from the
   expectation header.
2. Read both documents and apply normalization N (`source-tree-spec.md`) to
   each before parsing.
3. Require produced `- spec:` to equal expected `- expectation:`
   (`report/v2`).
4. Require equal `- scope excludes:` values.
5. `- onboarding:` values must be equal.
6. Require the produced Findings header row to byte-equal the expected header
   row. Parse each data row by splitting on `|`, dropping
   the empty first and last fields, and stripping exactly one leading and
   one trailing space per cell. Sort both row lists byte-wise and compare as
   sequences: equal length, including duplicates, and
   pairwise byte-equal cells.
7. Observations: compare the two line lists as sorted sequences
   (byte-per-line, equal length), after first removing from BOTH sides any
   line whose token is registered as environment-dependent (none in v2).
8. Everything else — `project`, `scan root` (produced side), `date`,
   evidence, notes, local environment notes — is free-form and never
   compared.

PASS iff steps 3–7 hold.

## Codex activation hedge

Every report whose Findings contain at least one host=codex row includes
this sentence in "Evidence and notes":

> Codex-side surfaces are verified as written bytes only; activation is
> subject to host trust and configuration and is not observable from
> repository bytes.

This report-level sentence complements — never replaces — the per-row
`awaiting-host-trust` annotation.
