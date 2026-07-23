# Bridge skill reconciliation specification

Spec version: reconciliation/v1.

This file defines the M2 write-side contract for project skills. The read-only
carrier vocabulary lives in
[`../../bridge-sentinel/references/report-spec.md`](../../bridge-sentinel/references/report-spec.md);
the source unit and compatibility rules live in
[`../../bridge-sentinel/references/source-tree-spec.md`](../../bridge-sentinel/references/source-tree-spec.md).
Plan serialization lives in [`sync-plan-spec.md`](sync-plan-spec.md).

## Contents

- [Authority and scope](#authority-and-scope)
- [Versioned onboarding covenant](#versioned-onboarding-covenant)
- [Current snapshot](#current-snapshot)
- [Safety gates](#safety-gates)
- [Managed ownership evidence](#managed-ownership-evidence)
- [Baseline selection](#baseline-selection)
- [Reconciliation table](#reconciliation-table)
- [Intent records](#intent-records)
- [Delete and rename](#delete-and-rename)
- [Planning and confirmation](#planning-and-confirmation)
- [Writes, validation, and rollback](#writes-validation-and-rollback)

## Authority and scope

M2 writes only:

- the immutable covenant source at `.claude/rules/bridge-covenant.md`;
- its one managed block in root `AGENTS.md`; and
- immediate skill units rooted at `.claude/skills/<name>/` and
  `.agents/skills/<name>/`.

The covenant pair is a bootstrap infrastructure exception, not general rules
projection. M2 does not project other `CLAUDE.md` or `.claude/rules/` content,
does not install `templates/covenant/hook-intents.md`, does not edit either
hooks surface, does not derive `agents/openai.yaml`, and does not write
`skills.config`.

The source remains canonical after ownership is established, but an edit made
on a proven managed projection is a valid input to adoption. Intent records
are evidence, never ownership by themselves.

## Versioned onboarding covenant

The contract tuple is:

```text
covenant/v1
source-tree/v3
report/v3
reconciliation/v1
sync-plan/v1
```

Bootstrap reads the two exact assets under `templates/covenant/`. It creates
source half and inserts the exact managed block into root `AGENTS.md`.
Existing manual-zone bytes before and after the insertion remain unchanged.
Capture their pre-write bytes and verify them after insertion. Bridge never
stages; a newly created half is not tracked until the user records it in the
index, so the post-write onboarding header must continue to report the
observed blocked/bootstrap state rather than claiming a tracked covenant.

The project is onboarded only when both halves are tracked, schema-valid,
exact-template valid, and version-equal. Apply covenant gates in this order:
carrier path/type safety and trackability, pair structure/template coherence,
then tuple version, then reachable-history state. A later tuple label never
overrides an earlier safety or trackability blocker. Classify the pair with
this table before any skill-unit planning:

| Current pair | Reachable covenant evidence | Plan state | Allowed action | Atomic boundary |
|---|---|---|---|---|
| both halves absent | no prior valid covenant, or a completed explicit offboard is proven | `no-baseline` | `create` | source half + `AGENTS.md` block + preserved manual zone |
| both halves absent | prior valid current tuple and no completed explicit offboard | `offboarding` | explicit `restore` or `offboard` | both halves as one closure + preserved manual zone |
| both halves absent | prior valid older/different tuple and no completed explicit offboard | `contract-migration` | explicit `migrate` or `offboard` | historical pair decision + current pair + preserved manual zone |
| either occupied half has an unsafe path/type, exactly one half exists, or either half is untracked | any, regardless of declared tuple | `blocked` | `repair` with `user-decision` direction | safe, coherent pair + preserved manual zone; no migration in this closure |
| both halves are tracked but either is malformed/modified, or their tuple declarations disagree | any | `blocked` | `repair` with `user-decision` direction | coherent exact pair + preserved manual zone |
| both halves are tracked, mutually coherent, and exact for one recognized older/different tuple | any | `contract-migration` | `migrate` | old exact pair to current exact pair + preserved manual zone |
| both halves are tracked and exact for the current tuple | any | `unchanged` | `unchanged` | no write |

Serialize the plan header as `onboarded` only for the last row,
`bootstrap-required` for the first row, and `blocked` for every repair,
migration, restore, or offboarding decision until its required tracked
postcondition is actually observed.

`repair` first establishes a safe, tracked, mutually coherent exact pair
without interpreting its old tuple as migration permission;
`restore` reverses an unconfirmed disappearance whose reachable history
proves the current tuple; `migrate` crosses a tuple-version barrier; and
`offboard` ends managed ownership. Each operates on the complete pair, never
one half. Repair, restore, migration, and offboarding require a complete plan
and explicit confirmation. An older tuple is never an ordinary unit baseline.

For example, if an untracked source half and its tracked companion both
declare an otherwise exact older tuple, the result is `blocked`/`repair`, not
`contract-migration`/`migrate`. Bridge may plan byte repair but cannot stage
the half; after the user makes the coherent pair tracked, a fresh scan may
select the separate `migrate` closure.

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

Ignored files are not part of the canonical Git tree, never participate in a
baseline, and are never copied. List their paths without content under
`ignored-files-excluded`. If an ignored file is required for the skill, stop
and ask the user to make it an intentional non-ignored source input.

An empty directory contributes nothing. A non-empty target directory without
`SKILL.md`, an apparent manual duplicate, or any other unknown occupancy is
unmanaged and must reach `annex-or-keep`; it is never overwritten.

## Safety gates

Resolve the repository root and every unit root before planning a write.
Block a unit on any of these conditions:

- its lexical or resolved path escapes the expected immediate skill root;
- a Git symlink (`120000`), gitlink, filesystem symlink, junction/reparse
  point, special file, or case-fold collision occurs anywhere in the unit;
- `SKILL.md` fails an identity, YAML, BOM, or known host-loadability gate from
  `report/v3`;
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
canonical source presence, projection path history, an identical complete
Git tree after the transition, and commit/diff evidence consistent with
confirmed create, projection, adoption, or annexation. A newly appended
intent record and commit message may support that conclusion but neither is
sufficient alone. If the evidence admits a plausible unmanaged duplicate,
there is no managed baseline.

Ownership ends only through an explicit delete, rename, replacement,
migration, or offboarding decision. Unknown occupancy never inherits
ownership merely because the project is onboarded.

## Baseline selection

Recompute the baseline independently for each unit on every run. Do not store
hashes, attribution metadata, or a side database.

1. Enumerate commits reachable from `HEAD` only. Other refs, reflogs,
   timestamps, author dates, and commit dates cannot select a baseline.
2. A candidate commit must carry the exact current contract tuple, valid
   ownership evidence for the unit, and source/projection complete Git trees
   with identical relative paths, blob bytes, and representable modes.
3. Candidate `x` is older than candidate `y` when
   `git merge-base --is-ancestor x y` succeeds and the commits differ.
4. Retain ancestry-maximal candidates: candidates with no newer candidate
   descendant in the set.
5. Exactly one maximal candidate is baseline `B`. Zero means `no-baseline`.
   Two or more incomparable maximal candidates mean ambiguous history:
   `blocked`, `decision-required`, and no write for that unit.

This DAG rule handles merged histories without choosing by wall-clock time.
Contract migration is a barrier: a byte-identical unit under another contract
version is not a current baseline.

Compare the current source snapshot `S` and projection snapshot `P` with `B`
as complete trees. Absence is a tree value. Comparison covers relative paths,
raw bytes, and supported Git modes.

## Reconciliation table

Apply the first applicable row after safety, ownership, and baseline checks.

| Baseline | Current relation | State | Proposed action |
|---|---|---|---|
| unique B | S = B and P = B | `unchanged` | `unchanged` |
| unique B | S differs from B; P = B; S exists | `source-only` | `update` |
| unique B | S absent; P = B | `source-only` | `delete` from source to projection |
| unique B | S = B; P differs from B; P exists | `projection-only` | `adopt` |
| unique B | S = B; P absent | `projection-only` | `delete` from projection to source |
| unique B | S and P both differ from B; S = P | `unchanged` | `unchanged`, unless an intent record is required |
| unique B | S and P both differ from B; S != P | `both-changed` | `conflict` |
| none | valid S exists; target path is absent or empty | `no-baseline` | `create` after adding the initial intent record |
| none | any non-empty P exists, including S = P | `no-baseline` | `annex-or-keep` |
| ambiguous | any | `blocked` | `resolve-blocker` |

`source-only`, `projection-only`, and `both-changed` describe deltas from the
same B, not line-diff shape. Only different current trees changed on both
sides are `conflict`. Never perform an automatic three-way merge.

`reproject` is a user-confirmed resolution when source should replace a
projection-side change that the user identifies as accidental or mechanical.
It is not inferred from current two-tree shape. `annex` and `keep` appear only
after the user resolves `annex-or-keep`: annex establishes ownership using a
chosen authority; keep performs no unit write, creates no ignore manifest,
leaves the unit unresolved, and cannot be reported as synchronized. A
same-path kept skill must later be relocated, replaced through an explicit
decision, or abandoned.

## Intent records

Every managed source contains valid `bridge-intent.yaml`, and the projection
copies it byte-for-byte.

Append one `{date, note}` record for:

- initial create/onboarding of a unit;
- explicit annexation or projection-side adoption;
- semantic source updates;
- rename, with old and new names and motivation.

Do not append for `unchanged` or a byte-for-byte `reproject`. If a semantic
payload changed on both sides to the same bytes but lacks a corresponding new
record, the plan adds the record to the source and mechanically reprojects the
whole resulting tree. Obtain or propose the one-line motivation before the
write; never invent ownership from the record.

## Delete and rename

Automatic destructive convergence requires a unique baseline proving that the
affected projection was managed. Without it, deletion is absence and rename
is unknown occupancy, not permission to remove or move anything.

A delete records its direction and motivation in the plan. Because the skill
tree disappears, durable tombstone evidence must be carried by the eventual
user commit/diff (Bridge does not commit) or by an explicit future covenant
mechanism. Warn the user not to lose that evidence.

Rename is one atomic transaction over old and new units. Accept it only when
the user states the rename intent or reliable Git path history establishes
the move; never infer it from similarity scores. Validate the new identity,
append its rename intent record, prove ownership of every old path to be
removed, and require the destination to be absent/empty or explicitly
annexed. If any old/new member conflicts or is blocked, write none of the
rename closure. Atomic means that, at the end of execution, the complete old
and new closure is either the verified planned value or its verified
pre-write value. The confirmed rename plan authorizes automatic failure
compensation for this closure; it does not authorize a later user-requested
rollback. If safe compensation itself becomes impossible, report `partial`
instead of claiming atomic success.

## Planning and confirmation

Every write begins with the complete `sync-plan/v1` pre-write report. Include:

- all affected units, current snapshots, baselines or their absence, actions,
  directions, compatibility annotations, and exact paths;
- every relevant non-ignored untracked path and every excluded ignored path;
- related dirty changes plus a scoped summary of unrelated dirty changes that
  will be preserved;
- covenant/manual-zone impact and all blockers or user decisions.

Decisions are per unit, but physical writes are batched by dependency closure
and shared file: the covenant pair, all `AGENTS.md` block operations, and each
old/new rename pair are indivisible. A conflict or blocker receives zero
writes across its closure. Independent, unambiguous closures may proceed
after the user confirms the full plan; partial-batch execution must be
explicit in that confirmation. Stop at the first failed or partial closure.
Any later closure skipped because of that stop, or any dependent closure that
cannot execute, receives `not-attempted`; it is neither `blocked` nor
`failed`.

Conflict, annexation, replacement, migration, offboarding, and any destructive
choice require an explicit decision. All other writes still require
confirmation of the complete scoped plan. Re-scan if relevant bytes change
between plan and confirmation.

## Writes, validation, and rollback

Use host-native file operations. Before the first mutation in every confirmed
physical closure, create an operation-local journal in a unique, access-safe
OS-temporary directory outside the repository. For every path the closure may
touch, record the exact precondition: existence, entry type, raw bytes for a
regular file, and representable Git mode. Also record the planned value after
each step. The journal is not a durable Bridge baseline and never enters the
repository.

Execute each step as compare-and-swap:

1. immediately before writing, re-read existence, type, bytes, and mode;
2. require them to equal the journaled precondition (or the exact value
   written by the preceding step in this closure);
3. perform only that planned mutation; and
4. re-read and journal the exact value this run wrote.

A mismatch is concurrent or otherwise out-of-plan change. Stop before
overwriting it. Never touch unrelated dirty paths.

After all steps:

1. re-read every affected path;
2. compare source/projection manifests mechanically over path, type, bytes,
   and modes;
3. verify the covenant source, managed block, and preserved manual-zone
   snapshot when covenant work ran;
4. run scoped `git status --short`, scoped `git diff`, and
   `git diff --check`; and
5. emit the post-write plan with per-unit outcomes and remaining warnings.

If a write or verification step fails after mutation begins, the already
confirmed plan automatically authorizes **failure compensation** for that
same closure; do not ask for a second confirmation. Walk journaled mutations
in reverse. Before restoring each path, require its current existence, type,
bytes, and mode to equal the exact value written by this run. Only then
restore the precondition, including prior absence and mode, and verify the
whole closure. Successful compensation yields `compensated`. A failure before
the first mutation, with the closure proven unchanged, yields `failed`.

If a compensation compare-and-swap sees concurrent edits, restoration fails,
or the pre-write closure cannot be proven after compensation, stop without
overwriting the new value and report `partial`. This is the explicit extreme
failure boundary of the atomic protocol; never claim that the closure was
restored. Preserve the scoped evidence and mark dependent or later closures
`not-attempted`.

A user-requested rollback **after** an `applied` result is a separate
operation. It is limited to this run's journaled paths and preconditions,
requires a new complete plan and explicit confirmation, and must
compare-and-swap the current closure against the verified applied value before
restoring anything. After the same validation sequence it receives
`rolled-back`. Never use blanket `git restore`, reset, stash, or cleanup, and
never erase a pre-existing or concurrent user change.
