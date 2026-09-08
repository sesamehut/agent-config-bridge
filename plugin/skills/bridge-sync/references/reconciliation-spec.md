# Bridge reconciliation specification

Spec version: reconciliation/v3.

This file defines the write-side contract for project skills, entry/rule
managed blocks, and hook units on both native hook carriers. The read-only
carrier vocabulary lives in
[`../../bridge-sentinel/references/report-spec.md`](../../bridge-sentinel/references/report-spec.md);
the source unit and compatibility rules live in
[`../../bridge-sentinel/references/source-tree-spec.md`](../../bridge-sentinel/references/source-tree-spec.md).
Plan serialization lives in [`sync-plan-spec.md`](sync-plan-spec.md).

## Contents

- [Authority and scope](#authority-and-scope)
- [Versioned onboarding covenant](#versioned-onboarding-covenant)
- [Current snapshot](#current-snapshot)
- [Entry/rule snapshot](#entryrule-snapshot)
- [Hooks snapshot](#hooks-snapshot)
- [Entry/rule baseline value](#entryrule-baseline-value)
- [Hook baseline value](#hook-baseline-value)
- [Safety gates](#safety-gates)
- [Managed ownership evidence](#managed-ownership-evidence)
- [Baseline selection](#baseline-selection)
- [Reconciliation table](#reconciliation-table)
- [Entry/rule reconciliation](#entryrule-reconciliation)
- [Hooks reconciliation](#hooks-reconciliation)
- [Hook handler reverse adoption](#hook-handler-reverse-adoption)
- [Intent records](#intent-records)
- [Three onboarding starts](#three-onboarding-starts)
- [Delete and rename](#delete-and-rename)
- [Planning and confirmation](#planning-and-confirmation)
- [Writes, validation, and rollback](#writes-validation-and-rollback)
- [Hooks carrier writes](#hooks-carrier-writes)
- [Host trust consequences](#host-trust-consequences)
- [Guarded and strict call discipline](#guarded-and-strict-call-discipline)

## Authority and scope

Bridge writes only:

- the immutable covenant source at `.claude/rules/bridge-covenant.md`;
- Bridge-owned managed blocks in root `AGENTS.md`, preserving every other byte;
- exactly one Claude project entry (`CLAUDE.md` or
  `.claude/CLAUDE.md`);
- rule shards under `.claude/rules/**/*.md`, excluding the covenant and the
  hook intent document;
- immediate skill units rooted at `.claude/skills/<name>/` and
  `.agents/skills/<name>/`;
- the hook intent document `.claude/rules/hooks.md`; and
- the owned `hooks` spans of the two native hook carriers,
  `.claude/settings.json` for Claude and `.codex/hooks.json` for Codex.

`.claude/rules/hooks.md` is a hook source unit, never a `rules/<id>` unit;
the two id namespaces are disjoint. A hooks carrier is written only inside its
owned `(event, effective matcher)` group spans. Every other byte of those
files, including unrelated top-level keys and the Codex top-level
`description`, is unowned and preserved byte-for-byte.

Bridge does not derive `agents/openai.yaml`, write `skills.config`, modify
Codex root-marker/budget/fallback configuration, modify `AGENTS.override.md`,
write inline `[hooks]` into `.codex/config.toml`, or write
`.claude/settings.local.json`, which stays a read-only observation. It
introduces no CLI, package, plugin manifest, bundled JavaScript, or
distribution payload. `templates/hook-intents.example.md` is an example
document: nothing installs it and no write reads it as an asset.

Hooks committed to a repository run for everyone who clones it: Bridge
classification is review metadata, not a sandbox. Every hook carrier write
therefore carries an explicit acknowledged disclosure, and a `gate` or
`side-effect` entry is never projected without a dated `enabled-by` record
that lives in the source document and is inherited by every clone.

The source remains canonical after ownership is established, but an edit made
on a proven managed projection is a valid input to adoption. Intent records
are evidence, never ownership by themselves.

## Versioned onboarding covenant

The single current contract tuple is:

```text
covenant/v3
source-tree/v5
report/v5
reconciliation/v3
sync-plan/v3
```

Bootstrap reads the two exact assets under `templates/covenant/`. It creates
source half and inserts the exact managed block into root `AGENTS.md`.
Existing manual-zone bytes before and after the insertion remain unchanged.
Capture their pre-write bytes and verify them after insertion. Bridge never
stages; a newly created half is not tracked until the user records it in the
index. The verified/applied result remains bound to the operation's starting
empty snapshot: it keeps `bootstrap-required`, `no-baseline`, `create`, and
`applied`, and does not add `covenant-anchor-anomaly` merely because its two
successful creates are still untracked. It still emits
`untracked-files-included` for both paths. After that operation's journal is
closed, a later invocation is an independent fresh scan. If both exact
carriers are still untracked, that scan is `blocked` and selects only the
zero-write `resolve-blocker` covenant decision described below.

The project is onboarded only when both halves are tracked, schema-valid,
exact-template valid, and version-equal. Apply covenant gates in this order:
carrier path/type safety and trackability, pair structure/template coherence,
then tuple version, then reachable-history state. A later tuple label never
overrides an earlier safety or trackability blocker. Classify the pair with
this table before ordinary unit reconciliation; contract migration additionally
enumerates the complete legacy-owned set below:

| Current pair | Reachable covenant evidence | Plan state | Allowed action | Closure boundary |
|---|---|---|---|---|
| both halves absent | no prior valid covenant, or a completed explicit offboard is proven | `no-baseline` | `create` | source half + `AGENTS.md` block + preserved manual zone |
| both halves absent | prior valid current tuple and no completed explicit offboard | `offboarding` | explicit `restore` or `offboard` | both halves as one closure + preserved manual zone |
| both halves absent | a prior exact archived tuple and no completed explicit offboard | `contract-migration` | explicit `migrate` or `offboard` | historical pair decision + closed legacy-owned set + current pair + preserved manual zone |
| either occupied half has an unsafe path/type, exactly one half exists, or an untracked shape is not the exact both-untracked current pair below | any, regardless of declared tuple | `blocked` | `repair` with `user-decision` direction | safe, coherent pair + preserved manual zone; no migration in this closure |
| both halves exist, are safe and exact for the current tuple, and both are untracked | any | `blocked` | zero-write `resolve-blocker` with `user-decision` direction | user records both exact carriers as tracked; Bridge does not stage or write |
| both halves are tracked but either is malformed/modified, or their tuple declarations disagree | any | `blocked` | `repair` with `user-decision` direction | coherent exact pair + preserved manual zone |
| both halves are tracked, mutually coherent, and exact for an archived tuple | any | `contract-migration` | `migrate` | old exact pair + closed legacy-owned set to current transition |
| both halves are tracked and exact for the current tuple | reachable archived-tuple ownership exists but no qualifying closed archived-to-current transition commit is reachable | `contract-migration` | finish `migrate`; Bridge byte writes may already be unnecessary | closed legacy-owned set + current transition commit |
| both halves are tracked and exact for the current tuple | no legacy ownership requires carry-forward, or a qualifying closed archived-to-current transition commit is reachable | `unchanged` | `unchanged` | no write |

Serialize the plan header as `onboarded` only for the last row,
`bootstrap-required` for the first row, and `blocked` for every repair,
untracked-carrier resolution, migration, restore, or offboarding decision
until its required tracked postcondition is actually observed. The
same-operation applied bootstrap result is the temporal exception above: it
reports completion against the starting empty snapshot without pretending the
fresh current snapshot is onboarded.

`repair` first establishes a safe, tracked, mutually coherent exact pair
without interpreting its old tuple as migration permission;
`restore` reverses an unconfirmed disappearance whose reachable history
proves the current tuple; `migrate` crosses a tuple-version barrier; and
`offboard` ends managed ownership. Each operates on the complete pair, never
one half. Repair, restore, migration, and offboarding require a complete plan
and explicit confirmation. An older tuple is never an ordinary unit baseline.
The exact archived pairs under `templates/covenant/v1/` and
`templates/covenant/v2/` are read only to identify one explicit whole-pair
migration to the current tuple. The archived-pair recognizer is a closed
two-member set `{v1, v2}`; each archived version is a single hop to the
current tuple, with no chaining and no dual-read mode. Normal runtime
supports no archived interpretation and no dual-read compatibility.

The legacy-owned set for an archived-to-current transition contains exactly
the unit classes `entry`, `rules/<id>`, and `skills/<name>`. Hook units never
appear in Migration decisions or Migration candidates, because
`reconciliation/v2` forbade every hook write, so no reachable archived-era
commit can prove a hook baseline. A `hooks/*` unit claiming a reachable
v2-era baseline is evidence of an out-of-contract write and is `blocked` /
`resolve-blocker`, never carried. Hook units arrive afterwards through
ordinary `no-baseline` / `create` reconciliation, so the migration closure,
the ancestry-maximal candidate derivation, the independent Migration
candidates table, and the `migration-transition-uncommitted` external wait all
run unchanged.

For migration, derive the complete legacy-owned set `L` from all
ancestry-maximal managed-unit candidates provable in the reachable
archived-tuple DAG. Retain the complete maximal candidate set per unit.
Serialize every full oid in the independent sync-plan/v3 Migration candidates
table; never choose one incomparable candidate as a representative. A unit with one candidate repeats
that oid as `legacy baseline`. A unit with multiple incomparable candidates
uses `legacy baseline` `-`, relation `ambiguous`, disposition `block`, and
decision `pending`.

When any payload unit is ambiguous, keep the complete migration closure
selected and blocked. Every Units member uses baseline `-`,
`contract-migration` / `resolve-blocker`, `user-decision`, authorization
`not-applicable`, and outcome `blocked`. The ambiguous payload row carries
only `decision-required`; the covenant and each unambiguously carried payload
row carry `migration-transition-required`. Unique legacy oids remain in the
migration evidence tables rather than becoming current baselines across an
open version barrier.

`L` contains legacy managed payload units only. The covenant pair is
transition evidence and an indivisible member of `closure/migration`, but
`onboarding/covenant` never appears in Migration decisions or Migration
candidates. Enumerate candidates independently for every payload unit; never
serialize one covenant commit as a scalar baseline for the whole migration.

Every safe unambiguous unit in `L` whose current carriers already satisfy its
current-contract relation is carried automatically. Any missing, unsafe, ambiguous, or
non-converged member blocks the whole migration until the plan records an
allowed explicit decision; ambiguity itself cannot be hidden by
`repair-and-carry` or release based on an arbitrary candidate. A release must
leave durable, unambiguous Git transition evidence; destructive bytes need
separate explicit confirmation. No member may silently disappear because the
covenant changed.

A qualifying migration commit has a reachable pre-transition archived covenant
state, the exact current covenant pair in its tree, and the complete carried
set in a current-contract converged state; its transition evidence also identifies every
explicit release. That commit is an ownership-establishing transition for
each carried unit, so its source/projection value becomes a current-tuple
baseline candidate even when the unit bytes themselves did not change.
Preparing the bytes in the worktree is not enough. Because Bridge does not
commit, migration remains `contract-migration` with
`migration-transition-uncommitted` until the user records that closed
transition and it is reachable from `HEAD`.

In the post-write migration result, carried and repaired payload rows retain
their unique legacy baseline plus `migration-transition-required` until that
commit is reachable. A released payload row has Units baseline `-` and no
migration transition annotation; its legacy oid remains only as release
evidence.

For example, if an untracked source half and its tracked companion both
declare an otherwise exact older tuple, the result is `blocked`/`repair`, not
`contract-migration`/`migrate`. Bridge may plan byte repair but cannot stage
the half; after the user makes the coherent pair tracked, a fresh scan may
select the separate `migrate` closure.

When both exact current halves are untracked after a successful empty
bootstrap, the independent fresh scan instead serializes one selected
`onboarding/covenant` row with closure
`closure/decision/onboarding/covenant`, baseline and annotations `-`, state
`blocked`, action `resolve-blocker`, direction `user-decision`,
authorization `not-applicable`, and outcome `blocked`. It emits one
`covenant-anchor-anomaly` with reason `(untracked)` and one
`untracked-files-included` line for each carrier, and emits no capability or
write row.

## Current snapshot

For every immediate name in either skill root, build a current snapshot from:

1. tracked worktree paths selected by `git ls-files --stage`;
2. relevant non-ignored untracked files selected by
   `git ls-files --others --exclude-standard`; and
3. tracked deletions visible in scoped `git status`.

Apply excludes before reading bytes. A relevant non-ignored untracked regular
file participates in the pre-write plan and current comparison and emits
`untracked-files-included`. It remains untracked: Bridge never calls
`git add`, stages, commits, or changes ignore rules. Its manifest mode is
explicitly prospective; it does not pretend that an untracked path is already
a Git-tree entry.

Emission is unconditional once the path is relevant: retain one warning for
each such file when its unit is blocked, deferred, unchanged, not selected, or
selected, and retain it in a later result while the file remains relevant and
untracked. Selection and authorization never suppress untracked evidence.

Ignored files are not part of the canonical Git tree, never participate in a
baseline, and are never copied. List their paths without content under
`ignored-files-excluded`. If an ignored file is required for the skill, stop
and ask the user to make it an intentional non-ignored source input.

An empty directory contributes nothing. A non-empty target directory without
`SKILL.md`, an apparent manual duplicate, or any other unknown occupancy is
unmanaged and must reach `annex-or-keep`; it is never overwritten.

### Entry/rule snapshot

Enumerate `entry` only when exactly one supported Claude entry exists. Both
entry locations present is `dual-project-entry` and blocks the unit; neither
path has precedence. Enumerate every safe rule shard from source-tree/v5,
excluding the covenant and the hook intent document. For each unit capture:

- raw current source bytes and exact path/type/tracking state;
- parsed v5 control comments and validated ordered `paths`;
- deterministic `render(source)` plus its source-origin/protected-span map;
- the paired managed block body and exact marker byte spans in root
  `AGENTS.md`; and
- every byte span outside selected managed blocks as protected manual data.

A relevant non-ignored untracked entry or rule source follows the same
current-snapshot rule as a skill path: include it in the plan and emit
`untracked-files-included`. It remains ineligible as ownership or baseline
evidence and Bridge never stages it.

Any active shared import, invalid/no-op/duplicate/over-budget `paths`,
unknown/misplaced control comment, unsafe entry type, duplicate block id,
legacy `mode=`, or malformed marker blocks the affected unit. A malformation
that prevents a trustworthy whole-file region map blocks every
`AGENTS.md` write.

Before proposing apply, prove Codex target eligibility: root override absent;
effective root markers select this repository root; creating `AGENTS.md` does
not shadow an active fallback; effective budget is positive; and the exact
planned full-file UTF-8 byte count fits. Bridge reports and stops instead of
editing config/override/fallback. At seven eighths of the positive budget,
require explicit warning acknowledgement.

These are **live activation inputs**, disjoint from repo ownership bytes.
Resolve the effective root-marker, `project_doc_fallback_filenames`, and
`project_doc_max_bytes` values, and inspect the exact root override,
`AGENTS.md`, and configured same-directory fallback candidates even when they
are untracked or ignored. Read a carrier only when it is a safe regular file
at the expected root child path. If configuration resolution, carrier type,
fallback selection, or budget remains unknown, emit
`codex-activation-unresolved` or `codex-root-unresolved` and block apply.
Use a documented default only after complete resolution proves the key
absent. These bytes and values never grant ownership or enter a baseline.

### Hooks snapshot

Enumerate hook units only from `.claude/rules/hooks.md`. For each schema-valid
entry capture:

- the entry's exact byte span, its normalized machine-field model, and its
  five prose-bullet values verbatim;
- the file-level `bridge:hooks-shared-execution` acknowledgement comment with
  its exact span, or its proven absence;
- per host, the owned `(event, effective-matcher(h))` group's exact
  `[start, end)` span in that host's carrier, its normalized handler model or
  proven absence, and its passthrough, semantics-changing, and unknown keys;
- the complete preimage of both carriers plus their parse result,
  duplicate-key result, closed-shape result, and inferred style; and
- the shallow `.codex/config.toml` inline-hooks scan result.

Also record, claiming no ownership, every group that no valid entry owns,
every handler carrying a `[bridge:<id>]` marker without a schema-valid entry,
and every foreign handler inside an owned group. These are unmanaged
occupancy that must reach `annex-or-keep`; Bridge never deletes or rewrites
them. An entry that violates the `source-tree/v5` hook schema emits one
`intent-doc-anomaly` per violation and no unit row.
`.claude/settings.local.json` is read only for the informational
`local-hooks-present` observation and is never written.

The `.codex/config.toml` detector is a shallow byte scan, not a TOML parse. It
matches both a `[hooks` table header and a top-level `hooks =` pointer key
outside a TOML string, so it catches the legacy pointer form as well. If the
file exists and the scan cannot prove absence of a hooks section, block
`closure/hooks/codex` and emit `codex-inline-hooks-conflict`. The two forms
merge within one Codex layer and register as two distinct positional trust
keys that share one normalized hash, so the hook runs twice; silently
doubling a user's hook execution is exactly the harm the non-overwrite
discipline exists to prevent.

Codex project trust and the effective Codex hooks feature flag are live
activation inputs, disjoint from repository ownership bytes and resolved
exactly like the other Codex activation inputs. They never grant ownership and
never enter a baseline. Emit `codex-project-untrusted` only when at least one
hook row targets `.codex/hooks.json` and project trust resolves untrusted.

### Entry/rule baseline value

An entry/rule candidate commit carries a pair `(B_s, B_p)`: raw source bytes
`B_s` and the paired historical block `B_p`, where
`N(B_p.body) == render(B_s)`. The values are not byte-identical carriers.
Candidate ownership additionally requires the current contract tuple, a
well-formed unique marker with the correct id/source, and a prior confirmed
projection/adoption/annex transition.

Apply the same HEAD-reachable, ancestry-maximal DAG rule used for skills.
Exactly one maximal candidate is the unit baseline; zero is `no-baseline`;
incomparable maxima are blocked. Intent comments support evidence but never
grant ownership.

### Hook baseline value

For `hooks/<entry-id>/source` the baseline value `B_s` is the entry's
normalized machine-field model plus its five prose-bullet values. For
`hooks/<entry-id>/<host>` the value is the pair `(B_s, B_p)`, where `B_p` is
the normalized handler model of that host's owned group at the candidate
commit and absence is itself a value. A candidate additionally requires
`B_p == project(B_s, host)`.

Selection uses the unchanged HEAD-reachable ancestry-maximal DAG rule:
exactly one maximal candidate is the baseline, zero is `no-baseline`, and
incomparable maxima are `blocked` with `ambiguous-baseline`. Candidate
ownership additionally requires the current contract tuple and a prior
confirmed create, projection, adoption, or annexation transition.

Because both values are field-normalized, reformatting the intent document or
either carrier never invalidates a baseline. Because no archived-tuple commit
can prove a hook baseline, a hook unit's earliest possible candidate is a
post-migration commit.

## Safety gates

Resolve the repository root and every unit root before planning a write.
Block a unit on any of these conditions:

- its lexical or resolved path escapes the expected immediate skill root;
- a Git symlink (`120000`), gitlink, filesystem symlink, junction/reparse
  point, special file, or case-fold collision occurs anywhere in the unit;
- `SKILL.md` fails an identity, YAML, BOM, or known host-loadability gate from
  `report/v5`;
- content appears to contain secrets, credentials, private keys, or generated
  payloads that should not be copied;
- a required executable mode cannot be read and preserved reliably.

The unit-wide case-fold domain includes current selected paths and tracked
deletions. Treat the same exact path appearing in both sets as one name, but
block distinct case-fold-equal names, including deleted tracked `Foo` plus
current or untracked `foo`.

Build every current and historical snapshot with
`git-tree-manifest/v1`. Compare relative path, entry type, raw-byte digest,
and mode; a filesystem-only byte comparison is insufficient. For tracked
worktree entries, retain `HEAD` and index modes and, on POSIX with
`core.filemode=true`, probe executable bits for unstaged mode-only changes.
When that probe is unavailable, the index remains evidence for the mode of an
already tracked entry, but it cannot prove a worktree-only mode claim.

A relevant untracked regular file has no index mode. A reliable POSIX probe
establishes its prospective `100644` or `100755`. When that probe is
unavailable on Windows, with `core.filemode=false`, or for another host
reason, use the platform-provable prospective default `100644`. This ordinary
case remains safe for create, source additions, and annexation confirmed at
`100644`; do not block the whole unit merely because the file is untracked.

Mode preservation becomes directional only after an action is selected. For
source-to-projection or projection-to-source, compare the authority mode with
what the target can already prove or reliably set. Emit `mode-limited` only
when the operation requires a different mode that the target cannot realize,
especially tracked/history `100755` or explicit executable intent against a
target limited to prospective `100644`. A pending `annex-or-keep` observation
and confirmed `keep` are zero-write choices and do not invoke a target-mode
requirement. Annex may explicitly adopt `100644`; if the user requires
executable behavior, stop for `mode-limited`. Never call a content-only tree
equivalent or silently reinterpret required `100755` as `100644`.

Claude-only frontmatter, `allowed-tools`, and dynamic content are not blockers
when both hosts remain loadable. Copy them byte-for-byte and attach
`behavior-degraded`. A current Codex validator rejection is the independent
warning `validator-profile-mismatch`; it does not silently rewrite a
format-valid source.

## Managed ownership evidence

A valid project covenant does not annex every occupied skill path. A
projection is managed only when one of these is true:

1. the current user explicitly confirms annexation in this run; or
2. reachable Git history proves a prior ownership-establishing transition and
   continuous ownership through the candidate baseline.

An ownership-establishing transition must combine the valid contract tuple,
canonical source presence, projection path history, a valid post-transition
pair (identical complete Git trees for skills; deterministic source render
equal to the unique block for entry/rules), and commit/diff evidence
consistent with confirmed create, projection, adoption, or annexation. A
newly appended intent record and commit message may support that conclusion
but neither is sufficient alone. If the evidence admits a plausible unmanaged
duplicate, there is no managed baseline.

Ownership ends only through an explicit delete, rename, replacement,
migration, or offboarding decision. Unknown occupancy never inherits
ownership merely because the project is onboarded.

## Baseline selection

Recompute the baseline independently for each unit on every run. Do not store
hashes, attribution metadata, or a side database.

1. Enumerate commits reachable from `HEAD` only. Other refs, reflogs,
   timestamps, author dates, and commit dates cannot select a baseline.
2. A candidate commit must carry the exact current contract tuple and valid
   ownership evidence. A skill requires identical complete Git trees. An
   entry/rule requires a safe raw source plus one unique historical block
   whose normalized body equals the deterministic render.
3. Candidate `x` is older than candidate `y` when
   `git merge-base --is-ancestor x y` succeeds and the commits differ.
4. Retain ancestry-maximal candidates: candidates with no newer candidate
   descendant in the set.
5. Exactly one maximal candidate is baseline `B`. Zero means `no-baseline`.
   Two or more incomparable maximal candidates mean ambiguous history:
   `blocked`, `decision-required`, and no write for that unit.

This DAG rule handles merged histories without choosing by wall-clock time.
Contract migration is a barrier: a byte-identical unit under another contract
version is not a normal current baseline. The sole bridge across that barrier
is the qualifying closed-set migration transition defined above: its commit is
a current candidate for every carried unit, while released units receive no
current ownership. Runtime selection after that transition reads only
current-tuple candidates; it never dual-reads an archived tuple.

For skills, compare the current source snapshot `S` and projection snapshot
`P` with tree baseline `B`; absence is a tree value. For entry/rules compare
raw `S` with `B_s` and normalized block body `P` with `B_p`, then separately
test whether current `P == render(S)`.

## Reconciliation table

Apply the first applicable row after safety, ownership, and baseline checks.

| Baseline | Current relation | State | Proposed action |
|---|---|---|---|
| unique B | S = B and P = B | `unchanged` | `unchanged` |
| unique B | S differs from B; P = B; S exists | `source-only` | `update` |
| unique B | S absent; P = B | `source-only` | `delete` from source to projection |
| unique B | S = B; P differs from B; P exists | `projection-only` | `adopt` |
| unique B | S = B; P absent | `projection-only` | `delete` from projection to source |
| unique B | S and P both differ from B; S = P; intent complete | `unchanged` | `unchanged` |
| unique B | S and P both differ from B; S = P; required semantic intent missing | `intent-missing` | `update` source intent and reproject the resulting tree |
| unique B | S and P both differ from B; S != P | `both-changed` | `conflict` |
| none | valid S exists; target path is absent or empty | `no-baseline` | `create` after adding the initial intent record |
| none | any non-empty P exists, including S = P | `no-baseline` | `annex-or-keep` |
| ambiguous | any | `blocked` | `resolve-blocker` |

`source-only`, `projection-only`, and `both-changed` describe deltas from the
same B, not line-diff shape. Only different current trees changed on both
sides are `conflict`. Never perform an automatic three-way merge.

Serialize `both-changed` as a selected decision closure with authorization
`required`, outcome `deferred`, and `decision-required`; it is a visible
zero-write decision, not an omitted partial-batch member. A projection-only
semantic-review candidate with exact proposed source and rerender bytes uses
its selected physical closure, authorization `required`, outcome `planned`,
and both `intent-required` and `semantic-review-required`. This is distinct
from pending Codex-start segmentation, which has no source target yet.

`reproject` is a user-confirmed resolution when source should replace a
projection-side change that the user identifies as accidental or mechanical.
It is not inferred from current two-tree shape. `annex` and `keep` appear only
after the user resolves `annex-or-keep`: annex establishes ownership using a
chosen authority; keep performs no unit write, creates no ignore manifest,
leaves the unit unresolved, and cannot be reported as synchronized. A
same-path kept skill must later be relocated, replaced through an explicit
decision, or abandoned.

### Entry/rule reconciliation

Use the same state/action tokens with render-aware equality:

| Baseline | Current relation | State | Proposed action |
|---|---|---|---|
| unique pair | S and P exist; `P = render(S)`; intent complete | `unchanged` | `unchanged` |
| unique pair | S and P exist; `P = render(S)`; required semantic intent missing | `intent-missing` | `update` source intent only; rendered block stays byte-identical |
| unique pair | `S != B_s`; `P = B_p`; S exists; current pair not converged | `source-only` | render and `update` block |
| unique pair | S absent; `P = B_p` | `source-only` | delete proven block after explicit destructive confirmation |
| unique pair | `S = B_s`; `P != B_p`; P exists; current pair not converged | `projection-only` | reverse-map and `adopt` |
| unique pair | `S = B_s`; P absent | `projection-only` | delete source only after explicit destructive confirmation |
| unique pair | both changed; `P != render(S)` | `both-changed` | `conflict` |
| none | valid source; paired id absent | `no-baseline` | `create` block after initial intent |
| none | any block/manual content is proposed as authority | `no-baseline` | `annex-or-keep`; never infer ownership |
| ambiguous | any | `blocked` | `resolve-blocker` |

Projection-only adoption strips an exact `pv2` preamble, preserves source
frontmatter/control comments/claude-only protected spans, and applies mapped
body changes. A valid exact preamble edit may update `paths`. A hunk crossing
a protected boundary, a non-exact preamble, or host-specific wording needs
`semantic-review-required`: present proposed source bytes and their exact
rerender, then wait for explicit confirmation. There is no free semantic
managed mode.

### Hooks reconciliation

Apply the first applicable row per host unit after safety, ownership, and
baseline checks. `S` is the entry model, `P` the owned group's handler model
on that host, and `project(S, h)` the desired model for that host. Two rows
override first-match order and are stated as such. A host whose target
declares `surface: none` takes the `declared-unsynced` row only while its
carrier is unoccupied for that entry, using report/v5's H-T4-PRESENT test: no
handler marked `[bridge:<entry-id>]` anywhere in that carrier and, when the
entry declares a `command`, no command handler in the
`(event, effective-matcher(h))` group whose `command` equals the effective
command. An occupied `surface: none` host falls
through to the ordinary `no-baseline` / `annex-or-keep` row, which is the
write-side answer to the `drift`/`reconcile` that report/v5 reports as
H-T4-PRESENT in an onboarded project. An entry whose `class` is `gate` or
`side-effect` with `enabled: true` and no covering `enabled-by` record keeps
its computed state but takes the `opt-in-or-skip` action inside
`closure/decision/hooks/<entry-id>`.

| Baseline | Current relation | State | Proposed action |
|---|---|---|---|
| unique pair | `P = project(S, h)`; required intent complete | `unchanged` | `unchanged`; no Write capabilities row, and `hook-format-preserved` when the bytes differ |
| unique pair | `P = project(S, h)`; a required semantic source intent record is missing | `intent-missing` | `update` the source intent only |
| unique pair | `S != B_s`; `P = B_p` | `source-only` | `update` the carrier |
| unique pair | entry absent; `P = B_p` | `source-only` | `delete` the owned group after explicit destructive confirmation |
| unique pair | `S = B_s`; `P != B_p`; `P` exists | `projection-only` | `adopt` within the restricted field set below |
| unique pair | `S = B_s`; `P` absent | `projection-only` | `delete` the source entry after explicit destructive confirmation |
| unique pair | both differ; `P != project(S, h)` | `both-changed` | `conflict`; one entry-level decision closure, zero writes |
| none | valid entry; owned group absent | `no-baseline` | `create` after the initial intent record |
| none | any non-empty owned group, foreign handler, semantics-changing key, or marked orphan | `no-baseline` | `annex-or-keep` |
| any | `targets.<h>.surface: none` and that carrier is unoccupied for the entry | `declared-unsynced` | `unchanged` |
| any | `class` is `gate` or `side-effect`, `enabled: true`, and no covering `enabled-by` record | as computed above | `opt-in-or-skip` |
| ambiguous | any | `blocked` | `resolve-blocker` |

Semantic handler equality decides the state; byte equality decides only
whether a physical write row exists. `declared-unsynced` is a real serialized
state, not an omission: it is how the plan states that a declared hook has no
counterpart on that host.

### Hook handler reverse adoption

The adoptable field set is exactly the declared field set for that host:
`command`, `commandWindows` on Codex, `timeout`, and the group `matcher`.

`statusMessage` is never adopted. `source-tree/v5` gives it no source field,
so it is an attribution key rather than a projected value: any text after the
`[bridge:<id>]` prefix is unowned free text with no destination in
`.claude/rules/hooks.md`, and adopting it would be dropped by the next
projection. The desired model therefore takes its `statusMessage` from the
existing handler on both hosts, so a hand-added suffix is carried forward
verbatim, compares equal, and never becomes drift or an adoption candidate.
Bridge writes the bare `[bridge:<id>]` marker only into a handler that
carries no `statusMessage` at all: on Claude whenever it composes the
handler, and on Codex only at creation. On an existing Codex handler
`statusMessage` is outside the edited field set entirely, because it is
inside the Codex trust identity.

A changed value maps to the shared scalar only when the other host's value is
unchanged and equal to it, and the plan MUST then show the resulting
rerendered bytes for the other host's carrier before confirmation. Otherwise
it maps to `targets.<host>.<field>` and requires both a stated
`override-reason` and an explicit confirmation. Bridge never collapses a
per-host edit into the shared scalar by inference.

`event` is never adopted. A different event is a different group, so it is a
proven managed delete plus a create, each under its own gate.

A passthrough-key change is not adoption at all: Codex
`additionalContextLimit` and Claude `if` are preserved in place, excluded from
handler equality, and leave the row `unchanged`.

A `type` change, a foreign handler, a semantics-changing key (Claude `args`,
`async`, `asyncRewake`, `once`; Codex `async`), more than one command handler
in an owned group, and any matcher change that becomes mode-ambiguous force
`semantic-review-required` with the exact proposed source bytes and their
deterministic rerender.

Every adoption appends a `bridge:intent` record and carries
`intent-required`. Adopting the `command` of a `gate` or `side-effect` entry
additionally requires a fresh dated `enabled-by` record: a stale
acknowledgement must never carry across a hand-edited command line.

Serialize every unresolved handler in the `## Hook adoption decisions` table
of `sync-plan/v3` with its location, disposition, destination, and decision.
A confirmed `adopt` writes the new entry into `.claude/rules/hooks.md` inside
`closure/hooks/source` with user-supplied prose bullets; Bridge never invents
`Purpose` or `Failure policy`. `discard` is destructive and needs its own
explicit confirmation. Bridge never deletes an unowned handler and never
rewrites a user key to make a row converge.

## Intent records

Every managed skill source contains valid `bridge-intent.yaml`, and the skill
projection copies it byte-for-byte. Entry/rule units carry the strict
source-tree/v5 `bridge:intent` HTML comments; their renderer strips those
comments from `AGENTS.md`. Do not add a `bridge` YAML frontmatter key.

Append one `{date, note}` record for:

- initial create/onboarding of a unit;
- explicit annexation or projection-side adoption;
- semantic source updates;
- rename, with old and new names and motivation.

Do not append for `unchanged` or a mechanical `reproject`. If a semantic
payload converged on both sides but lacks a corresponding new record, the
plan adds the record to the source and mechanically reprojects when the
rendered carrier changes. Obtain or propose the one-line motivation before
the write; never invent ownership from the record.

A hook entry carries its own entry-local `intent` list in the fenced block of
`.claude/rules/hooks.md`, with the same `{date, note}` grammar and the same
append triggers. It additionally carries `enabled-by`, a list of
`{date, note}` records that is required when `class` is `gate` or
`side-effect` and `enabled` is `true`. `enabled-by` is not an intent record
and never substitutes for one: it is the dated opt-in that authorizes
projecting a high-consequence hook at all. Appending either record is a write
to `.claude/rules/hooks.md` inside `closure/hooks/source`.

The one-time file-level comment
`<!-- bridge:hooks-shared-execution <YYYY-MM-DD> acknowledged: committed Claude hooks run for every clone without a trust prompt -->`
must exist before the first Claude hook carrier write. Its absence emits
`hook-acknowledgement-missing` and blocks `closure/hooks/claude` only.

## Three onboarding starts

- **Empty project**: propose the minimal source units, current covenant pair,
  and rendered blocks. Newly created untracked files remain honestly
  untracked; the same operation's verified result preserves its
  `bootstrap-required` create/applied shape, while a later independent scan
  blocks on the still-untracked pair. Bridge never claims onboarded until both
  covenant halves are tracked and exact. Do not add `onboarding/agents-md`
  merely because the root `AGENTS.md` create is unavailable; that unit exists
  only for explicit segmentation decisions over existing content.
- **Claude start**: treat the one existing entry and safe rule shards as
  source candidates. Existing `AGENTS.md` bytes stay manual unless the user
  explicitly selects exact spans for shared adoption.
- **Codex start**: segment existing `AGENTS.md` into contiguous exact byte
  spans and list every non-whitespace span in the sync-plan/v3 Adoption
  decisions table. The user confirms each disposition as `shared-entry`,
  `shared-rule`, `manual`, or destructive `discard`; a shared disposition
  records `entry` or `rules/<id>` in the separate destination column, with
  optional valid paths for a rule. Never annex the whole file by inference.

For a confirmed shared span, source creation/update and replacement of that
same AGENTS span with its deterministic managed block are one closure. Manual
spans remain byte-identical. Show the proposed source, any host-neutral
rewrite, and the exact rerender before writing. Default Claude `/init` is not
an onboarding mechanism and is not assumed to read `AGENTS.md`.

## Delete and rename

Automatic destructive convergence requires a unique baseline proving that the
affected projection was managed. Without it, deletion is absence and rename
is unknown occupancy, not permission to remove or move anything.

A delete records its direction and motivation in the plan. When the canonical
unit disappears, its local intent carrier disappears too; durable tombstone
evidence must be carried by the eventual user commit/diff (Bridge does not
commit) or by an explicit future covenant mechanism. Warn the user not to
lose that evidence.

A hook delete removes the owned element span plus exactly one adjacent
separator comma, the preceding one when the element is not first and
otherwise the following one, together with the whitespace run on that side.
When a deletion empties an event, remove the whole `"<Event>": [...]` member
rather than leaving an empty array: Codex trust keys are per event, so no
other event re-indexes. When the `hooks` object itself becomes empty, leave
`"hooks": {}`, because removing the key changes what an absent carrier means
on the read side. Any Codex deletion that removes a non-final element from an
event that retains others shifts the positional trust keys of the later
elements and emits the acknowledged `codex-trust-reindex`. Bridge never
deletes an unowned group or an unowned handler under any of these rules.

Rename is one dependency closure over old and new units. For a rule rename,
the source path, derived marker id/source, old block, and new block are the
same closure. Accept it only when
the user states the rename intent or reliable Git path history establishes
the move; never infer it from similarity scores. Validate the new identity,
append its rename intent record, prove ownership of every old path/block to be
removed, and require the destination to be absent/empty or explicitly
annexed. If any old/new member conflicts or is blocked, write none of the
rename closure. Serialize its destination/source path operations in order and
require an attested strict protocol for every forward and inverse step.
The new unit has no current baseline and therefore uses baseline `-` with
state `no-baseline`; every old unit uses its proven baseline with state
`source-only`.
`guarded-patch/v1` never participates in rename. If any strict create,
replace, delete, or compensation primitive is unavailable, emit
`conditional-write-unavailable` and block the entire rename before mutation.
There is no cross-file atomic guarantee even when every individual step is
strict.

## Planning and confirmation

Every write begins with the complete `sync-plan/v3` pre-write report. Include:

- all affected units, current snapshots, baselines or their absence, actions,
  directions, compatibility annotations, exact paths, and stable closure ids;
- the exact Closures table: sorted members and dependencies, selected versus
  not-selected status, and per-closure authorization;
- the exact Capability profiles and Write capabilities tables: closed
  environment/tool bindings plus physical step order, path operation,
  forward protocol/binding, and pre-resolved inverse protocol/binding;
- for contract migration, the complete independent Migration candidates table
  with every ancestry-maximal legacy candidate oid per unit;
- every relevant non-ignored untracked path and every excluded ignored path;
- related dirty changes plus a scoped summary of unrelated dirty changes that
  will be preserved;
- for hooks, the complete `## Hook tiers` table, the `## Hook adoption
  decisions` table, the exact command line of every projected hook, and the
  pinned disclosure that the opt-in record is a review checkpoint in Git and
  not an enforcement boundary;
- covenant/manual-zone impact, exact planned full `AGENTS.md` byte count,
  target-eligibility evidence, all blockers, and every onboarding/adoption
  decision.

The Units and Closures tables serialize affected or explicitly request-scoped
units, not every carrier inspected during the repository-wide preflight. An
`onboarded` header proves the covenant precondition; it does not by itself add
an unaffected `onboarding/covenant` row. A covenant row appears only when the
covenant is itself the requested or affected unit.

Decisions are per unit, but authorization and execution are per serialized
closure. Every unit row binds one stable closure id and repeats that closure's
`selection` and `authorization`; no selection may live only in Evidence and
notes. All selected changes to root `AGENTS.md` are composed into one desired
file and one `closure/agents-md` write-protocol closure, together with
their source paths, except that a contract migration uses the encompassing
`closure/migration`. Unselected/conflict blocks and every manual span are
protected preconditions, not implicit mutation dependencies: an independent
block may change while a conflict block remains byte-identical. The covenant
pair, closed migration set, and each old/new rename pair remain indivisible.
A conflict or blocker receives zero writes.

Independent, unambiguous closures may proceed only when the serialized plan
marks each one `selected` and `confirmed`. A partial batch is represented by
`not-selected` closures and unit rows before confirmation, never by a prose
exception. Verify closure dependencies after selection; selecting a closure
whose dependency is not selected/confirmed is a blocker. Stop at the first
failed or partial selected closure.
Any later closure skipped because of that stop, or any dependent closure that
cannot execute, receives `not-attempted`; it is neither `blocked` nor
`failed`.

Conflict, annexation, replacement, migration, offboarding, and any destructive
choice require an explicit decision. All other writes still require
confirmation of the complete scoped plan. Re-scan if relevant bytes change
between plan and confirmation.

Every write blocker must map to the closed apply-blocker registry in
`sync-plan/v3`; reconciliation may not introduce an unregistered prose-only
blocker. In particular `mode-limited`, `sensitive-or-generated-blocked`, and
`unsafe-tree-entry` block writes just as strictly as activation, marker,
baseline, covenant, source-schema, migration, and conditional-capability
failures.

The `write capability`, `hook carrier`, and `hook opt-in` gates are the only
gates whose prohibition is scoped to the matching closure and its dependents;
`hook source` and every other gate stay project-wide. A scoped-blocked
closure keeps `selected` with authorization `not-applicable` and outcome
`blocked`, never `not-selected`; when its sibling carrier proceeds, the
acknowledged `hook-projection-asymmetric` is emitted on the blocked carrier.
For an entry whose `class` is `gate` the sibling does not proceed at all: a
blocked or unavailable carrier forces the other carrier closure to
`not-selected` with zero writes, because asymmetric enforcement is worse than
no enforcement.

## Writes, validation, and rollback

Resolve `capability-profile/v1` against the active host, host version, tool
surface, platform, and filesystem assumptions. Every operation defaults to
unavailable. Prefer an attested strict protocol:

- existing-file replacement: `strict-replace/v1`;
- absent-path creation: `strict-create/v1`; and
- existing-file removal: `strict-delete/v1`.

An adapter must bind the mutation and complete expected value in one
operation. A planning read, user confirmation, advisory lock, atomic rename,
or tool success message is not capability evidence. Create, delete, rename,
mode changes, and inverse operations never degrade to an optimistic
check/write sequence. Emit `conditional-write-unavailable` and block before
mutation when their required strict protocol is absent.

### Capability attestation

Strict capability is opt-in evidence, never an inference from a programming
environment. In the absence of an explicit versioned adapter attestation,
PowerShell cmdlets or .NET file APIs, Claude Code `Edit` or `Write`, Codex
`apply_patch`, and Python file or path I/O all remain `unavailable` for
`strict-replace/v1`, `strict-create/v1`, and `strict-delete/v1`. A successful
call, an exclusive handle implemented ad hoc by the agent, a pre-read, or an
exact post-read does not upgrade that classification. A named primitive may
support `guarded-patch/v1` only when its attestation independently proves
every exact-literal and complete-file requirement below.

`write-capability-fixture/v1` is fixture-only replay evidence. It is never a
live host attestation and never authorizes a write outside its one
materialized fixture operation. Accept it only when all of these bindings
validate before plan serialization:

1. the worktree is a lease-bound OS-temporary fixture materialization and its
   retained marker is a safe plain regular file under that worktree's exact
   Git directory;
2. the marker's spec, suite, scenario, resolved root, baseline commit, and
   caller-supplied lease hash all match the current materialization, and
   current `HEAD` equals the bound baseline commit;
3. the marker binds the SHA-256 of one safe plain
   `write-capability-fixture/v1` document, and the independently recomputed
   document hash matches;
4. the document repeats the marker's exact spec, suite, scenario, resolved
   root, baseline commit, and lease hash, and binds the exact replay-input
   branch, operation kinds, protocols, profile fields, and filesystem
   assumptions used by the plan; and
5. neither marker nor capability document is discovered by scanning, reused
   across a different root, lease, scenario, branch, `HEAD`, plan, operation,
   process, or session.

If any binding is absent or mismatched, ignore the fixture profile and fall
back to `unavailable`. The formal sync-plan validator must reject a fixture
profile that lacks this complete marker/lease/hash chain. Fixture evidence
does not establish ownership, a Git baseline, or a production adapter.

For a fixture fault adapter that mutates a root-child target, platform
attestation must additionally bind the current child name to the retained leaf
in the same mutation. A retained POSIX leaf handle, inode identity, and link
count do not provide that binding after a same-directory rename followed by a
replacement at the original name. Until an adapter proves the missing binding,
the POSIX mutation case is declarative-only and `apply-fault` must fail closed
before target mutation. Do not project this restriction onto Windows:
Windows capability remains independently resolved from its handle, name,
reparse, and filesystem attestation, without silent upgrade or downgrade.

For replacement of an existing safe, byte-round-trippable regular UTF-8 text
file with a non-empty preimage, `guarded-patch/v1` is an explicitly weaker
alternative when strict replace is unavailable. Derive one contiguous region
covering every changed Unicode code point, extend stable unchanged context
only at code-point boundaries until the exact non-empty old region occurs
once in the complete preimage, and record its byte offset and exact old/new
UTF-8 values. The complete preimage, postimage, old region, and new region
must decode as strict UTF-8; the offset and old-region end may not split a
multi-byte code point. The complete postimage must be exactly
`prefix + new-region + suffix`. The adapter must expose one exact-literal,
unique-match, non-regex, non-fuzzy, non-`replace_all` replacement. If any
condition fails, emit `guarded-patch-unavailable` and block.

A selected guarded path emits `guarded-patch-non-cas`; guarded root
`AGENTS.md` also emits `manual-zone-guarded`. Both require explicit
acknowledgement. The user must see that preflight and postverification leave a
race inside the host call: an in-region concurrent edit can be rejected or
overwritten, and postverification proves only the observed complete value at
that moment. Never call this CAS, atomic replace, or a transaction.

Before the first mutation in the selected closure set, create one
operation-local journal in a newly allocated, access-safe OS-temporary
operation-id lease directory outside the repository. Create the directory and
journal exclusively without following links or reparse points. Generate an
opaque `operation-id` for this live run and retain the exact journal path in
memory; never discover journals by scanning a broad temporary directory. The
journal may bind only an independently serialized, confirmed
`phase: pre-write` plan whose selected mutations and closures are
`confirmed` / `planned`, apart from a scoped-blocked closure that stays
`not-applicable` / `blocked` and contributes no journal step; it must never
digest a post-write result or expectation. The journal binds:

- `operation-id`, resolved repository path, starting `HEAD` object id (or
  `unborn`), and SHA-256 of the exact confirmed sync-plan/v3 bytes;
- every selected stable closure id, its dependencies, selection, and
  authorization;
- lifecycle `prepared`, `executing`, `compensating`, `verified`, `partial`, or
  `closed`; and
- for every planned path operation: serialized step, closure id, operation
  kind, forward protocol, inverse protocol, capability-profile binding, exact
  pre-value (absence or type/raw bytes/representable mode), exact intended
  post-value, and the exact value observed after the host call;
- for `guarded-patch/v1`, the region byte offset and exact old/new region.

The digest binds authorization to the serialized plan; it is not ownership
metadata or a durable baseline. A journal from a different repo, `HEAD`, plan
digest, closure selection, operation id, or process/session cannot authorize
mutation. Any byte change to the confirmed pre-write plan invalidates the
digest. Cleanup validates the retained path, operation id, repository,
lifecycle, plain-directory lease, and plain regular journal without following
links, then removes only that exact journal and its exact empty lease
directory. It never scans or removes sibling leases.

For an `AGENTS.md` closure, compute the complete desired file bytes before any
mutation. Recheck every source precondition and the exact full AGENTS preimage
at preflight. Write canonical source paths first and the composed AGENTS
carrier last. A strict carrier uses `strict-replace/v1`; a guarded carrier
uses one region derived only after all selected block changes are composed.
The region may span manual, unselected, or conflict bytes, but their old/new
values must be identical. A missing carrier uses only `strict-create/v1`.
The journal stores complete pre/applied images rather than block bodies.

When a plan writes hook units, the step order is `.claude/rules/hooks.md`,
then `AGENTS.md`, then `.claude/settings.json`, then `.codex/hooks.json`.
Source is written first so a carrier never records a decision the source
cannot justify, and the two hook carrier closures never depend on each
other, so one may proceed while the other is scoped-blocked.

### Hooks carrier writes

Both hook carriers use `guarded-patch/v1` for `replace` and
`strict-create/v1` for `create`. `json-owned-span/v1` is the postimage
derivation rule for those carriers. It is not a protocol token, claims no
adapter strength, and adds no journal field.

1. **Eligibility.** The carrier must be an existing, safe,
   byte-round-trippable regular UTF-8 text file that parses as a JSON object
   under a strict parser with no duplicate object key anywhere and whose
   `hooks` value stays inside the closed shape: an object of event names,
   each an array of group objects carrying an optional string `matcher` and a
   `hooks` array of handler objects. A handler member whose value is not a
   string, integer, or boolean stays inside the closed shape: it is unowned,
   its bytes are preserved verbatim, Bridge never projects it and never reads
   it as a declared field, and it is never a reason to block the carrier. The
   motivating case is a Claude `mcp_tool` handler carrying an `input` object.
   `unmodelled-shape` is therefore reserved for a carrier root that is not a
   JSON object, a `hooks` value that is not an object, an event value that is
   not an array, a group element that is not an object, a non-string
   `matcher`, a group without a `hooks` array, a handler element that is not
   an object, a handler without a string `type`, and the whole-carrier case of
   a span scan that disagrees with the strict parser. A parse failure, a
   duplicate key, or one of those violations emits `hooks-carrier-unusable`
   with reason `(parse-error)`, `(duplicate-key)`, or `(unmodelled-shape)` and
   blocks that closure. Failing closed is mandatory: a bridge that guesses
   which duplicate key it owns can silently drop a user's hook.
2. **Owned-span location.** Locate spans from the exact preimage bytes with
   the span-preserving inspector, which never reserializes and never judges
   ownership. The owned span set is derived from the intent document alone:
   for host `h`, one span per owned `(event, effective-matcher(h))` group. A
   group that does not exist is a zero-width insertion point carrying its
   exact separator bytes at the `group`, `event`, or `hooks` level.
3. **Composed desired image.** The postimage is the preimage with owned spans
   edited in place and located insertion points filled. An existing handler or
   group uses minimal-member-span editing: a changed scalar replaces exactly
   that value span, an added key is inserted after the object's last member
   using that object's own separator and indent, and a removed key removes its
   member span plus exactly one separator. Group key order and an unchanged
   `matcher` member are never rewritten. A new group or handler uses the
   canonical render with the style inferred from the file, with the fixed
   handler key order `type, command, commandWindows, timeout, statusMessage`,
   then the Claude-only `shell`, then any carried-forward passthrough key in
   its original relative order, and group key order `matcher, hooks`.
   `source-tree/v5` `### Projected handler shape` is the authority for that
   complete order. Every other byte is copied verbatim,
   including sibling events, sibling groups, unrelated top-level keys, the
   Codex top-level `description`, key order, indentation, and the file's
   trailing-newline presence. Reserializing the parsed document is forbidden
   and is rejected by the `hooks-carrier-composition` validator check. Bridge
   writes only documented fields, so its own output can never break the
   carrier: handler types `http`, `mcp_tool`, `prompt`, and `agent` are never
   projected, and neither is any passthrough key (Codex
   `additionalContextLimit`, Claude `if`) or semantics-changing key (Claude
   `args`, `async`, `asyncRewake`, `once`; Codex `async`). An existing key of
   any of those kinds is preserved in place and never removed.
4. **Region derivation.** Hand the `(preimage, postimage)` pair to the
   unchanged generic guarded rule. Hooks JSON is repetitive, so the region may
   legitimately cover adjacent unowned bytes whose old and new values are
   identical. Context is never shortened to force a match; a region that
   cannot be made unique emits `guarded-patch-unavailable` and blocks.
5. **Idempotence law.** `compose(preimage, desired) == preimage` whenever
   every owned group already parses equal to its desired model, regardless of
   formatting. Semantic handler equality decides the state: strip leading and
   trailing ASCII whitespace from strings, compare code points, compare
   `timeout` as an integer, require `type` to equal `command`, match matcher
   absence only with absence, and exclude passthrough keys. Byte equality
   decides only whether a Write capabilities row exists. A semantically equal,
   passthrough-clean group therefore yields `unchanged` / `unchanged`, no
   Write capabilities row, and the informational `hook-format-preserved`.
   Bridge never reformats a converged group.
6. **Append-only array discipline.** Bridge never moves, sorts, or reorders an
   existing element, owned or unowned. Codex persists per-hook trust and the
   user's own disable choice under positional keys, so a deterministic re-sort
   would re-point unrelated hooks' trust and could silently re-enable a hook
   the user deliberately disabled. A new group is appended at the array's
   closing bracket, back-tracked over the trailing whitespace run. A new
   `hooks.<Event>` member is inserted in byte-wise ascending order among the
   existing event keys when those keys are already ascending, and appended
   last otherwise; both cases are deterministic.
7. **Codex `description`.** `.codex/hooks.json` denies unknown top-level keys
   and has exactly two, so `description` is the user's only metadata slot.
   Bridge never writes it, never creates it on a create, and preserves an
   existing value byte-for-byte as unowned bytes. Its absence is never
   repaired.
8. **Class gate.** Never project a `gate` or `side-effect` entry without a
   dated `enabled-by` record already present in the source document. The
   record is a reviewable checkpoint in Git that every clone inherits, not an
   enforcement boundary. Hooks committed to a repository run for everyone who
   clones it, and Bridge classification is review metadata, not a sandbox.
9. **Post-write verification.** After every hooks-carrier write, re-parse both
   hooks carriers and verify that every unowned byte is byte-identical to the
   preimage, that every owned group parses equal to its desired model, and
   that the complete file still parses with no duplicate key. Any mismatch
   follows the ordinary complete-value classification: exact planned preimage
   with no prior mutation is `failed`, and every third value is `partial`.

### Host trust consequences

These host facts were verified at source level on 2026-09-07 and bind the
disclosure Bridge must serialize. They are consequences of the write, not
capabilities Bridge can control.

Codex binds per-hook trust to a normalized identity computed after timeout
defaulting and clamping. The identity contains the normalized `timeout`,
`statusMessage`, the normalized `additionalContextLimit`, `matcher`,
`command`, and `async`. It does not contain `commandWindows`. Therefore:

- a change to any identity field emits the acknowledged
  `codex-hook-retrust-required` with its `(<Event> group=<i> handler=<j>)`
  detail, one line per changed handler, so the user sees before confirmation
  exactly which hooks go dark; and
- a replacement that touches only `commandWindows` of a handler that already
  exists in `.codex/hooks.json` keeps the old trusted hash valid, so the
  changed Windows command runs under the previous approval. That asymmetry is
  security-relevant, so Bridge emits the informational
  `codex-trust-blind-change` for it and never `codex-hook-retrust-required`.

Codex writes trust state as `[hooks.state."<key>"]` into the user's
`config.toml`, keyed `<source>:<Event>:<groupIndex>:<handlerIndex>`. The key
is positional, so Bridge renders groups and handlers in a stable sorted order,
appends only, and reports any index shift with `codex-trust-reindex`. Bridge
does not read that state: it lives outside the repository byte domain, and
project trust is the documented, live-verified signal it does read.

Projection adds the `[bridge:<id>]` `statusMessage` marker on the Claude
surface always, and on the Codex surface only when creating the handler.
Bridge never adds, changes, or removes a Codex `statusMessage` on an
otherwise converged handler, because that field is inside the Codex trust
identity and touching it manufactures a re-trust.

Codex skips untrusted and modified hooks silently at dispatch, with no prompt
during a session and no notice in the `codex exec --json` stream. The user
reviews and trusts them inside Codex. An untrusted project never loads the
`.codex/` layer at all, which is why `codex-project-untrusted` is a real
inertness signal rather than a hedge.

An interactive Claude session holds settings-file hooks until the workspace
trust dialog is accepted, but a `-p` or SDK session never shows that dialog
and treats the folder as trusted, so hooks committed in a repository's
`.claude/settings.json` run in a folder the user has never trusted. The
per-teammate opt-outs are `--bare`, `--safe-mode`, `--setting-sources user`,
and `--settings '{"disableAllHooks": true}'`. That is why every Claude hook
carrier write emits the acknowledged `claude-hooks-shared-execution` and why
the first such write requires the dated file-level acknowledgement in
`.claude/rules/hooks.md`.

Hook execution itself is observed-but-not-guaranteed on both hosts, and edits
to a hooks carrier are only normally picked up without a restart. No Bridge
state may be read as a runtime guarantee.

### Guarded and strict call discipline

Immediately before every guarded call, re-read the complete file and require
exact type and preimage equality. If it differs before any mutation, report
`failed`; if an earlier step already mutated the closure, report `partial`.
Confirmation never substitutes for this final preflight. A deterministic
preflight-mismatch replay therefore orders its events as exact plan
confirmation, bound external change, final complete-file preflight rejection,
then a `failed` post-write result with zero Bridge writes; it does not claim
that the change happened after the final preflight.
Invoke the one exact-region replacement, then re-read the complete file
regardless of tool success or error:

- exact planned postimage verifies that step and permits the next step;
- exact planned preimage yields `failed` when no prior step mutated, otherwise
  `partial`; and
- any third value, unreadable path, or changed type yields `partial`.

Apply equivalent complete-value postverification after every strict call.
Stop on the first rejection or mismatch and never touch unrelated dirty
paths. A multi-path closure has no stronger guarantee than its individual
calls. Bridge implements no lock, cross-file transaction, crash durability,
or stronger atomicity than an attested strict primitive actually supplies.

After all steps:

1. re-read every affected path;
2. compare skill manifests over path/type/bytes/modes and compare every
   entry/rule block with a fresh deterministic render;
3. verify the covenant source, every selected managed block, the complete
   full-file AGENTS image, and all protected manual spans;
4. re-parse both hooks carriers, verify every unowned byte against the
   preimage, and verify every owned group against its desired model;
5. run scoped `git status --short`, scoped `git diff`, and
   `git diff --check`; and
6. emit the post-write plan with per-unit outcomes and remaining warnings.

When execution actually writes root `AGENTS.md`, or a failed/partial host call
means that carrier may have been written, attach `restart-may-be-required` to
only the affected entry/rule rows and instruct the user to start a new Codex
run/session before testing activation. A pre-write blocker, deferred or
not-selected closure, source-only operation that cannot touch the carrier, or
failed operation proven to retain the exact preimage receives no restart
annotation. Do not rely on current-main environment-selection refresh
behavior as a public reload contract.

When execution actually writes `.codex/hooks.json`, or a failed/partial host
call means that carrier may have been written, attach `awaiting-host-trust`
to only the affected `hooks/<entry-id>/codex` rows and state that Codex lists
a new or modified hook as requiring review and silently skips it until the
user trusts it in Codex. `codex exec` never prompts and simply will not run
it. A pre-write plan never carries the annotation.

Same-operation failure compensation is disabled by default. Resolve every
inverse protocol before the first forward mutation: replacement needs
`strict-replace/v1`, creation needs `strict-delete/v1`, and deletion needs
`strict-create/v1`. `guarded-patch/v1` is never an inverse. If any inverse is
unavailable, emit `strict-compensation-unavailable`; explicit acknowledgement
may authorize the forward guarded plan, but it does not authorize an
optimistic reverse operation.

Only when all needed inverse steps are strict does the already confirmed plan
authorize compensation in that same live operation while the bound journal
remains open. Walk observed mutations in reverse with those serialized strict
steps and verify each complete result. Full restoration yields `compensated`.
An unavailable/rejected inverse, restoration mismatch, missing live journal,
or inability to prove the complete pre-write closure yields `partial`.
Preserve scoped evidence and mark dependent or later selected closures
`not-attempted`.

Once an `applied` result is emitted, mark the live journal `verified` then
`closed`; it grants no later or cross-session rollback authority. A later
user-requested rollback is a new operation with a new plan and explicit
confirmation, reconstructed from current bytes plus reachable Git. User
confirmation authorizes that new plan but cannot substitute arbitrary evidence
for missing ownership, baseline, or prior bytes. If reachable Git cannot
reconstruct the exact prior value, rollback is unavailable; the user may
instead confirm a separately classified annexation or destructive decision
under its normal gates. Never scan temporary directories for an old journal
or promise recovery from one. A successfully reconstructed and conditionally
executed reverse plan may receive `rolled-back`. Never use blanket restore,
reset, stash, or cleanup, and never erase a pre-existing or concurrent user
change.
