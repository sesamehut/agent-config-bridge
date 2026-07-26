# Bridge sentinel report specification

Spec version: report/v4.

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
- [Diff shape](#diff-shape-observation-only-algorithm-independent)
- [Observations](#closed-observation-vocabulary)
- [Fidelity tiers](#fidelity-tiers-per-row-tier-column)
- [Skill portability lints](#skill-portability-lint-list-closed)
- [Report format](#report-document-format)
- [Expectation comparison](#expectation-files-and-the-deterministic-comparison-rule)
- [Codex runtime hedges](#codex-runtime-hedges)

## Input set

The report has two disjoint input domains:

| Domain | Inputs | Permitted use |
|---|---|---|
| **repo ownership bytes** | worktree bytes selected by `git ls-files` under the scan root, plus the exact untracked-covenant-path safety exception below | source enumeration, managed-region comparison, onboarding carrier validation, and ownership-facing findings |
| **live activation inputs** | resolved effective Codex root markers, `project_doc_fallback_filenames`, and `project_doc_max_bytes`; filesystem type/existence and, when needed, bytes for the exact root override, root `AGENTS.md`, configured same-directory fallbacks, and root-marker candidates | loadability, shadowing, root selection, and budget observations only |

Repo mode uses the repository root. Fixture mode uses the fixture path within
the outer repository's tracked set and must explicitly pin any live activation
inputs that it expects to compare. Untracked files otherwise appear only in
Local environment notes, with one ownership-domain safety exception: an
untracked covenant half at either exact anchor path participates in onboarding
validation and emits `covenant-anchor-anomaly`.

Live activation candidates are inspected even when untracked or ignored, but
only at the exact expected root child paths. Read bytes only from safe regular
files with no symlink, reparse point, special type, or resolved path escape.
If effective configuration or required carrier safety/selection cannot be
resolved, emit the registered unresolved observation and block activation;
never substitute an assumed default. A documented default is usable only
after complete configuration resolution proves the key absent. Live carrier
bytes and external/user configuration are never repo ownership bytes and
never establish source units, managed regions, onboarding ownership, or Git
baselines.

The selected index modes are part of skill-tree observation; mode `120000`,
gitlinks, and other non-regular entries are not silently read as ordinary file
content. A complete skill-tree comparison uses a `git-tree-manifest/v1`
snapshot on each side and compares relative path, entry type, raw-byte digest,
and Git mode. A filesystem-only byte comparison cannot establish Git-tree
identity.

Filter repo bytes by expectation scope excludes before applying any rule.
Patterns are scan-root-anchored gitignore/pathspec globs: `*` does not cross
`/`; `**` crosses any number of segments and matches files and directories.

## Registry growth rule (binding on all closed sets)

Closed token registries in both specifications are immutable within a
version. Any addition, removal, or semantic change requires a new spec
version. Unknown tokens are not silently accepted. Entry/rule source metadata
follows the closed v4 control-comment and `paths` schemas in
`source-tree-spec.md`.

## The states (closed set)

A row uses the `(surface, unit, host)` model in `source-tree-spec.md`.
Evaluate onboarding once before emitting rows.

| Token | Meaning | Suggested action | Regime |
|---|---|---|---|
| `in-sync` | Projection matches its source, including H-DISABLED-OK absence | `-` | onboarded; H-DISABLED-OK in either regime |
| `drift` | An onboarded carrier pairing differs or is incomplete | `reconcile` | onboarded |
| `adoption-candidate` | Content occupies a projection location without current read-side ownership proof | `annex-or-keep` | both |
| `declared-unsynced` | A hook target declares `surface: none` and tier `declared-unsynced` | `-` | both |
| `not-projected` | A source unit lacks an equivalent projection before onboarding | `onboard` | not-onboarded |
| `no-source-unit` | The surface has no source unit | `-` | both |
| `blocked` | Safety or loadability prevents a trustworthy carrier comparison | `resolve-blocker` | both |

Every `drift` row uses the neutral action `reconcile`. Current carrier bytes
cannot establish source direction, adoption, or conflict; those decisions
belong exclusively to `bridge-sync` and its Git baseline. Diff shape may
appear in evidence but never changes the state or action.

The same boundary applies to contract migration. Sentinel never serializes a
single legacy oid as a substitute for history resolution. Bridge Sync must
enumerate the complete per-unit ancestry-maximal legacy candidate set and
serialize it in sync-plan/v2 Migration candidates. Multiple incomparable
candidates remain write-blocking ambiguity; a report note or user
confirmation cannot choose one.

The unit model's `no-source-unit` rule and the decision tables are the sole
detection rules. Intent records and Git evidence may appear in notes but do
not override the resulting state or action. Print the project-level predicate
as `- onboarding: <onboarded|not-onboarded|blocked>`.

Annotations are `lint:<token>`, `behavior-degraded`,
`live-activation-unknown`, and `awaiting-host-trust`.

- Attach `awaiting-host-trust` only to `in-sync` Codex hook rows. Codex
  project hooks have a documented trust gate.
- Attach `live-activation-unknown` to a Codex skill row whenever its current
  projection carrier exists. Repository bytes do not reveal discovery or
  current-session activation.
- Attach `behavior-degraded` when any behavior-portability lint is present.

There is deliberately no state-to-write-verb mapping in this report. A
sentinel `in-sync` observation commonly becomes sync-plan `unchanged`, while
every other mapping depends on history or an explicit user decision.

## Per-surface decision tables

“Absent” means absent from scope-filtered repo bytes. The covenant anchor alone
selects the onboarding regime. When onboarding is `blocked`, emit its required
blocked agents-md row, then use the onboarded branch for carrier observations;
the write side must resolve or migrate the anchor before acting on any unit.

### Skills

Evaluate each name `n` in masters ∪ copies.

| Case | Condition | Result |
|---|---|---|
| S0 | either tree contains a non-regular/path-unsafe entry, complete Git-tree identity cannot be established (including `mode-limited` evidence), a required Git mode cannot be preserved, or the master has an identity/YAML/definite-load blocker | `blocked`/`resolve-blocker` |
| S1 | master ∃, copy ∃, identical file sets, every file raw-byte and Git mode equal | onboarded: `in-sync`; not-onboarded: master row = `not-projected`; copy row = `adoption-candidate` (unit = `.agents/skills/<n>`) |
| S2 | master ∃, copy ∃, any difference | onboarded: `drift`/`reconcile`. not-onboarded: master row = `not-projected`; copy row = `adoption-candidate` (unit = `.agents/skills/<n>`) |
| S3 | master ∃, copy ∄ | onboarded: `drift`/`reconcile`; not-onboarded: `not-projected` |
| S4 | master ∄, copy ∃ | `adoption-candidate`/`annex-or-keep` in both onboarding regimes; unit = `.agents/skills/<n>` |

S1 no longer affects onboarding; only the covenant anchor does. In an
onboarded report, `in-sync` means current carrier equality, not historical
unit-ownership proof. Use raw bytes and Git modes for all files, with no
entrypoint or sidecar exemption. Compute lints on the master and attach them
to its row in any state. A directory without `SKILL.md` is not a unit; record
a non-empty occupied target in evidence so the write-side plan can require
annex-or-keep. S4 is always conservative: the project covenant does not prove
unit ownership, and the sentinel does not inspect the historical baseline
needed to distinguish an unmanaged copy from a managed source-side deletion.
That arbitration belongs exclusively to `bridge-sync`.

### Agents-md

Evaluate each source unit `u` and parsed block `b`.

| Case | Condition | Result |
|---|---|---|
| A0 | covenant anchor is partial, malformed, modified, untracked, or version-mismatched | one `(agents-md, rules/bridge-covenant, codex)` row: `blocked`/`resolve-blocker`, tier `structural`; emit `covenant-anchor-anomaly` |
| A-SURFACE | live activation input is unresolved; effective root cannot be proven; root override shadows `AGENTS.md`; a fallback would be shadowed by creating `AGENTS.md`; effective budget is zero; or current root `AGENTS.md` exceeds the positive budget | affected unit rows are `blocked`/`resolve-blocker`; emit the exact activation observation |
| A-SOURCE | dual project entries, invalid/no-op/over-budget `paths`, active shared import, unsafe source type/path, misplaced/invalid control comment, or unrepresentable source | affected unit is `blocked`/`resolve-blocker` |
| A-MARKER | marker malformation, duplicate id, or a legacy `mode=` start prevents a trustworthy region map | affected rows are `blocked`/`resolve-blocker`; a whole-file malformation blocks every would-be write-side unit |
| A1 | block(u.id) ∃ and N(body) == N(render(u)) | `in-sync` |
| A2 | block(u.id) ∃ and bodies differ | `drift`/`reconcile` |
| A3 | block(u.id) ∄ | onboarded: `drift`/`reconcile`; not-onboarded: `not-projected` |
| A4 | block b is unattributable because its id derives from a missing source | onboarded: `drift`/`reconcile`; not-onboarded: `adoption-candidate`/`annex-or-keep`; unit = b.id; tier `-` |
| A6 | root AGENTS.md absent | every source unit hits A3's absent branch; no adoption-candidate row |
| A7 | not-onboarded, AGENTS.md ∃, zero well-formed blocks, not whitespace-only | one `adoption-candidate` row, unit `AGENTS.md`, plus one `not-projected` row per source unit |

A-SURFACE, A-SOURCE, and A-MARKER run before A1–A7. A legacy `mode=`
marker is never a semantic mode in v4. A0 replaces the ordinary covenant row
but does not suppress observations for other units. These cases do not infer
onboarding. In an onboarded project, content outside well-formed and proven
managed blocks is a protected manual zone; carrier reporting does not grant
ownership.

An exact archived-v1 pair therefore hits A0: report/v4 never interprets v1 as
a second runtime contract. Conversely, current v2/v4 carrier equality says
nothing about whether a closed v1-to-v2 ownership transition commit is
reachable. Sentinel remains history-free; reconciliation/v2 may still report
`contract-migration` and `migration-transition-uncommitted` until that
transition carries every reachable-v1 proven unit.

For duplicate ids, report the first as its authoritative id and later
occurrences as `<id>#<ordinal>` in file order, all `blocked` under A-MARKER.

### Hooks

Evaluate each entry `e` and declared host `h`. Let `s` be its
surface and `F` the host's top-level `hooks` object. “handler-equal” means all
host-applicable declared fields match and no undeclared handler keys exist,
using `source-tree-spec.md`.

| Case | Condition | Result |
|---|---|---|
| H-T4-PRESENT | s = `none` and (F contains a handler marked `[bridge:<e.id>]`, or e.command is declared and the `(e.event, e.matcher)` group of F contains a command handler whose `command` equals e.command) | onboarded: `drift`/`reconcile` (replaces the declared-unsynced row). not-onboarded: the `declared-unsynced` row stands; the occupied group is reported as `undeclared-hooks-key` |
| H-T4 | s = `none` and H-T4-PRESENT does not fire | `declared-unsynced` (both regimes) |
| H-DISABLED-PRESENT | s ≠ `none`; e.enabled = false; a command handler exists in any owned group for e on F, or a `[bridge:<e.id>]`-marked handler exists in F | `drift`/`reconcile` |
| H-DISABLED-OK | s ≠ `none`; e.enabled = false; no command handler exists in any owned group for e on F and no handler marked `[bridge:<e.id>]` exists in F | `in-sync` (vacuously consistent; reachable in either regime) |
| H-NOFILE | F absent, or not valid JSON (emit `json-parse-error` observation), or lacks the hooks object | onboarded: `drift`/`reconcile`; not-onboarded: `not-projected` |
| H-MISSING | owned group for (e.event, e.matcher) absent, or present with zero command handlers | onboarded: `drift`/`reconcile`; not-onboarded: `not-projected` |
| H-OK | e.enabled = true; the owned group contains exactly one command handler; it is handler-equal to e | `in-sync` |
| H-EXTRA-KEYS | unique handler, declared fields all equal, handler has undeclared keys | `drift`/`reconcile` |
| H-FIELD-ABSENT | unique handler, a declared field absent from the handler, no undeclared keys, all present fields equal | `drift`/`reconcile` |
| H-FIELD-DIFF | unique handler, any declared field value differs (or both undeclared keys and missing/differing fields) | `drift`/`reconcile` |
| H-MULTI | more than one command handler in the owned group | `drift`/`reconcile` |
| H-MARKED-ORPHAN | a handler in F carries `statusMessage` beginning `[bridge:<id>]` where `<id>` has no schema-valid entry in the intent document | onboarded: `drift`/`reconcile`; not-onboarded: `adoption-candidate`/`annex-or-keep`; unit = `hooks/<id>`, host = F's host, tier `-` |

For each valid entry/host, apply the first matching case in table order.
Evaluate H-MARKED-ORPHAN afterward over marked handlers without valid entries.
Handlers in owned groups use the table. A marked handler with a valid id uses
that entry's cases; one without a valid entry uses H-MARKED-ORPHAN. A group
that is neither owned nor marked emits one `undeclared-hooks-key` per
`(file, event, matcher)` and no row. Duplicate ownership declarations make
all involved entries invalid, emitting `intent-doc-anomaly` and no rows.
Hook prose does not affect consistency.

## Diff shape (observation only, algorithm-independent)

For source lines A and projection lines B after surface preprocessing:

- **additions-only** := A is a proper subsequence of B (every line of A
  occurs in B in order; B ≠ A).
- **deletions-only** := B is a proper subsequence of A.
- **both** := neither.

For skills, a copy-only file contributes additions, a master-only file
contributes deletions, and a changed pair contributes its line shape. The
unit is additions-only or deletions-only only when every contribution has
that shape; otherwise it is both. The subsequence test, not diff hunk output,
is normative. A within-line substitution is `both`. Shape is evidence about
the current carriers only and never selects a write direction.

## Closed observation vocabulary

Emit each observation as `- <token>: <repo-relative-path>` plus the specified
detail. Provenance is binding:

| Provenance | Observation tokens |
|---|---|
| repo ownership bytes (plus the exact covenant exception where specified) | `active-shared-import`, `dual-project-entry`, `invalid-rule-paths`, `legacy-managed-mode`, every `nested-*`, `legacy-commands-dir`, `legacy-codex-skills`, `undeclared-hooks-key`, `local-hooks-present`, `json-parse-error`, `marker-anomaly`, `covenant-anchor-anomaly`, `intent-doc-anomaly`, `unsafe-skill-tree`, `unrepresentable-source-path` |
| live activation inputs only | `surface-shadowed`, `codex-activation-unresolved`, `codex-root-unresolved`, `fallback-shadow`, `codex-effective-budget`, `agents-md-budget-disabled`, `agents-md-budget-exceeded`, `agents-md-size` |
| host/filesystem capability evidence | `mode-limited` |

No token in the second or third row may contribute ownership or baseline
evidence. In fixture mode those inputs must be pinned explicitly; otherwise
their observation lines are environment-dependent.

| Token | Emitted when | Detail |
|---|---|---|
| `surface-shadowed` | a safe regular root `AGENTS.override.md` exists, whether tracked, untracked, or ignored | none |
| `codex-activation-unresolved` | effective Codex configuration or an exact activation carrier cannot be resolved safely | `(<reason>)` |
| `codex-root-unresolved` | effective root-marker evidence does not prove the scan root as Codex project root | `(<reason>)` |
| `fallback-shadow` | root `AGENTS.md` is absent and a safe regular configured same-directory fallback file is currently selected, whether tracked, untracked, or ignored | `(<selected fallback path>)` |
| `codex-effective-budget` | configuration resolution proves the effective non-negative project-document budget | `(project_doc_max_bytes=<value>; source=<resolved|documented-default>)` |
| `agents-md-budget-disabled` | effective `project_doc_max_bytes` is zero | none |
| `agents-md-budget-exceeded` | a safe regular current root `AGENTS.md` is larger than the resolved effective positive budget | `(<n> bytes of <B>)` |
| `agents-md-size` | a safe regular root `AGENTS.md` size is at least floor(7 × B / 8), where B is the resolved effective positive project-document budget; do not emit when B = 0 | `(<n> bytes of <B>)` with n the exact byte size |
| `active-shared-import` | after control/claude-only subtraction and code-span/fence exclusion, shared source matches `(?<!\S)@[A-Za-z0-9_./~-]+` | one line per source path and match: `(<token>)` |
| `dual-project-entry` | both `CLAUDE.md` and `.claude/CLAUDE.md` exist at the scan root | none |
| `invalid-rule-paths` | present `paths` violates v4 schema/pattern/no-op/duplicate/brace-budget rules | one line per rule shard: `(<reason>)` |
| `legacy-managed-mode` | a marker-like start line contains the removed v3 `mode=` attribute | one line per offending line number |
| `nested-claude-md` | a tracked `CLAUDE.md` exists at any non-root directory | one line per file |
| `nested-agents-md` | a tracked `AGENTS.md` or `AGENTS.override.md` exists at any non-root directory | one line per file |
| `nested-claude-skills` | a tracked `.claude/skills/` directory exists at any non-root directory | one line per directory |
| `nested-agents-skills` | a tracked `.agents/skills/` directory exists at any non-root directory | one line per directory |
| `legacy-commands-dir` | `.claude/commands/` contains ≥ 1 tracked `.md` file | none |
| `legacy-codex-skills` | a tracked `.codex/skills/` directory exists | none |
| `undeclared-hooks-key` | see the hooks decision table's reverse direction above | `(<Event> matcher=<matcher or omitted>)` |
| `local-hooks-present` | a TRACKED `.claude/settings.local.json` carries a `hooks` key (untracked ones go to Local environment notes instead) | none |
| `json-parse-error` | a hooks projection file exists but is not valid JSON | none |
| `marker-anomaly` | any malformed/unpaired marker condition of the marker malformation rules in `source-tree-spec.md` | one line per offending line number: `(line <n>)` |
| `covenant-anchor-anomaly` | exactly one covenant half exists, or a half is untracked, malformed, non-template, or version-mismatched | one line per affected path, with `(partial)`, `(untracked)`, `(malformed)`, `(modified)`, or `(version-mismatch)` |
| `intent-doc-anomaly` | a hook-intent schema violation | `(entry <id>)` when the offending construct is in a recognized entry; otherwise `(line <n>)` for its 1-based first line |
| `mode-limited` | a required executable mode cannot be proved or realized for a proposed skill-tree operation | one line per entry with `(explicit-executable-unrealizable)`, `(worktree-mode-unobservable)`, or `(target-mode-unpreservable)` |
| `unsafe-skill-tree` | a skill tree contains a Git symlink/gitlink, filesystem symlink/reparse point, special file, case-fold collision, or path escape | one line per entry with its kind |
| `unrepresentable-source-path` | a would-be source path violates the marker source-path grammar | one line per file |

Closed `codex-activation-unresolved` reasons are `config-unresolved`,
`override-carrier-unsafe`, `agents-carrier-unsafe`,
`fallback-carrier-unsafe`, `fallback-selection-unknown`, and
`budget-unknown`. Closed `codex-root-unresolved` reasons are
`effective-root-unknown`, `empty-markers`, and `root-marker-excluded`.
Either unresolved token blocks affected agents-md rows under A-SURFACE.
Closed `invalid-rule-paths`
reasons are `schema`, `empty`, `unsafe`, `invalid-bracket`,
`no-op-universal`, `duplicate`, `expansion-count`, `expansion-bytes`, and
`expansion-unproved`.

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
| agents-md rule-shard unit without frontmatter | `structural` |
| agents-md rule-shard unit with valid scoped `paths` frontmatter | `semantic` |
| agents-md orphan block (case A4) and marked-orphan hook rows | `-` |
| skills unit rows except adoption-candidate | `native`; express behavioral degradation with lints |
| hooks rows | entry `targets.<host>.tier`, verbatim |
| adoption-candidate and no-source-unit rows | `-` |

## Skill portability lint list (closed)

Compute lints on the master only. Attach `lint:<token>` to its row in any
state without changing the carrier-comparison result, except that the
blocker mapping below selects S0.

For lint analysis only, remove a leading `EF BB BF` from `SKILL.md` so the
remaining issues can be reported, and also emit `lint:utf8-bom`. Actual host
recognition retains the BOM.

| Token | Condition (pure function of master bytes) | Pinned wording (used verbatim in the report's "Evidence and notes" section) |
|---|---|---|
| `invalid-frontmatter` | after the lint-only BOM skip, `SKILL.md` does not open and close YAML frontmatter on full `---` lines, YAML parsing fails, or the result is not a map | "SKILL.md frontmatter is absent or invalid YAML; the managed source is not format-loadable." |
| `missing-name` | valid frontmatter lacks `name`, or its value is empty/whitespace-only | "SKILL.md lacks a non-empty `name`; it does not satisfy the cross-host Agent Skills contract." |
| `invalid-name` | the directory name violates the 1–64 character, `[a-z0-9-]`, edge-hyphen, or consecutive-hyphen rules; or a present `name` value is not a string, differs from the directory, or violates the same grammar | "The skill name violates the cross-host name grammar or differs from its directory; discovery is not portable." |
| `missing-description` | valid frontmatter lacks `description`, or its value is empty/whitespace-only | "SKILL.md lacks a non-empty `description`; the skill does not satisfy the cross-host discovery contract." |
| `invalid-description` | a present `description` value is not a string or exceeds 1024 characters | "The description violates the Agent Skills scalar or length contract." |
| `implementation-specific-frontmatter` | valid frontmatter contains a top-level key outside Agent Skills `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools` | "The frontmatter contains a host extension or unknown key; the skill is copied unchanged but behavior is not portable." |
| `allowed-tools-behavior` | valid frontmatter contains `allowed-tools` | "The experimental `allowed-tools` key has no cross-host permission-equivalence guarantee; the skill is copied unchanged with degraded behavior portability." |
| `codex-validator-rejection` | the pinned Codex validator profile would reject the frontmatter: `compatibility` is present, a string `description` contains `<` or `>`, or any top-level key is outside `name`, `description`, `license`, `allowed-tools`, and `metadata` | "The skill is outside the pinned Codex authoring-validator profile; this validator result is independent of format validity and runtime loading." |
| `dynamic-content` | the body contains a Claude-rendered token or command form: literal `$ARGUMENTS`; `$ARGUMENTS[N]` for one or more decimal digits; `$N` for one or more decimal digits including zero; `$name` for a valid name declared by the frontmatter `arguments` list; `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`, or `${CLAUDE_PROJECT_DIR}`; an inline `` !`command` `` preceded by start-of-body or whitespace; or a fenced command block whose opening fence has `!` immediately after the fence run. Search the complete body, including ordinary code fences. `@path` is not a dynamic-content token. | "The body uses Claude-rendered dynamic content; Codex receives inert source text instead of Claude's substitution or command output. The bytes are consistent but behavior is degraded." |
| `utf8-bom` | any file in the master directory begins with bytes `EF BB BF` | "The master contains file(s) beginning with a UTF-8 BOM; a BOM before line-one frontmatter breaks portable skill recognition." |

`invalid-frontmatter`, `missing-name`, `invalid-name`,
`missing-description`, and `invalid-description` are S0 blockers. A BOM in
`SKILL.md` is also an S0 blocker; a BOM in a supporting file is a lint only.
`implementation-specific-frontmatter`, `allowed-tools-behavior`, and
`dynamic-content` add `behavior-degraded`. `codex-validator-rejection`
describes only the pinned validator profile and is neither a format nor a
runtime blocker by itself.

## Report document format

### Document skeleton

```markdown
# Bridge Sentinel Report

- project: <directory name of the scan root>
- scan root: <path as invoked>
- scope excludes: <comma+space-separated globs, or (none)>
- date: <YYYY-MM-DD>
- spec: report/v4
- scan surfaces: agents-md, hooks, skills
- onboarding: <onboarded|not-onboarded|blocked>

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
  Tokens: `awaiting-host-trust`, `behavior-degraded`,
  `live-activation-unknown`, and `lint:<token>`. Lint wording sentences
  (pinned in the lint list above) go in "Evidence and notes", never in the
  cell.
- Use registered state and tier tokens. Actions are `-`, `reconcile`,
  `annex-or-keep`, `onboard`, and `resolve-blocker`.
- Observation lines use `- <token>: <repo-relative-path>` plus optional
  ` (<detail>)`, sorted byte-wise by the whole line; emit `- (none)` when
  empty.

## Expectation files and the deterministic comparison rule

An expectation contains:

```markdown
- expectation: report/v4
- scan root: <path relative to the directory containing this file>
- scope excludes: <comma+space-separated globs, or (none)>
- activation profile: <path relative to the directory containing this file, or environment-dependent>
- onboarding: <onboarded|not-onboarded|blocked>

## Findings

<header row, separator row, and expected rows>

## Observations

<expected observation lines or "- (none)">
```

Resolve `scan root` relative to the expectation file (`.` means its
directory) and pass `scope excludes` as the run parameter. A pinned activation
profile is UTF-8 JSON with this closed shape:

```json
{
  "version": "activation-fixture/v1",
  "root_markers": [".git"],
  "fallback_filenames": ["AGENTS.fallback.md"],
  "project_doc_max_bytes": 32768,
  "budget_source": "resolved"
}
```

The three values are respectively a string array, a string array, and a
non-negative integer; use JSON `null` for an intentionally unresolved value.
`budget_source` is `resolved` or `documented-default`. No other key is
allowed. Carrier existence/type/bytes are still read from the exact paths
under the fixture scan root; profile values never become ownership bytes.

Comparison rule:

1. Run the sentinel with scan root and scope excludes taken from the
   expectation header.
2. Read both documents and apply normalization N (`source-tree-spec.md`) to
   each before parsing.
3. Require produced `- spec:` to equal expected `- expectation:`
   (`report/v4`).
4. Require equal `- scope excludes:` values.
5. `- onboarding:` values must be equal.
6. Require the produced Findings header row to byte-equal the expected header
   row. Parse each data row by splitting on `|`, dropping
   the empty first and last fields, and stripping exactly one leading and
   one trailing space per cell. Sort both row lists byte-wise and compare as
   sequences: equal length, including duplicates, and
   pairwise byte-equal cells.
7. Observations: compare the two line lists as sorted sequences
   (byte-per-line, equal length). When `activation profile` names a valid
   profile, compare live-activation lines normally; host/filesystem capability
   lines remain environment-dependent. For `environment-dependent`, first
   remove from BOTH sides every line whose provenance is live activation or
   host/filesystem capability under the table above.
8. Everything else — `project`, `scan root` (produced side), `date`,
   evidence, notes, local environment notes — is free-form and never
   compared.

PASS iff steps 3–7 hold.

## Codex runtime hedges

Every report whose Findings contain a Codex skill row with a current
projection carrier includes:

> Codex skill bytes are verified only as a repository carrier. Live discovery
> and activation are not inferable from those bytes; test in a fresh session,
> and restart the host when the current session may have cached its skill
> inventory.

Every report containing a Codex hook row includes:

> Codex hook bytes are verified only as a repository carrier. Activation is
> subject to project and per-hook trust and is not observable from repository
> bytes.

The sentences complement, and never replace, the corresponding
`live-activation-unknown` skill annotation or `awaiting-host-trust` hook
annotation.
