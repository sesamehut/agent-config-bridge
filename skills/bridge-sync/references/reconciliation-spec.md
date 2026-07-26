# Bridge reconciliation specification

Spec version: reconciliation/v2.

This file defines the M3 write-side contract for project skills plus
entry/rule managed blocks. The read-only
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
- [Entry/rule baseline value](#entryrule-baseline-value)
- [Safety gates](#safety-gates)
- [Managed ownership evidence](#managed-ownership-evidence)
- [Baseline selection](#baseline-selection)
- [Reconciliation table](#reconciliation-table)
- [Entry/rule reconciliation](#entryrule-reconciliation)
- [Intent records](#intent-records)
- [Three onboarding starts](#three-onboarding-starts)
- [Delete and rename](#delete-and-rename)
- [Planning and confirmation](#planning-and-confirmation)
- [Writes, validation, and rollback](#writes-validation-and-rollback)

## Authority and scope

M3 writes only:

- the immutable covenant source at `.claude/rules/bridge-covenant.md`;
- Bridge-owned managed blocks in root `AGENTS.md`, preserving every other byte;
- exactly one Claude project entry (`CLAUDE.md` or
  `.claude/CLAUDE.md`);
- rule shards under `.claude/rules/**/*.md`, excluding the covenant and
  `.claude/rules/hooks.md`; and
- immediate skill units rooted at `.claude/skills/<name>/` and
  `.agents/skills/<name>/`.

M3 does not install `templates/covenant/hook-intents.md`, edit either hooks
surface, derive `agents/openai.yaml`, write `skills.config`, modify Codex
root-marker/budget/fallback configuration, or modify `AGENTS.override.md`.
It introduces no CLI, package, plugin manifest, bundled JavaScript, or
distribution payload.

The source remains canonical after ownership is established, but an edit made
on a proven managed projection is a valid input to adoption. Intent records
are evidence, never ownership by themselves.

## Versioned onboarding covenant

The single current contract tuple is:

```text
covenant/v2
source-tree/v4
report/v4
reconciliation/v2
sync-plan/v2
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
| both halves absent | prior exact archived v1 tuple and no completed explicit offboard | `contract-migration` | explicit `migrate` or `offboard` | historical pair decision + closed legacy-owned set + current pair + preserved manual zone |
| either occupied half has an unsafe path/type, exactly one half exists, or an untracked shape is not the exact both-untracked current pair below | any, regardless of declared tuple | `blocked` | `repair` with `user-decision` direction | safe, coherent pair + preserved manual zone; no migration in this closure |
| both halves exist, are safe and exact for the current tuple, and both are untracked | any | `blocked` | zero-write `resolve-blocker` with `user-decision` direction | user records both exact carriers as tracked; Bridge does not stage or write |
| both halves are tracked but either is malformed/modified, or their tuple declarations disagree | any | `blocked` | `repair` with `user-decision` direction | coherent exact pair + preserved manual zone |
| both halves are tracked, mutually coherent, and exact for archived v1 | any | `contract-migration` | `migrate` | old exact pair + closed legacy-owned set to current transition |
| both halves are tracked and exact for the current tuple | reachable v1 ownership exists but no qualifying closed v1-to-v2 transition commit is reachable | `contract-migration` | finish `migrate`; Bridge byte writes may already be unnecessary | closed legacy-owned set + current transition commit |
| both halves are tracked and exact for the current tuple | no legacy ownership requires carry-forward, or a qualifying closed v1-to-v2 transition commit is reachable | `unchanged` | `unchanged` | no write |

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
The exact v1 source and block under `templates/covenant/v1/` are read only to
identify one explicit v1/v3 → v2/v4 whole-pair migration. Normal runtime
supports no v1/v3 interpretation and no dual-read compatibility.

For migration, derive the complete legacy-owned set `L` from all
ancestry-maximal managed-unit candidates provable in the reachable v1 DAG.
Retain the complete maximal candidate set per unit. Serialize every full oid
in the independent sync-plan/v2 Migration candidates table; never choose one
incomparable candidate as a representative. A unit with one candidate repeats
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
v4 relation is carried automatically. Any missing, unsafe, ambiguous, or
non-converged member blocks the whole migration until the plan records an
allowed explicit decision; ambiguity itself cannot be hidden by
`repair-and-carry` or release based on an arbitrary candidate. A release must
leave durable, unambiguous Git transition evidence; destructive bytes need
separate explicit confirmation. No member may silently disappear because the
covenant changed.

A qualifying migration commit has a reachable pre-transition v1 covenant
state, the exact v2/v4 covenant pair in its tree, and the complete carried
set in a v4-converged state; its transition evidence also identifies every
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
path has precedence. Enumerate every safe rule shard from source-tree/v4,
excluding covenant and hooks. For each unit capture:

- raw current source bytes and exact path/type/tracking state;
- parsed v4 control comments and validated ordered `paths`;
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

## Safety gates

Resolve the repository root and every unit root before planning a write.
Block a unit on any of these conditions:

- its lexical or resolved path escapes the expected immediate skill root;
- a Git symlink (`120000`), gitlink, filesystem symlink, junction/reparse
  point, special file, or case-fold collision occurs anywhere in the unit;
- `SKILL.md` fails an identity, YAML, BOM, or known host-loadability gate from
  `report/v4`;
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
current ownership. Runtime selection after that transition reads only v2/v4
candidates; it never dual-reads v1.

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

## Intent records

Every managed skill source contains valid `bridge-intent.yaml`, and the skill
projection copies it byte-for-byte. Entry/rule units carry the strict
source-tree/v4 `bridge:intent` HTML comments; their renderer strips those
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
  spans and list every non-whitespace span in the sync-plan/v2 Adoption
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

Every write begins with the complete `sync-plan/v2` pre-write report. Include:

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
`sync-plan/v2`; reconciliation may not introduce an unregistered prose-only
blocker. In particular `mode-limited`, `sensitive-or-generated-blocked`, and
`unsafe-tree-entry` block writes just as strictly as activation, marker,
baseline, covenant, source-schema, migration, and conditional-capability
failures.

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
`confirmed` / `planned`; it must never digest a post-write result or
expectation. The journal binds:

- `operation-id`, resolved repository path, starting `HEAD` object id (or
  `unborn`), and SHA-256 of the exact confirmed sync-plan/v2 bytes;
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
4. run scoped `git status --short`, scoped `git diff`, and
   `git diff --check`; and
5. emit the post-write plan with per-unit outcomes and remaining warnings.

When execution actually writes root `AGENTS.md`, or a failed/partial host call
means that carrier may have been written, attach `restart-may-be-required` to
only the affected entry/rule rows and instruct the user to start a new Codex
run/session before testing activation. A pre-write blocker, deferred or
not-selected closure, source-only operation that cannot touch the carrier, or
failed operation proven to retain the exact preimage receives no restart
annotation. Do not rely on current-main environment-selection refresh
behavior as a public reload contract.

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
