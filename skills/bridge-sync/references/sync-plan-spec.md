# Bridge sync plan specification

Spec version: sync-plan/v2.

This file defines the deterministic M3 pre-write plan and post-write result
for [`reconciliation/v2`](reconciliation-spec.md). It covers skills plus
entry/rule managed blocks while keeping one write authority and one
versioned write-protocol vocabulary. Minimal normative fragments live in
[`canonical-plan-cases.md`](canonical-plan-cases.md); they illustrate this
specification and do not relax its complete-document requirements.

## Contract header

Every document uses:

```markdown
# Bridge Sync Plan

- project: <directory name of repository root>
- scan root: <path as invoked>
- date: <YYYY-MM-DD>
- spec: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: <pre-write|post-write>
- onboarding: <onboarded|bootstrap-required|blocked>
- authorization: <required|confirmed|not-applicable>

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
<rows>

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
<rows>

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
<rows, or "- (none)">

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
<rows, or "- (none)">

## Warnings

<warning lines or "- (none)">

## Migration decisions

<the exact table below, or "- (none)">

## Migration candidates

<the exact table below, or "- (none)">

## Adoption decisions

<the exact table below, or "- (none)">

## Evidence and notes

<free-form>
```

Unit ids are `onboarding/covenant`, `onboarding/agents-md`, `entry`,
`rules/<source-relative-id>`, or `skills/<name>`. Sort rows byte-wise by unit.
`baseline` is `-` or the full lowercase 40- or 64-hex Git object id. Empty
cells use `-`. Cell padding and annotation sorting follow `report/v4`.
Serialize only affected or explicitly request-scoped units. Repository-wide
preflight evidence does not require a row for every inspected carrier, and an
`onboarded` header does not automatically add an unchanged covenant row.

Every unit row binds exactly one closure and repeats that closure's
`selection` and `authorization`; disagreement is invalid. Closed selection
tokens are `selected` and `not-selected`. Closed authorization tokens are
`required`, `confirmed`, and `not-applicable`. The header authorization is
derived: `required` when any selected mutating closure is not confirmed,
`confirmed` when all selected mutating closures are confirmed, and
`not-applicable` when no selected closure can mutate.

`phase` is determined by operation lifecycle, not by whether the document is
the last report the agent intends to emit. Use `pre-write` until the bound live
operation enters lifecycle `executing`. This includes blocked, deferred,
not-selected, zero-write, confirmation-pending, confirmation-complete, and
journal-`prepared` documents. Once the operation enters `executing`, every
subsequent document for that operation is `post-write`, including `failed`,
`partial`, `compensated`, and `not-attempted` results even when no mutation
survives. A plan that never enters execution never becomes `post-write`.

The validation context also names whether the document is an
operation-scoped result or an independent fresh scan. A verified or closed
empty-bootstrap result remains bound to the scan in which both covenant
carriers were absent: its applied row stays
`bootstrap-required` / `no-baseline` / `create` / `applied`, even when both
successful creates are still untracked. It emits both
`untracked-files-included` lines but no `covenant-anchor-anomaly`. Once that
journal is closed, a later invocation begins a new `prepared` lifecycle. If
both exact carriers remain untracked, the independent plan is `pre-write` /
`blocked` and uses the zero-write covenant blocker shape below. A caller may
not relabel one context as the other.

Stable closure ids are:

- `closure/migration` for the complete contract-migration set;
- otherwise `closure/agents-md` for all selected operations that may change
  root `AGENTS.md` and their coupled source paths;
- `closure/skill/<name>` for an ordinary skill closure;
- `closure/skill-rename/<old-name>--to--<new-name>` for a skill rename; and
- `closure/decision/<unit>` for a zero-write, blocked, deferred, unchanged, or
  explicitly not-selected unit that belongs to no physical write closure.

The migration rule has precedence over every other id rule. Closure rows sort
byte-wise by id. `members` is the byte-wise sorted unit list joined by `; `;
`depends on` is the sorted closure-id list joined by `; `, or `-`. A selected
closure may depend only on selected closures. Its authorization and outcome
apply to the complete member set. A not-selected closure has authorization
`not-applicable` and outcome `not-selected`. A selected zero-write closure
also has authorization `not-applicable`; a selected mutating closure is
`required` until the exact serialized closure is confirmed, then `confirmed`.

`Capability profiles` is the closed `capability-profile/v1` binding schema.
`binding` is `capability/<positive-decimal>`, allocated contiguously in first
use order. `profile` is exactly `capability-profile/v1`. `host` is
`claude-code`, `codex`, `other`, or `unresolved`; `platform` is `linux`,
`macos`, `windows`, `other`, or `unresolved`. `host version` and
`tool surface` are exact observed ASCII identifiers or `unresolved`.
`filesystem assumptions` is `unresolved` or a byte-wise sorted `; `-joined
list of versioned ASCII assumption tokens. Rows use numeric binding-suffix
order, not byte-wise binding-string order. Allocate bindings contiguously in
first-use order while scanning Write capabilities by numeric step, forward
binding before inverse binding. Thus ten rows serialize `capability/1`
through `capability/10`, never `capability/1`, `capability/10`,
`capability/2`. Every row must be cited by at least one forward or inverse
operation; no gap or unreferenced row is allowed.

A row records admitted evidence; it does not create capability. Generic
PowerShell/.NET, Claude Code `Edit`/`Write`, Codex `apply_patch`, and Python
file/path I/O serialize no strict protocol without the explicit versioned
adapter attestation required by reconciliation/v2. A profile sourced from
`write-capability-fixture/v1` is valid only for the one fixture operation
whose lease-bound materialization marker and capability-document hashes were
formally validated. It uses the profile fields in that document, never the
agent's inferred host fields, and is invalid in every non-fixture plan.

`Write capabilities` serializes the physical operations of selected mutating
closures in exact execution order. `step` is a one-based decimal integer with
no gaps. `path` is repository-relative, slash-separated, and subject to the
same path-safety rules as the unit. `operation` is `replace`, `create`, or
`delete`. `protocol` and `inverse protocol` use the closed registry below.
`binding` and `inverse binding` cite Capability profiles rows. A strict or
guarded protocol requires a binding; `unavailable` requires `-`. The inverse
is resolved before the first mutation; it is `unavailable` when no strict
compensation primitive is attested. A pre-write blocker may retain an
`unavailable` forward protocol row to expose the missing capability. A
document with no selected mutating intent emits `- (none)` for both tables;
a capability-blocked intent may have `- (none)` profiles plus one or more
`unavailable` Write capabilities rows.

## State registry

| Token | Meaning |
|---|---|
| `unchanged` | Current managed carriers are equal and require no write |
| `source-only` | Only source differs from the unique baseline |
| `projection-only` | Only projection differs from the unique baseline |
| `both-changed` | Both differ from the same baseline and current trees differ |
| `intent-missing` | Payload carriers are converged but a required semantic source intent record is absent |
| `no-baseline` | No current-contract managed baseline is provable |
| `contract-migration` | The exact archived-v1 pair, or a current pair without its reachable closed-set transition, requires explicit migration completion |
| `offboarding` | Both covenant halves disappeared after provable onboarding |
| `blocked` | Safety, malformed ownership, or ambiguous evidence prevents a write |

## Action registry

| Token | Meaning |
|---|---|
| `create` | Create a missing covenant pair, canonical source, or projection under the confirmed onboarding decision |
| `repair` | Resolve safety/trackability or restore a partial, malformed, modified, or incoherent covenant pair before tuple migration |
| `restore` | Restore both current covenant halves after an unconfirmed historical disappearance |
| `update` | Propagate a source-only semantic change or add a required source intent record |
| `reproject` | User confirms source should repair an accidental/mechanical projection change |
| `adopt` | Copy a projection-only managed intent to source and append its intent record |
| `conflict` | Both sides carry different new intent; write neither |
| `delete` | Converge a proven managed deletion in the stated direction |
| `rename` | Rename an old/new managed unit through one dependency closure and ordered strict path operations |
| `annex-or-keep` | Unknown occupancy requires an explicit ownership decision |
| `annex` | User explicitly establishes ownership using the recorded authority |
| `keep` | Leave unknown occupancy untouched for this run and unresolved |
| `migrate` | Replace archived v1 and establish one closed current-tuple transition for every carried legacy-owned unit |
| `offboard` | Explicitly remove the Bridge covenant and managed ownership |
| `resolve-blocker` | No write until the named safety/evidence problem is resolved |
| `unchanged` | No write |

## Direction registry

`-`, `source-to-projection`, `projection-to-source`, and `user-decision`.
Delete and rename rows use the direction of the intent. A conflict,
annex-or-keep, repair, restore, migration choice, or unresolved offboarding
uses `user-decision`. `resolve-blocker` also always uses `user-decision`;
`-` would conceal the explicit resolution needed before a fresh plan.

A rename closure contains both sides. Its destination row has baseline `-`
and state `no-baseline`; every old/source row has a proven baseline and state
`source-only`. A destination baseline is not inferred from rename similarity.

## Outcome registry

| Token | Phase | Meaning |
|---|---|---|
| `planned` | pre-write | Authorized action has not run yet |
| `applied` | post-write | Write and all verification passed |
| `unchanged` | either | No write was needed |
| `not-selected` | either | The serialized partial-batch plan explicitly excludes this closure from execution |
| `deferred` | either | A confirmed `keep` or explicit selected zero-write deferral remains unresolved |
| `blocked` | either | Safety/evidence gate prevented the write |
| `failed` | post-write | Execution failed before mutation and the closure is proven unchanged |
| `compensated` | post-write | Mutation began, failed, and automatic operation-local compensation restored and verified the complete pre-write closure |
| `partial` | post-write | Mutation began and the complete applied or pre-write closure cannot be proven after compensation stopped or failed |
| `not-attempted` | post-write | The closure did not run because an earlier closure failed/was partial or a dependency closure did not execute |
| `rolled-back` | post-write | A separately planned and confirmed reverse operation reconstructed from current bytes plus reachable Git was verified |

Pre-write actions that could mutate use `planned` only when their closure is
`selected`; a `not-selected` closure and all its unit rows use
`not-selected`. The per-closure authorization is authoritative and the header
is its derived summary. Pending Codex-start segmentation and an unresolved
`annex-or-keep` target use a not-selected decision closure. A `both-changed`
conflict is instead a selected, `required`, zero-write decision closure with
outcome `deferred` and `decision-required`. A semantic-review adoption with
exact proposed source bytes is a selected physical closure with
`required` / `planned`, plus `intent-required` and
`semantic-review-required`. A confirmed zero-write
`keep` or explicitly deferred resolution uses a selected zero-write decision
closure with authorization `not-applicable` and outcome `deferred`. `keep`
never uses `unchanged`. `resolve-blocker` uses `blocked`. `blocked` means a
pre-write safety or evidence gate selected the closure; `failed` means
execution was attempted but no mutation survived; `not-attempted` means
execution never began.
`compensated` is automatic failure handling already authorized by the
confirmed plan in the same live operation. `rolled-back` is a later,
separately confirmed operation and never relies on discovering an old
temporary journal.

## Write protocol registry

| Token | Position | Meaning |
|---|---|---|
| `strict-replace/v1` | forward or inverse | One attested operation binds replacement to the complete expected existing byte image |
| `strict-create/v1` | forward or inverse | One attested operation creates only when the final path is absent |
| `strict-delete/v1` | forward or inverse | One attested operation binds removal to the complete expected existing byte image |
| `guarded-patch/v1` | forward only | One exact-literal unique-region replacement surrounded by complete-file preflight and postverification; explicitly not CAS |
| `unavailable` | forward or inverse | The capability adapter cannot attest an allowed protocol for this operation |

Capability resolution uses `capability-profile/v1` and binds host, host
version, tool surface, platform, and filesystem assumptions. Every capability
defaults to unavailable. A changed or unresolved binding invalidates the
profile. Tool names, a planning re-read, user confirmation, an advisory lock,
or an atomic rename alone cannot upgrade a protocol token.

Fixture-only root-child fault mutation has an additional platform gate. A
retained POSIX leaf handle, inode identity, and link count do not prove that
the current child name still resolves to that leaf after same-directory
rename/replacement. Without a mutation-bound current name-to-leaf attestation,
the POSIX case remains declarative-only and `apply-fault` must fail closed
before target mutation. This does not change a Windows binding: its capability
is resolved independently from Windows handle, name, reparse, and filesystem
evidence.

`guarded-patch/v1` is eligible only for replacement of an existing, safe,
byte-round-trippable regular UTF-8 text file with a non-empty preimage. The
plan derives one non-empty contiguous old region that covers every changed
Unicode code point, extends it only at code-point boundaries until it is
unique in the complete preimage, and records its byte offset and exact
old/new UTF-8 values. Complete pre/post images and both regions decode as
strict UTF-8; neither the offset nor the old-region end may split a multi-byte
code point. The adapter must perform one exact-literal, unique-match,
non-regex, non-fuzzy, non-`replace_all` replacement. The complete preimage
must match immediately before the call, and the complete postimage must match
immediately after it. These checks filter and detect races; they do not close
the race inside the host call.

Create accepts only `strict-create/v1`; delete accepts only
`strict-delete/v1`. Rename is serialized as destination/source path
operations and requires strict protocols for every step. Guarded patch is
never an inverse protocol. Automatic compensation is attempted only when
every required inverse row is strict; otherwise the compensation attempt is
blocked and an unexpected intermediate value yields `partial`.

## Tier and annotation registries

`tier` is `native` for managed skill rows, `structural` for entry and
unscoped-rule rows, `semantic` for valid path-scoped rules, and `-` for
onboarding or unresolved unmanaged rows.

Formal validation derives this value from the authenticated public replay
input and render documents. It does not trust the Units cell or consult an
expectation. It uses source-tree/v4's exact raw-byte frontmatter recognizer,
not a partial YAML parser. The proposed/rendered source takes precedence over
the input source so a confirmed scope conversion is classified by its result;
source deletion falls back to the authenticated input source or exact `pv2`
projection. Missing or duplicate fallback evidence is invalid. A rule that
declares an invalid scope remains a blocked semantic candidate; it is never
reclassified as an unscoped structural rule. An unresolved unmanaged skill
using `annex-or-keep` or `keep` has tier `-`; other managed or resolved skill
rows use `native`.

Annotations are sorted byte-wise and joined by `; `:

- `behavior-degraded`
- `decision-required`
- `intent-required`
- `live-activation-unknown`
- `migration-transition-required`
- `restart-may-be-required`
- `semantic-review-required`

`live-activation-unknown` is neutral: it is not a trust state. A pre-write
plan never carries it. In a post-write result, attach it only to a skill row
whose `.agents/skills/<name>/` carrier was written or may have been written,
or to an entry/rule row whose root `AGENTS.md` carrier was written or may have
been written. Do not attach it when execution never began, the row was
blocked/deferred/not-selected, only a canonical source path could be touched,
or complete-value verification proves the carrier retained its preimage.
`migration-transition-required` is attached to `onboarding/covenant` and every
carried migration row until the closed v1-to-v2 transition commit is reachable.
A released migration row has Units baseline `-` and no transition annotation;
its legacy oid remains evidence only in Migration decisions/candidates.
`restart-may-be-required` follows the same post-write carrier-touch predicate:
attach it only when a Codex skill carrier, or root `AGENTS.md` for the affected
entry/rule, was written or may have been written. A pre-write blocker and
every other no-carrier-write case receive neither restart nor live-activation
annotations. For each affected row, Evidence and notes must say: “Start a new
Codex run/session before testing the updated project instructions or skill.”
This is a required activation step for M3 outcomes, not a claim that
current-main environment refresh will reload the carrier.

## Warning registry

Each line is `- <token>: <path>` followed only when allowed by the closed
detail table below by one parenthesized detail, and lines sort byte-wise as
complete lines. `<path>` is `.` for repository-graph, operation, or closure
evidence that has no single physical carrier; otherwise it is the exact
slash-separated repository-relative **file** path that carries the evidence.
Do not serialize an absolute path, unit id, closure id, or directory path in
this field.

| Token | Condition |
|---|---|
| `active-shared-import` | An entry/rule shared region contains an active Claude import |
| `agents-md-budget-disabled` | Effective Codex project-document budget is zero |
| `agents-md-budget-exceeded` | Exact planned root `AGENTS.md` bytes exceed the positive budget |
| `agents-md-near-budget` | Exact planned root `AGENTS.md` bytes are at least seven eighths of the positive budget |
| `ambiguous-baseline` | Reachable current-contract history has multiple incomparable ancestry-maximal ownership candidates |
| `authorization-incomplete` | A selected mutating closure is not `confirmed` |
| `closure-dependency-unsatisfied` | A selected closure depends on a closure that is not selected and confirmed |
| `codex-activation-unresolved` | Effective Codex configuration or an exact activation carrier cannot be resolved safely |
| `codex-root-unresolved` | Root-marker evidence does not prove the intended Codex project root |
| `conditional-write-unavailable` | A forward or mandatory rename/rollback/compensation operation whose policy requires strict semantics has no attested strict protocol |
| `covenant-anchor-anomaly` | Covenant path/type/tracking, pair coherence, template, or version safety is unresolved |
| `dual-project-entry` | Both supported Claude project-entry files exist |
| `entry-rule-source-anomaly` | An entry/rule source has unsafe type/path, BOM, or invalid/unknown/misplaced v4 control metadata |
| `fallback-shadow` | Creating root `AGENTS.md` would shadow an active configured fallback |
| `guarded-patch-non-cas` | A selected replacement uses `guarded-patch/v1`, whose preflight and postverification leave a residual race |
| `guarded-patch-unavailable` | An existing-file replacement has neither an attested strict protocol nor an eligible exact-region guarded protocol |
| `ignored-files-excluded` | Relevant ignored paths were excluded and not read or copied |
| `ignored-required-input` | A required unit input is ignored and therefore cannot participate safely |
| `invalid-rule-paths` | A `paths` list is invalid, no-op, duplicate, or over its expansion budget |
| `legacy-managed-mode` | A removed v3 `mode=` marker requires explicit migration/repair |
| `manual-zone-guarded` | An `AGENTS.md` guarded patch includes all non-selected spans in the complete pre/post images but cannot prove absence of a lost concurrent edit |
| `manual-zone-preserved` | An `AGENTS.md` write protects all non-selected byte spans in one full-file exact-precondition conditional edit |
| `marker-anomaly` | Marker structure prevents a trustworthy managed/manual region map |
| `migration-closure-incomplete` | A reachable-v1 proven managed unit is absent from the closed migration set or lacks a confirmed repair/release decision |
| `migration-transition-uncommitted` | Desired v2/v4 bytes exist but no reachable Git transition commit establishes the complete carried set |
| `mode-limited` | A proposed write requires an executable/worktree-only mode that Git/filesystem cannot prove or realize on the target |
| `sensitive-or-generated-blocked` | Suspected secret, credential, private key, or generated payload blocks copying |
| `skill-loadability-blocked` | A skill fails a report/v4 identity, YAML, BOM, or definite host-loadability gate |
| `surface-shadowed` | Root `AGENTS.override.md` shadows the projection carrier |
| `strict-compensation-unavailable` | At least one selected forward operation has no attested strict inverse; Bridge will not attempt guarded compensation |
| `unrelated-dirty-preserved` | The repository has out-of-scope dirty changes that the plan preserves |
| `unsafe-tree-entry` | Symlink, reparse point, gitlink, special file, case collision, or path escape blocks a unit |
| `untracked-files-included` | Relevant non-ignored untracked files participate in the current snapshot and plan |
| `validator-profile-mismatch` | Current Codex validator profile rejects otherwise separately classified content |

### Warning detail grammar

Detail is closed. A token absent from this table must omit it.

| Token | Required detail grammar |
|---|---|
| `active-shared-import` | `(<import-token>)`, where the token matches `@[A-Za-z0-9_./~-]+` |
| `agents-md-budget-exceeded` | `(<n> bytes of <B>)`, with canonical non-negative decimal `n`, canonical positive decimal `B`, and `n > B` |
| `agents-md-near-budget` | `(<n> bytes of <B>)`, with canonical non-negative decimal `n`, canonical positive decimal `B`, `n >= floor(7 * B / 8)`, and `n <= B` |
| `codex-activation-unresolved` | `(<reason>)`, where reason is `config-unresolved`, `override-carrier-unsafe`, `agents-carrier-unsafe`, `fallback-carrier-unsafe`, `fallback-selection-unknown`, or `budget-unknown` |
| `codex-root-unresolved` | `(<reason>)`, where reason is `effective-root-unknown`, `empty-markers`, or `root-marker-excluded` |
| `covenant-anchor-anomaly` | `(<reason>)`, where reason is `partial`, `untracked`, `malformed`, `modified`, or `version-mismatch` |
| `invalid-rule-paths` | `(<reason>)`, where reason is `schema`, `empty`, `unsafe`, `invalid-bracket`, `no-op-universal`, `duplicate`, `expansion-count`, `expansion-bytes`, or `expansion-unproved` |
| `legacy-managed-mode` | `(line <n>)`, where `n` is a canonical positive decimal source-line number |
| `marker-anomaly` | `(line <n>)`, where `n` is a canonical positive decimal carrier-line number |
| `mode-limited` | `(<reason>)`, where reason is `explicit-executable-unrealizable`, `worktree-mode-unobservable`, or `target-mode-unpreservable` |

Warnings never grant write authority. `agents-md-near-budget`,
`guarded-patch-non-cas`, `manual-zone-guarded`, `manual-zone-preserved`, and
`strict-compensation-unavailable` require explicit acknowledgement but are
not forward-apply blockers. The absence of a strict inverse blocks an
automatic compensation attempt, not an explicitly confirmed guarded forward
operation. `ignored-files-excluded`, `unrelated-dirty-preserved`,
`untracked-files-included`, and `validator-profile-mismatch` are informational
unless a separate blocker row below applies. Evidence and notes may cite
commands, intent records, commit ids, operation-local manual-zone digests, and
user decisions; it is free-form and not a durable baseline.

Emit `untracked-files-included` once for every relevant non-ignored
untracked file in every phase in which it remains relevant and untracked.
Blocked, deferred, unchanged, not-selected, or unauthorized status does not
suppress the line. Its warning path is the exact file path; `.` is invalid
for this token.

Every context-derived warning is serialized once per exact graph or path
fact, not once per token. For example, three guarded paths require three
`guarded-patch-non-cas` lines, and three available forward operations whose
inverse is unavailable require three
`strict-compensation-unavailable` lines. Duplicate lines are invalid.
Sort the complete warning lines byte-wise after rendering the token, exact
path, and optional closed detail; token-only sorting or token-only
cardinality is insufficient.

For an independent scan whose two exact current covenant carriers are both
untracked, also emit `covenant-anchor-anomaly` with reason `(untracked)` once
for each carrier. Serialize one selected `onboarding/covenant` row in
`closure/decision/onboarding/covenant` with baseline and annotations `-`,
state `blocked`, action `resolve-blocker`, direction `user-decision`,
authorization `not-applicable`, and outcome `blocked`; both capability
sections are none. This fresh-scan rule does not retroactively alter the
operation-scoped applied bootstrap result above.

## Closed apply-blocker registry

Apply is forbidden when any row matches. Every blocker in reconciliation/v2
must map to this table; adding a blocker requires a spec-version change.

| Gate | Trigger | Serialized evidence |
|---|---|---|
| authorization | selected mutating closure authorization is not `confirmed` | `authorization-incomplete` plus closure authorization |
| dependency | selected closure dependency is not selected and confirmed | `closure-dependency-unsatisfied` plus Closures row |
| covenant | covenant path/type/tracking, pair coherence, template, or version is unresolved | `covenant-anchor-anomaly` |
| activation | effective config/carrier is unknown, root is unproven, override/fallback shadows, budget is zero/exceeded | one or more of `codex-activation-unresolved`, `codex-root-unresolved`, `surface-shadowed`, `fallback-shadow`, `agents-md-budget-disabled`, `agents-md-budget-exceeded` |
| entry/rule source | dual entry, active import, invalid paths, legacy mode, unsafe/control anomaly, or marker map failure | one or more of `dual-project-entry`, `active-shared-import`, `invalid-rule-paths`, `legacy-managed-mode`, `entry-rule-source-anomaly`, `marker-anomaly` |
| history | ownership candidates are ambiguous | `ambiguous-baseline` |
| migration closure | legacy set/decision is incomplete | `migration-closure-incomplete` |
| migration finalization | desired current bytes are already prepared but the closed transition commit is not reachable | `migration-transition-uncommitted`; block ordinary Bridge writes and synchronized/ownership claims, but wait for the external user commit rather than blocking the already-completed migration byte preparation |
| tree safety | symlink/reparse/gitlink/special file, case collision, path escape, or unsafe target | `unsafe-tree-entry` |
| ignored required input | a required input is excluded by ignore rules | `ignored-required-input` |
| skill loadability | report/v4 definite skill-load gate fails | `skill-loadability-blocked` |
| sensitive/generated | content must not be copied | `sensitive-or-generated-blocked` |
| mode preservation | selected direction requires an unrealizable/unprovable mode | `mode-limited` |
| write capability | a strict-required forward or mandatory rename/rollback/compensation operation is unavailable, or an eligible existing-file replacement has neither a strict nor guarded protocol | `conditional-write-unavailable` for strict-required operations; otherwise `guarded-patch-unavailable`, plus the matching `unavailable` Write capabilities row |
| unresolved unit decision | conflict, annex/replace, release, destructive, migration, semantic-review, or offboarding decision is pending | the matching closed decision shape below; never prose-only state |

## Closed decision serialization

Decision state is serialized in rows, never only in prose. Apply the first
matching row:

| Decision state | Closure | selection | authorization | outcome | Required annotations |
|---|---|---|---|---|---|
| Codex onboarding segmentation or authority target pending | `closure/decision/onboarding/agents-md` | `not-selected` | `not-applicable` | `not-selected` | `decision-required` |
| two-sided `both-changed` conflict | `closure/decision/<unit>` | `selected` | `required` | `deferred` | `decision-required` |
| exact semantic-review source candidate awaits confirmation | physical closure selected by the stable-id rules | `selected` | `required` | `planned` | `intent-required; semantic-review-required` |
| choice confirmed but required source intent or motivation is incomplete | physical closure selected by the stable-id rules | `selected` | `required` | `planned` | `intent-required` |
| confirmed `keep` or explicit zero-write deferral | `closure/decision/<unit>` | `selected` | `not-applicable` | `deferred` | `-` |
| choice and all required intent are satisfied by an exact mutating plan | physical closure selected by the stable-id rules | `selected` | `required` until exact confirmation, then `confirmed` | `planned` | remove satisfied `decision-required`, `semantic-review-required`, and `intent-required` |

The unit row repeats the closure's selection, authorization, and outcome.
Confirmation never leaves a mutating row in its decision closure. Conversely,
an annotation is not removed merely because the user discussed the choice:
the exact serialized disposition, destination, motivation, source bytes, and
rerender must all be complete.

### Pending and confirmed Codex onboarding

For a pending shared-content decision, serialize exactly:

| Field | Value |
|---|---|
| unit | `onboarding/agents-md` |
| closure | `closure/decision/onboarding/agents-md` |
| state / action / direction | `no-baseline` / `annex-or-keep` / `user-decision` |
| selection / authorization / outcome | `not-selected` / `not-applicable` / `not-selected` |
| tier | `-` |
| annotations | `decision-required` |

Before a shared destination is confirmed there is no source intent target, so
the onboarding row never carries `intent-required`. After a `shared-entry`
destination is selected, collect its required initial intent and serialize
the resulting exact source candidate in the physical closure. Once both the
decision and required initial intent are confirmed,
replace that decision row with unit `entry` in `closure/agents-md`; use
state `no-baseline`, action `annex`, direction `projection-to-source`, tier
`structural`, and selected `required`/`planned` or
`confirmed`/`planned`. A confirmed `shared-rule` similarly becomes
`rules/<id>` with state `no-baseline`, action `annex`, direction
`projection-to-source`, and its structural or semantic tier in
`closure/agents-md`.
Remove satisfied decision, semantic-review, and intent annotations from those
rows. The Adoption decisions table retains the confirmed segment evidence;
the obsolete pending unit and decision closure do not remain beside the
physical entry/rule closure.

## Live operation journal binding

The execution journal is operation-local authorization evidence, not a
baseline or a future rollback store. It records:

- one opaque `operation-id`, resolved repository path, starting `HEAD` oid or
  `unborn`, and SHA-256 of the exact independently serialized, confirmed
  `phase: pre-write` plan document;
- the exact selected closure ids, dependencies, selection, and authorization;
- for each path operation, its step, closure, operation kind, selected
  protocol and binding, inverse protocol and binding, exact pre-value,
  intended post-value, and exact observed applied value;
- for `guarded-patch/v1`, the region byte offset and exact old/new region; and
- lifecycle `prepared`, `executing`, `compensating`, `verified`, `partial`, or
  `closed`.

When any profile comes from `write-capability-fixture/v1`, the journal also
binds the materialization lease hash, marker path and SHA-256, capability
document path and SHA-256, suite, scenario, replay-input branch, resolved root,
and marker baseline. Missing or mismatched fixture fields invalidate the
profile and the journal before execution.

The bound document must have header authorization `confirmed`; every selected
mutating unit and closure is `confirmed` / `planned`. A post-write result,
expectation document, required authorization, or non-planned mutation cannot
seed a journal, and any byte change invalidates the plan digest.

Allocate the journal exclusively in an access-safe operation-id lease
directory that is a no-follow, non-reparse direct child of the OS temporary
directory and resolves outside the repository. The active process retains the
exact newly allocated path. Never scan a broad temporary directory to find a
journal. Cleanup validates that exact path, operation id, repository, plain
file/directory types, and closed lifecycle, then removes only the exact
journal and exact empty lease; sibling leases are never enumerated or removed.
Automatic compensation is authorized only in that same live operation while
this binding remains open. After `applied`, close it. Any later/cross-session
reverse operation needs a new plan and confirmation reconstructed from
current bytes plus reachable Git. Confirmation authorizes the new plan but
cannot replace missing ownership, baseline, or prior bytes with arbitrary
evidence. If Git cannot reconstruct the exact prior value, rollback is
unavailable; annexation or a destructive decision remains a separately
classified action under its normal gates.

## Contract-migration decisions

Every `contract-migration` plan includes this exact table:

```markdown
| unit | legacy baseline | current relation | disposition | decision |
|---|---|---|---|---|
```

It is followed by this independent candidate table:

```markdown
| unit | legacy candidate |
|---|---|
```

Derive the complete legacy-owned set from the reachable v1 DAG before
planning any covenant replacement. Emit exactly one row per proven unit,
sorted byte-wise by unit. Emit one Migration candidates row for every
ancestry-maximal v1 candidate of that unit, sorted byte-wise by
`(unit, legacy candidate)`, with no duplicates. A candidate is its full
lowercase 40- or 64-hex commit object id.

Rows are per legacy managed payload unit. The covenant pair remains in
`closure/migration` and its history is transition evidence, but
`onboarding/covenant` is excluded from both tables. The candidate-table unit
set must equal the Migration decisions unit set after that exclusion.
When a unit has exactly one candidate, `legacy baseline` is that same full oid
and `current relation` is not `ambiguous`. When it has two or more
incomparable candidates, `legacy baseline` is `-`, `current relation` is
`ambiguous`, and every maximal candidate appears in the independent table.
No timestamp, first-parent choice, abbreviated oid, or arbitrary representative
may collapse the set. `current relation` is otherwise `converged`,
`repair-required`, `missing`, or `unsafe`.

A safe unit already satisfying its v4 relation uses `carry-forward` and
`derived`; it cannot silently disappear from the migration. Every other row
starts with disposition `block` and decision `pending`. The user may confirm
`repair-and-carry` or `release`; release must have durable, unambiguous Git
transition evidence and any destructive byte change receives its own explicit
confirmation. Thus `disposition` is `carry-forward`, `repair-and-carry`,
`release`, or `block`, and `decision` is `derived`, `pending`, or `confirmed`.
An `ambiguous` row remains `block` / `pending` until reachable Git supplies an
unambiguous ancestry-maximal result or separately proves one durable
transition that resolves the complete candidate set. Confirmation alone
cannot select or discard an incomparable candidate.

If any row is ambiguous, the complete `closure/migration` remains selected
and blocked. Every member uses Units baseline `-`, state
`contract-migration`, action `resolve-blocker`, direction `user-decision`,
authorization `not-applicable`, and outcome `blocked`. The ambiguous payload
unit carries only `decision-required`; `onboarding/covenant` and each
unambiguously carried payload unit carry `migration-transition-required`.
Unique legacy oids remain in Migration decisions/candidates and are not
promoted to current Units baselines while the version barrier is open.

The migration closure is the covenant pair plus every legacy-owned row:
`carry-forward` and `repair-and-carry` members establish current ownership,
while confirmed `release` members establish its explicit end. A pending/block row emits
`migration-closure-incomplete` and prevents the whole migration. Do not emit
`migration-transition-uncommitted` merely because an old-pair pre-write plan
has not yet prepared the transition bytes. After those bytes are prepared,
the user must record one reachable Git commit whose tree carries the exact
v2/v4 covenant and the complete closed set. Bridge does not commit; until that
commit is reachable, emit `migration-transition-uncommitted`, keep migration
unresolved, and permit no ordinary Bridge write or current-ownership claim.
This is an external finalization wait, not a reason to undo or re-run the
already-applied byte preparation. When no migration is in progress, emit
`- (none)` for both Migration decisions and Migration candidates.

In the post-write migration result, a `carry-forward` or
`repair-and-carry` payload row keeps its unique legacy baseline and
`migration-transition-required`. A `release` payload row has Units baseline
`-` and no migration annotation; its legacy baseline remains only in the
migration evidence tables. After the closed transition commit is reachable,
fresh current-contract selection uses that transition as the baseline for
carried units and omits released units.

## Codex-start adoption decisions

When an existing root `AGENTS.md` has unmanaged content proposed for
onboarding, include this exact table after the Warnings section:

```markdown
| segment | lines | disposition | destination | decision |
|---|---|---|---|---|
```

Segments are contiguous exact source byte spans numbered `segment/1`,
`segment/2`, and so on in file order; `lines` is `<start>-<end>` using
one-based inclusive source lines. `disposition` is `shared-entry`,
`shared-rule`, `manual`, or `discard`. `destination` is `entry`,
`rules/<id>`, or `-`. `decision` is `pending` or `confirmed`.

Every non-whitespace unmanaged byte belongs to exactly one segment. A pending
row uses the pending-onboarding decision shape above:
`onboarding/agents-md`, `closure/decision/onboarding/agents-md`,
`annex-or-keep`, `user-decision`, and
`not-selected` / `not-applicable` / `not-selected`. `discard` is destructive
and needs an explicit confirmed choice. A confirmed shared destination moves
to its `entry` or `rules/<id>` physical closure row and removes annotations
whose decision and intent are satisfied. The evidence section includes the
exact byte-range preview plus the proposed source and deterministic rerender.
When segmentation is not needed, emit `- (none)`. Segment ids are
operation-local review handles, not ownership or baseline metadata.

## Formal validation

Every document must pass a formal `sync-plan/v2` validator before it is shown
for confirmation, used to seed a journal, emitted as a result, or passed to a
fixture comparison. The validator parses the exact independently serialized
bytes; a model review, Markdown renderer, expectation parser, successful
apply, or post-state comparison is not a substitute. On failure, the document
is not a plan: make no write, correct it, serialize fresh bytes, and validate
again.

The validator contract is `sync-plan-validator/v1`. Its result contains the
contract token, exact plan SHA-256, exact validation-context SHA-256, boolean
`pass`, and an ordered list of closed rule identifiers for failures. `pass`
is true only with an empty failure list. Failure identifiers sort byte-wise
and come from this exact registry:

```text
adoption-consistency
decision-transition
document-grammar
fixture-attestation
migration-candidates
phase-lifecycle
unit-closure
warning-grammar
write-capability
```

Any implementation claiming this contract must implement every check below;
a partial parser must use a different name and cannot admit a plan.

### Public diagnostic companion

`sync-plan-diagnostic/v1` is a separate, closed explanation contract. It
accepts exactly the same replay input, worktree, lease, plan bytes, and
operation lifecycle as the validator. It does not alter or extend the
`sync-plan-validator/v1` response. Its top-level fields are exactly:

```text
contract
plan_sha256
context_sha256
failures
diagnostics
```

The two hashes and `failures` repeat the formal validation result.
`diagnostics` is deterministically sorted. Every item has exactly
`kind`, `section`, `token`, `path`, `detail`, `actual_line`,
`required_line`, `actual_count`, and `required_count`, using `null` when a
field is inapplicable. Warning kinds are `missing`, `extra`,
`invalid-order`, `cardinality`, `token`, and `path`. Other formal failures
may be reported only as `generic`; the companion must not invent a private
target plan.

The companion independently derives warning requirements from the installed
public replay commitment, input bytes, live Git tracked/untracked state,
capability operations, render operations, decision facts, temporal context,
and supplied lifecycle. It may not read, accept, or serialize an expectation
id/path/content, a scenario matrix result, planned/post-state alias, golden
plan, or oracle. In particular, a verified or closed, confirmed
`closure/migration` render that exactly matches the live tree while its
transition remains dirty in Git requires
`- migration-transition-uncommitted: .`; the prepared pre-write plan does
not.

The validator is closed and must reject unknown tokens or fields. At minimum
it validates:

1. UTF-8, normalization, complete section order, exact headers, table widths,
   canonical cell padding, row ordering, object-id grammar, and phase/header
   derivation;
2. every state/action/direction/outcome/tier/annotation token, the phase versus
   supplied operation-lifecycle context, post-only carrier annotation timing,
   exact unit tiers derived from authenticated public input/render source
   documents, and the explicit temporal context that distinguishes an
   operation-scoped empty-bootstrap result from an independent
   untracked-carrier scan;
3. unit-to-closure equality, stable closure ids, member/dependency sorting,
   selection, authorization, outcome, dependency satisfaction, and header
   authorization;
4. numeric step order, repository file-path grammar, operation/protocol
   compatibility, capability binding first-use order, inverse rules, and the
   absence of unreferenced profiles;
5. explicit adapter attestation for every strict protocol and the complete
   lease/marker/document hash chain for every
   `write-capability-fixture/v1` profile; when the fixture binds a guarded
   preflight fault, the same validation context also proves the closed replay
   commitment, exact confirmed-plan snapshot, exclusive arm/claim/injected
   receipt chain, retained root/leaf identities, declared injected bytes, and
   complete post-tree before admitting the exact `failed` result. Executable
   target-mutation evidence additionally requires a platform-attested current
   root-child name-to-leaf binding; retained leaf identity alone is
   insufficient on POSIX, where its absence permits only declarative
   validation and requires pre-mutation fail-closed behavior. Windows remains
   governed by its independent platform attestation;
6. the closed warning token, `.`-versus-file path, detail grammar, sorting,
   budget arithmetic, closed reasons, positive line numbers, the complete
   legacy-mode/orphan-marker warning set, fallback blocker scope, and complete
   relevant-untracked warning set supplied by the live scan context in every
   phase, both fresh-scan covenant `(untracked)` anomalies, and absence of
   those anomalies from the same-operation applied bootstrap result;
7. closed decision transitions, including pending onboarding's
   not-selected/not-applicable/not-selected shape with only
   `decision-required`, `both-changed` selected/required/deferred,
   semantic-review source candidates selected/required/planned with
   `intent-required`, and confirmed entry/rule promotion with satisfied
   annotations removed;
8. per-payload-unit migration decisions and candidates, candidate-set
   equality, canonical selected blocked ambiguity, post-migration
   carried/released baseline and annotation state, and exclusion of
   `onboarding/covenant` from the evidence tables; and
9. Adoption decisions order, dispositions, destinations, and consistency with
   the Units and Closures tables, including rejection of
   `onboarding/agents-md` without explicit pending segmentation; plus the
   destination/source baseline-state pair for every rename closure.

Validation receives the exact scan/operation context needed for claims that
cannot be reconstructed from Markdown alone. The temporal distinction is
derived from public starting-tree facts, exact render and capability
operations, live Git tracking state, decision facts, and supplied lifecycle;
it may not read an expectation, scenario result alias, or golden plan to
decide whether a plan is valid. A fixture journal derives its prepared
context and formal result in one attestation over the authenticated public
replay envelope and one alternate index initialized from `HEAD`. A bound
create path that is already present after execution is added intent-to-add in
that alternate index before the live-untracked scan, reconstructing the
prepared view without accepting caller-supplied temporal or untracked fields.
The journal stores the returned context/result and their hashes; validation
recomputes the same attestation and rejects even a self-consistent forged
context plus hashes. Record the validator version, input document
SHA-256, context SHA-256, and PASS result in Evidence and notes. Canonical
accepted and rejected fragments are in
[`canonical-plan-cases.md`](canonical-plan-cases.md).

## Deterministic expectation comparison

A fixture expectation replaces `- spec:` with
`- expectation: sync-plan/v2` and may omit Evidence and notes. Compare after
normalization N from `source-tree/v4`:

1. expectation/spec, contracts, phase, onboarding, and authorization match;
2. the Units header is byte-identical and sorted row multisets are identical;
3. the Closures header is byte-identical and sorted closure row multisets are
   identical, including members, dependencies, selection, authorization, and
   outcome;
4. Capability profiles are both `- (none)` or have byte-identical headers and
   byte-identical complete row sequences in numeric-suffix, first-use binding
   order;
5. Write capabilities are both `- (none)` or have byte-identical headers and
   byte-identical complete row sequences in numeric step order;
6. sorted Warning line multisets are identical;
7. Migration decisions are both `- (none)` or have byte-identical headers and
   byte-identical complete row sequences in byte-wise unit order;
8. Migration candidates are both `- (none)` or have byte-identical headers
   and byte-identical complete row sequences in byte-wise
   `(unit, legacy candidate)` order;
9. Adoption decisions are both `- (none)` or have byte-identical headers and
   byte-identical complete row sequences in normative segment order;
10. project, invoked scan-root spelling, date, and Evidence and notes are
   ignored.

`codex-activation-unresolved`, `codex-root-unresolved`,
`conditional-write-unavailable`, `guarded-patch-unavailable`, and
`mode-limited` may depend on effective host or filesystem evidence. A
deterministic fixture must pin or deliberately exclude those inputs; plan
comparison does not silently remove the warnings.
