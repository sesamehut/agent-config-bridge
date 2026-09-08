# Bridge sync plan specification

Spec version: sync-plan/v3.

This file defines the deterministic pre-write plan and post-write result
for [`reconciliation/v3`](reconciliation-spec.md). It covers skills,
entry/rule managed blocks, and hook units on both native hook carriers while
keeping one write authority and one versioned write-protocol vocabulary.
Minimal normative fragments live in
[`canonical-plan-cases.md`](canonical-plan-cases.md); they illustrate this
specification and do not relax its complete-document requirements.

## Contract header

Every document uses:

```markdown
# Bridge Sync Plan

- project: <directory name of repository root>
- scan root: <path as invoked>
- date: <YYYY-MM-DD>
- spec: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
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

## Hook tiers

<the exact table below, or "- (none)">

## Migration decisions

<the exact table below, or "- (none)">

## Migration candidates

<the exact table below, or "- (none)">

## Adoption decisions

<the exact table below, or "- (none)">

## Hook adoption decisions

<the exact table below, or "- (none)">

## Evidence and notes

<free-form>
```

Unit ids are `onboarding/covenant`, `onboarding/agents-md`, `entry`,
`rules/<source-relative-id>`, `skills/<name>`, or `hooks/<entry-id>/<host>`
with `<host>` in `source`, `claude`, or `codex` and `<entry-id>` matching
`[a-z0-9][a-z0-9-]*`. Sort rows byte-wise by unit.
`baseline` is `-` or the full lowercase 40- or 64-hex Git object id. Empty
cells use `-`. Cell padding and annotation sorting follow `report/v5`.
Serialize only affected or explicitly request-scoped units. Repository-wide
preflight evidence does not require a row for every inspected carrier, and an
`onboarded` header does not automatically add an unchanged covenant row.

The Units header stays at eleven columns; a hook row never adds a twelfth.
`report/v5` keys the same hook as `hooks/<entry-id>` with a separate `host`
column and has no row for the `source` host, so the two specifications key
hook rows differently and neither derives the other. Serialize a
`hooks/<entry-id>/source` row only when `.claude/rules/hooks.md` is itself
written by this plan, that is for an `enabled-by` append, an intent record,
an adoption, or a reverse adoption, or when the source unit is itself
blocked. An entry whose source is unchanged and unwritten serializes only its
declared host rows.

Every unit row binds exactly one closure and repeats that closure's
`selection` and `authorization`; disagreement is invalid. Closed selection
tokens are `selected` and `not-selected`. Closed authorization tokens are
`required`, `confirmed`, and `not-applicable`. The header authorization is
derived from the selected mutating closures alone: `required` when any
selected mutating closure carries authorization `required`; `confirmed` when
at least one selected mutating closure exists and none of them carries
`required`; and `not-applicable` when no selected closure can mutate. A
scoped-blocked closure (`selected` / `not-applicable` / `blocked`) is still a
selected mutating closure, so a plan whose only mutating closure is
scoped-blocked derives `confirmed` although the plan writes nothing.

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
- `closure/skill-rename/<old-name>--to--<new-name>` for a skill rename;
- `closure/hooks/source` for all selected changes to `.claude/rules/hooks.md`;
- `closure/hooks/claude` for all selected changes to the Claude hook carrier
  `.claude/settings.json`;
- `closure/hooks/codex` for all selected changes to the Codex hook carrier
  `.codex/hooks.json`;
- `closure/decision/hooks/<entry-id>` for the zero-write hook rows of one
  entry; and
- `closure/decision/<unit>` for a zero-write, blocked, deferred, unchanged, or
  explicitly not-selected unit that belongs to no physical write closure.

A degraded Codex hook block in root `AGENTS.md` is an ordinary member of the
existing `closure/agents-md`; hooks introduce no separate prose-carrier
closure id. `closure/decision/hooks/<entry-id>` is an explicit documented
exception to the `closure/decision/<unit>` rule so that an entry's two host
rows never split across two decision closures.

`closure/hooks/claude`, `closure/hooks/codex`, and `closure/agents-md` each
depend on `closure/hooks/source` when it is selected. Hook carrier closures
never depend on one another and never on `closure/agents-md`, because
deferring a prose block must not make an executable carrier unexecutable.
Source-first and carrier-last is enforced by step order instead:
`.claude/rules/hooks.md`, then `AGENTS.md`, then `.claude/settings.json`,
then `.codex/hooks.json`.

The migration rule has precedence over every other id rule. Closure rows sort
byte-wise by id. `members` is the byte-wise sorted unit list joined by `; `;
`depends on` is the sorted closure-id list joined by `; `, or `-`. A selected
closure may depend only on selected closures. Its authorization and outcome
apply to the complete member set. A not-selected closure has authorization
`not-applicable` and outcome `not-selected`. A selected zero-write closure
also has authorization `not-applicable`; a selected mutating closure is
`required` until the exact serialized closure is confirmed, then `confirmed`.
The single exception is a scoped-blocked mutating closure, which carries
authorization `not-applicable` with outcome `blocked` because nothing in it
can be executed.

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
adapter attestation required by reconciliation/v3. A profile sourced from
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
| `declared-unsynced` | A hook target declares `surface: none`, so this host has no counterpart to converge |
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
| `opt-in-or-skip` | A `gate` or `side-effect` hook entry with `enabled: true` has no covering `enabled-by` record; the user records the dated opt-in in the source or skips the entry |
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

For a hooks carrier (`.claude/settings.json` or `.codex/hooks.json`) the
postimage MUST be produced by `json-owned-span/v1` composition: the exact
preimage with only the owned `(event, effective matcher)` group spans edited
and only the located insertion points filled. A postimage produced by parsing
the document and reserializing it is invalid even when it is semantically
equal, and is rejected by the `hooks-carrier-composition` validator check.
`json-owned-span/v1` is a postimage-derivation rule, not a capability claim:
it mints no protocol token and supplies no attestation.

A hooks carrier is eligible only when it also parses as a JSON object under a
strict parser with no duplicate object key anywhere and no node outside the
closed hooks shape. A duplicate key makes span-to-value correspondence
non-unique, and a bridge that guesses which duplicate it owns can silently
drop a user's hook, so this fails closed with `hooks-carrier-unusable` and
blocks that closure.

Hooks JSON is repetitive, so the derived guarded region may legitimately cover
adjacent unowned bytes whose old and new values are identical. Context is
never shortened to force a unique match; when the region cannot be made
unique, emit `guarded-patch-unavailable` and block.

Create accepts only `strict-create/v1`; delete accepts only
`strict-delete/v1`. Rename is serialized as destination/source path
operations and requires strict protocols for every step. Guarded patch is
never an inverse protocol. Automatic compensation is attempted only when
every required inverse row is strict; otherwise the compensation attempt is
blocked and an unexpected intermediate value yields `partial`.

An absent hooks carrier is therefore a `create` that accepts only
`strict-create/v1`, which no attested live adapter supplies today. Such a row
keeps action `create` with `unavailable` forward and inverse protocols and
outcome `blocked`, and the plan emits `conditional-write-unavailable` and
`hook-carrier-absent`, plus `hook-projection-asymmetric` when the sibling
carrier still proceeds (never for a `class: gate` entry; see Class-gated
all-or-nothing). `Capability profiles` may be `- (none)` for that plan. Bridge
does not create the carrier with an unconditional write and does not invent a
create-after-check. Evidence and notes must print the exact bytes the user can
paste to create the carrier, and must state that Bridge provides no
cross-carrier atomicity, so one host can be active while the other carrier is
still absent.

## Tier and annotation registries

`tier` is `native` for managed skill rows, `structural` for entry and
unscoped-rule rows, `semantic` for valid path-scoped rules, and `-` for
onboarding or unresolved unmanaged rows.

A `hooks/<entry-id>/<host>` row uses that entry's declared
`targets.<host>.tier` verbatim: `native`, `semantic`, or `declared-unsynced`.
`structural` is reserved and invalid for a hook row. A
`hooks/<entry-id>/source` row uses tier `-`, because the source document is
not a projection of itself.

Formal validation derives this value from the authenticated public replay
input and render documents. It does not trust the Units cell or consult an
expectation. It uses source-tree/v5's exact raw-byte frontmatter recognizer,
not a partial YAML parser. The proposed/rendered source takes precedence over
the input source so a confirmed scope conversion is classified by its result;
source deletion falls back to the authenticated input source or exact `pv2`
projection. Missing or duplicate fallback evidence is invalid. A rule that
declares an invalid scope remains a blocked semantic candidate; it is never
reclassified as an unscoped structural rule. An unresolved unmanaged skill
using `annex-or-keep` or `keep` has tier `-`; other managed or resolved skill
rows use `native`.

For a hook row the validator authenticates the declared tier against the same
entry in the authenticated `.claude/rules/hooks.md` source document and
against that unit's `## Hook tiers` row. It never computes a hook tier from a
host capability table; a declared tier that the dated event registry refutes
is a `source-tree/v5` schema violation reported as `intent-doc-anomaly`, not
a silent reclassification.

Annotations are sorted byte-wise and joined by `; `:

- `awaiting-host-trust`
- `behavior-degraded`
- `decision-required`
- `event-unverified`
- `intent-required`
- `live-activation-unknown`
- `migration-transition-required`
- `opt-in-required`
- `restart-may-be-required`
- `semantic-review-required`

`live-activation-unknown` is neutral: it is not a trust state. A pre-write
plan never carries it. In a post-write result, attach it only to a skill row
whose `.agents/skills/<name>/` carrier was written or may have been written,
to an entry/rule row whose root `AGENTS.md` carrier was written or may have
been written, or to a `hooks/<entry-id>/codex` row on the `agents-md` surface
whose degradation block was written or may have been written into root
`AGENTS.md`. Do not attach it when execution never began, the row was
blocked/deferred/not-selected, only a canonical source path could be touched,
or complete-value verification proves the carrier retained its preimage.
`migration-transition-required` is attached to `onboarding/covenant` and every
carried migration row until the closed archived-to-current transition commit
is reachable.
A released migration row has Units baseline `-` and no transition annotation;
its legacy oid remains evidence only in Migration decisions/candidates.
`restart-may-be-required` follows the same post-write carrier-touch predicate:
attach it only when a Codex skill carrier, or root `AGENTS.md` for the affected
entry/rule or for the affected degraded `hooks/<entry-id>/codex` row, was
written or may have been written. A pre-write blocker and
every other no-carrier-write case receive neither restart nor live-activation
annotations. For each affected row, Evidence and notes must say: “Start a new
Codex run/session before testing the updated project instructions or skill.”
This is a required activation step, not a claim that current-main environment
refresh will reload the carrier.

`awaiting-host-trust` is neutral and follows the same post-write carrier-touch
predicate as `live-activation-unknown`: attach it only in a post-write result,
and only to a `hooks/<entry-id>/codex` row whose `.codex/hooks.json` carrier
was written or may have been written. A pre-write plan never carries it.
Codex binds per-hook trust to a normalized handler identity, so a created or
identity-changed handler is listed as new or modified and is silently skipped
at dispatch until the user reviews it. The annotation records that fact; it is
not a trust state and never selects a plan state.

`opt-in-required` is attached to every hook row of an entry whose `class` is
`gate` or `side-effect` with `enabled: true` and no covering `enabled-by`
record. Remove it only after the confirmed dated record has actually been
appended to `.claude/rules/hooks.md`, never because the user discussed the
decision.

`event-unverified` is attached to every hook row whose declared `event` is
absent from the dated closed event registry named by `source-tree/v5`. An
unknown event name stays valid because it may be newer than the registry
date; the annotation records that Bridge cannot prove the host fires it. A
Claude-only event is outside that registry too, so both host rows of such an
entry carry it, including the row whose `## Hook tiers` reason is
`claude-only-event`.

`behavior-degraded` records a portability loss that stays loadable, never a
load failure. On a skill or entry/rule row attach it whenever a
behavior-portability lint is present. On a hook row the predicate is closed:
attach it to every row whose declared tier is `semantic`, because a prose
surface cannot execute the command, and to every row whose owned handler
carries a host passthrough key (Codex `additionalContextLimit`, Claude `if`)
or an unknown Codex handler key. A `native` or `declared-unsynced` hook row
with no such key never carries it. `report/v5` deliberately omits the
tier-`semantic` clause: a read-side row states what the observed carrier holds,
and a prose-surface row owns no handler there, so the read side leaves that
degradation to the row's `semantic` tier column, while a plan row also states
what the write will produce. The two predicates differ by design, and one unit
legitimately gains the annotation between the report and the plan.

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
| `authorization-incomplete` | A selected mutating closure carries authorization `required` |
| `claude-hooks-shared-execution` | A selected write projects a hook handler into the committed `.claude/settings.json` |
| `closure-dependency-unsatisfied` | A selected closure depends on a closure that is not selected and confirmed |
| `codex-activation-unresolved` | Effective Codex configuration or an exact activation carrier cannot be resolved safely |
| `codex-handler-unknown-key` | An owned Codex handler carries a key outside the declared, passthrough, and semantics-changing sets |
| `codex-hook-retrust-required` | A selected Codex write changes the normalized trust identity of a handler that already exists |
| `codex-inline-hooks-conflict` | The same Codex layer also declares hooks inline in `.codex/config.toml`, or their absence cannot be proven |
| `codex-project-untrusted` | Resolved Codex project trust for the scan root is `untrusted` while a hook row targets `.codex/hooks.json` |
| `codex-root-unresolved` | Root-marker evidence does not prove the intended Codex project root |
| `codex-trust-blind-change` | A selected Codex write replaces only `commandWindows` of an existing handler, which the trust identity does not cover |
| `codex-trust-reindex` | A Codex deletion removes a non-final element and shifts the positional trust keys of later elements in that event |
| `conditional-write-unavailable` | A forward or mandatory rename/rollback/compensation operation whose policy requires strict semantics has no attested strict protocol |
| `covenant-anchor-anomaly` | Covenant path/type/tracking, pair coherence, template, or version safety is unresolved |
| `dual-project-entry` | Both supported Claude project-entry files exist |
| `entry-rule-source-anomaly` | An entry/rule source has unsafe type/path, BOM, or invalid/unknown/misplaced v5 control metadata |
| `fallback-shadow` | Creating root `AGENTS.md` would shadow an active configured fallback |
| `guarded-patch-non-cas` | A selected replacement uses `guarded-patch/v1`, whose preflight and postverification leave a residual race |
| `guarded-patch-unavailable` | An existing-file replacement has neither an attested strict protocol nor an eligible exact-region guarded protocol |
| `hook-acknowledgement-missing` | A Claude hook carrier write is selected while `.claude/rules/hooks.md` carries no file-level shared-execution acknowledgement |
| `hook-carrier-absent` | The native carrier a selected hook row targets does not exist |
| `hook-format-preserved` | An owned group already parses equal to its desired model while its bytes differ, so Bridge writes nothing |
| `hook-opt-in-required` | A `gate` or `side-effect` entry with `enabled: true` has no covering `enabled-by` record |
| `hook-output-not-delivered` | A `reminder` entry declares a `native` tier on an event outside the shared stdout-delivering set |
| `hook-projection-asymmetric` | One host's hook carrier is blocked or unavailable while the sibling carrier proceeds |
| `hooks-carrier-unusable` | A hooks carrier fails to parse, carries a duplicate object key, or holds a node outside the closed hooks shape |
| `hooks-globally-disabled` | A tracked hooks projection file sets `"disableAllHooks": true` |
| `ignored-files-excluded` | Relevant ignored paths were excluded and not read or copied |
| `ignored-required-input` | A required unit input is ignored and therefore cannot participate safely |
| `intent-doc-anomaly` | `.claude/rules/hooks.md` violates the `source-tree/v5` hook intent schema |
| `invalid-rule-paths` | A `paths` list is invalid, no-op, duplicate, or over its expansion budget |
| `legacy-managed-mode` | A removed v3 `mode=` marker requires explicit migration/repair |
| `local-hooks-present` | A tracked `.claude/settings.local.json` carries a `hooks` key |
| `manual-zone-guarded` | An `AGENTS.md` guarded patch includes all non-selected spans in the complete pre/post images but cannot prove absence of a lost concurrent edit |
| `manual-zone-preserved` | An `AGENTS.md` write protects all non-selected byte spans in one full-file exact-precondition conditional edit |
| `marker-anomaly` | Marker structure prevents a trustworthy managed/manual region map |
| `matcher-grammar-divergent` | The closed `source-tree-spec.md` predicate holds: the shared `matcher` sits inside the Claude list character class and contains a comma or a pipe, both targets declare a host-executed JSON surface, and neither target overrides `matcher` |
| `migration-closure-incomplete` | A reachable-v1 proven managed unit is absent from the closed migration set or lacks a confirmed repair/release decision |
| `migration-transition-uncommitted` | Desired current-tuple bytes exist but no reachable Git transition commit establishes the complete carried set |
| `mode-limited` | A proposed write requires an executable/worktree-only mode that Git/filesystem cannot prove or realize on the target |
| `platform-branch-divergence` | A Codex handler's `commandWindows` differs from its effective `command`, so Windows and POSIX run different code |
| `sensitive-or-generated-blocked` | Suspected secret, credential, private key, or generated payload blocks copying |
| `skill-loadability-blocked` | A skill fails a report/v5 identity, YAML, BOM, or definite host-loadability gate |
| `surface-shadowed` | Root `AGENTS.override.md` shadows the projection carrier |
| `strict-compensation-unavailable` | At least one selected forward operation has no attested strict inverse; Bridge will not attempt guarded compensation |
| `undeclared-hooks-key` | A hooks carrier group is neither owned by a valid entry nor marked with a Bridge id |
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
| `codex-handler-unknown-key` | `(<Event> group=<i> handler=<j> key=<name>)`, with an exact-case event name, canonical non-negative decimal indices, and the exact handler key name |
| `codex-hook-retrust-required` | `(<Event> group=<i> handler=<j>)` |
| `codex-inline-hooks-conflict` | `(<Event>)` for an inline event table, or the literal `(pointer-key)` for a top-level `hooks =` key |
| `codex-root-unresolved` | `(<reason>)`, where reason is `effective-root-unknown`, `empty-markers`, or `root-marker-excluded` |
| `codex-trust-blind-change` | `(<Event> group=<i> handler=<j>)` |
| `codex-trust-reindex` | `(<Event> from=<index>)`, with a canonical non-negative decimal element index |
| `covenant-anchor-anomaly` | `(<reason>)`, where reason is `partial`, `untracked`, `malformed`, `modified`, or `version-mismatch` |
| `hook-opt-in-required` | `(entry <id>)`, where `<id>` matches `[a-z0-9][a-z0-9-]*` |
| `hook-output-not-delivered` | `(entry <id>)` |
| `hook-projection-asymmetric` | `(<unit-id>)`, the exact blocked or unavailable `hooks/<entry-id>/<host>` unit id |
| `hooks-carrier-unusable` | `(<reason>)`, where reason is `parse-error`, `duplicate-key`, or `unmodelled-shape` |
| `intent-doc-anomaly` | `(entry <id>)` for an entry-scoped violation, otherwise `(line <n>)` with a canonical positive decimal source-line number |
| `invalid-rule-paths` | `(<reason>)`, where reason is `schema`, `empty`, `unsafe`, `invalid-bracket`, `no-op-universal`, `duplicate`, `expansion-count`, `expansion-bytes`, or `expansion-unproved` |
| `legacy-managed-mode` | `(line <n>)`, where `n` is a canonical positive decimal source-line number |
| `marker-anomaly` | `(line <n>)`, where `n` is a canonical positive decimal carrier-line number |
| `matcher-grammar-divergent` | `(entry <id>)` |
| `mode-limited` | `(<reason>)`, where reason is `explicit-executable-unrealizable`, `worktree-mode-unobservable`, or `target-mode-unpreservable` |
| `platform-branch-divergence` | `(entry <id>)` |
| `undeclared-hooks-key` | `(<Event> matcher=<matcher>)` with the exact declared matcher string, or `(<Event> matcher=omitted)` when the group declares none |

Warnings never grant write authority. `agents-md-near-budget`,
`claude-hooks-shared-execution`, `codex-hook-retrust-required`,
`codex-trust-reindex`, `guarded-patch-non-cas`, `hook-projection-asymmetric`,
`manual-zone-guarded`, `manual-zone-preserved`,
`matcher-grammar-divergent`, `platform-branch-divergence`, and
`strict-compensation-unavailable` require explicit acknowledgement but are
not forward-apply blockers. The absence of a strict inverse blocks an
automatic compensation attempt, not an explicitly confirmed guarded forward
operation. `codex-handler-unknown-key`, `codex-project-untrusted`,
`codex-trust-blind-change`, `hook-carrier-absent`, `hook-format-preserved`,
`hook-output-not-delivered`, `hooks-globally-disabled`,
`ignored-files-excluded`, `local-hooks-present`, `undeclared-hooks-key`,
`unrelated-dirty-preserved`, `untracked-files-included`, and
`validator-profile-mismatch` are informational unless a separate blocker row
below applies. `codex-inline-hooks-conflict`, `hook-acknowledgement-missing`,
`hook-opt-in-required`, and `hooks-carrier-unusable` are closure-scoped
blockers; `intent-doc-anomaly` is a project-wide blocker. Evidence and notes may cite
commands, intent records, commit ids, operation-local manual-zone digests, and
user decisions; it is free-form and not a durable baseline.

Hook warnings obey the same one-line-per-exact-fact rule. Emit
`claude-hooks-shared-execution` once for `.claude/settings.json` whenever the
plan selects any Claude hook carrier write, one `codex-hook-retrust-required`
line per handler whose normalized identity changes, one
`codex-trust-blind-change` line per handler whose replacement touches only
`commandWindows`, one `hook-opt-in-required` line per entry, one
`intent-doc-anomaly` line per violation, and one `undeclared-hooks-key` line
per `(file, event, matcher)` fact. `codex-hook-retrust-required` and
`codex-trust-blind-change` are mutually exclusive for one handler: an
identity change emits the first, a `commandWindows`-only change the second.

Hook warning paths are pinned. Use `.claude/settings.json` for
`claude-hooks-shared-execution`; `.codex/hooks.json` for
`codex-handler-unknown-key`, `codex-hook-retrust-required`,
`codex-trust-blind-change`, and `codex-trust-reindex`; `.codex/config.toml`
for `codex-inline-hooks-conflict`; `.` for `codex-project-untrusted`;
`.claude/rules/hooks.md` for `hook-acknowledgement-missing`,
`hook-opt-in-required`, `hook-output-not-delivered`, `intent-doc-anomaly`,
`matcher-grammar-divergent`, and `platform-branch-divergence`;
`.claude/settings.local.json` for `local-hooks-present`; the absent carrier
for `hook-carrier-absent`; the blocked carrier for
`hook-projection-asymmetric`; the affected carrier for
`hook-format-preserved`, `hooks-carrier-unusable`, and
`undeclared-hooks-key`; and the settings file, either
`.claude/settings.json` or `.claude/settings.local.json`, for
`hooks-globally-disabled`.

Every plan containing at least one hook unit row states this exactly in
Evidence and notes: "The opt-in record is a review checkpoint in Git, not an
enforcement boundary. Bridge classification is author-declared metadata, not
a sandbox. Claude Code runs hooks from committed settings without a trust
prompt in `-p` and SDK sessions, so anyone who can commit to this repository
can run commands on a teammate's machine." Hook execution is also
observed-but-not-guaranteed on both hosts, so no Bridge state may be read as a
runtime guarantee.

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

Apply is forbidden when any row matches. Every blocker in reconciliation/v3
must map to this table; adding a blocker requires a spec-version change.

| Gate | Trigger | Serialized evidence |
|---|---|---|
| authorization | a selected mutating closure carries authorization `required` | `authorization-incomplete` plus closure authorization |
| dependency | selected closure dependency is not selected and confirmed | `closure-dependency-unsatisfied` plus Closures row |
| covenant | covenant path/type/tracking, pair coherence, template, or version is unresolved | `covenant-anchor-anomaly` |
| activation | effective config/carrier is unknown, root is unproven, override/fallback shadows, budget is zero/exceeded | one or more of `codex-activation-unresolved`, `codex-root-unresolved`, `surface-shadowed`, `fallback-shadow`, `agents-md-budget-disabled`, `agents-md-budget-exceeded` |
| entry/rule source | dual entry, active import, invalid paths, legacy mode, unsafe/control anomaly, or marker map failure | one or more of `dual-project-entry`, `active-shared-import`, `invalid-rule-paths`, `legacy-managed-mode`, `entry-rule-source-anomaly`, `marker-anomaly` |
| history | ownership candidates are ambiguous | `ambiguous-baseline` |
| hook source | `.claude/rules/hooks.md` violates the `source-tree/v5` hook intent schema | `intent-doc-anomaly` |
| hook carrier | a hooks carrier is unparseable, duplicate-keyed, or unmodelled, or the same Codex layer also declares inline `[hooks]` | `hooks-carrier-unusable`, `codex-inline-hooks-conflict` |
| hook opt-in | a selected native carrier of a `gate`/`side-effect` entry lacks a covering `enabled-by` record, or a selected Claude hook carrier write lacks the file-level acknowledgement | `hook-opt-in-required`, `hook-acknowledgement-missing` |
| migration closure | legacy set/decision is incomplete | `migration-closure-incomplete` |
| migration finalization | desired current bytes are already prepared but the closed transition commit is not reachable | `migration-transition-uncommitted`; block ordinary Bridge writes and synchronized/ownership claims, but wait for the external user commit rather than blocking the already-completed migration byte preparation |
| tree safety | symlink/reparse/gitlink/special file, case collision, path escape, or unsafe target | `unsafe-tree-entry` |
| ignored required input | a required input is excluded by ignore rules | `ignored-required-input` |
| skill loadability | report/v5 definite skill-load gate fails | `skill-loadability-blocked` |
| sensitive/generated | content must not be copied | `sensitive-or-generated-blocked` |
| mode preservation | selected direction requires an unrealizable/unprovable mode | `mode-limited` |
| write capability | a strict-required forward or mandatory rename/rollback/compensation operation is unavailable, or an eligible existing-file replacement has neither a strict nor guarded protocol | `conditional-write-unavailable` for strict-required operations; otherwise `guarded-patch-unavailable`, plus the matching `unavailable` Write capabilities row |
| unresolved unit decision | conflict, annex/replace, release, destructive, migration, semantic-review, or offboarding decision is pending | the matching closed decision shape below; never prose-only state |

### Narrowed blocker scope (closed exception)

The project-wide prohibition above stands for every gate except three. For
the `write capability`, `hook carrier`, and `hook opt-in` gates only, the
prohibition is scoped to the closure that contains the matching row and to
every closure that depends on it; independent selected closures may proceed.
Every other gate, including `hook source`, remains project-wide.

A scoped-blocked closure keeps `selected`, authorization `not-applicable`,
and outcome `blocked`, and each of its unit rows repeats that shape. It is
never relabelled `not-selected`, because a capability or gate failure must
stay inside header-authorization derivation and inside every gate. When one
carrier is scoped-blocked while its sibling proceeds, emit the acknowledged
`hook-projection-asymmetric` on the blocked carrier.

### Class-gated all-or-nothing

For an entry whose `class` is `reminder`, `observation`, or `side-effect`,
one carrier may apply while the sibling carrier is blocked or unavailable,
under the acknowledged `hook-projection-asymmetric`. For an entry whose
`class` is `gate` the entry is all-or-nothing: a blocked or unavailable
carrier forces the sibling carrier closure to `not-selected` with zero
writes, because asymmetric enforcement is worse than no enforcement.

## Closed decision serialization

Decision state is serialized in rows, never only in prose. Apply the first
matching row:

| Decision state | Closure | selection | authorization | outcome | Required annotations |
|---|---|---|---|---|---|
| Codex onboarding segmentation or authority target pending | `closure/decision/onboarding/agents-md` | `not-selected` | `not-applicable` | `not-selected` | `decision-required` |
| hook opt-in pending: `class` is `gate` or `side-effect`, `enabled: true`, and no covering `enabled-by` record exists | `closure/decision/hooks/<entry-id>` | `selected` | `required` | `deferred` | `decision-required; opt-in-required` |
| two-sided hook `both-changed` conflict | `closure/decision/hooks/<entry-id>` | `selected` | `required` | `deferred` | `decision-required` |
| pending hook occupancy: `annex-or-keep` over a marked orphan, a foreign handler, or a semantics-changing key | `closure/decision/hooks/<entry-id>` | `not-selected` | `not-applicable` | `not-selected` | `decision-required` |
| confirmed hook `keep` | `closure/decision/hooks/<entry-id>` | `selected` | `not-applicable` | `deferred` | `-` |
| hook target declares `surface: none` and no decision is pending | `closure/decision/hooks/<entry-id>` | `selected` | `not-applicable` | `unchanged` | `-` |
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

### Hook decision closures

An entry's zero-write hook rows share one `closure/decision/hooks/<entry-id>`
so a two-host decision is never split across two closures. The hook rows in
the table above are matched before the generic rows: a hook `both-changed`
conflict uses `closure/decision/hooks/<entry-id>`, never
`closure/decision/<unit>`.

A hook decision closure is zero-write, so header authorization stays derived
from selected mutating closures only. A plan whose only hook decision closure
is `selected` / `required` / `deferred` still serializes
`- authorization: not-applicable` and emits no `authorization-incomplete`
line, exactly as an entry/rule `both-changed` conflict does. Both
`Capability profiles` and `Write capabilities` are `- (none)` for such a plan.

An opt-in decision is resolved by writing, not by discussion. Confirming it
produces a `hooks/<entry-id>/source` row in `closure/hooks/source` with
action `update`, direction `user-decision`, tier `-`, and `intent-required`
until the dated `enabled-by` record exists, plus the ordinary carrier rows
that depend on that closure. Until those bytes exist, `opt-in-required`
remains attached to every hook row of the entry. Evidence and notes must show
the exact command line being enabled and the pinned "not a sandbox" sentence
before confirmation.

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
mutating unit and closure the journal will execute is `confirmed` / `planned`.
A scoped-blocked closure stays `not-applicable` / `blocked` and contributes no
journal step, so its presence never keeps a plan out of a journal. A
post-write result, expectation document, required authorization, or
non-planned mutation cannot seed a journal, and any byte change invalidates
the plan digest.

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
`onboarding/covenant` is excluded from both tables. A `hooks/*` unit never
appears in either table: no archived-tuple commit can prove a hook baseline,
so a hooks unit claiming one is out-of-contract evidence and is
`blocked` / `resolve-blocker`. The candidate-table unit
set must equal the Migration decisions unit set after that exclusion.
When a unit has exactly one candidate, `legacy baseline` is that same full oid
and `current relation` is not `ambiguous`. When it has two or more
incomparable candidates, `legacy baseline` is `-`, `current relation` is
`ambiguous`, and every maximal candidate appears in the independent table.
No timestamp, first-parent choice, abbreviated oid, or arbitrary representative
may collapse the set. `current relation` is otherwise `converged`,
`repair-required`, `missing`, or `unsafe`.

A safe unit already satisfying its current-contract relation uses
`carry-forward` and `derived`; it cannot silently disappear from the
migration. Every other row
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
current covenant pair and the complete closed set. Bridge does not commit;
until that commit is reachable, emit `migration-transition-uncommitted`,
keep migration
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

## Hook tiers and reasons

Every document carries a `## Hook tiers` section immediately after
`## Warnings`. It is `- (none)` when the plan has no hook unit row. Otherwise
it is exactly this table:

```markdown
| unit | class | surface | tier | reason |
|---|---|---|---|---|
```

`unit` is a plan hook unit id. `class` is the entry's declared
`reminder`, `observation`, `gate`, or `side-effect`. `surface` is the entry's
declared `targets.<host>.surface`, which is `settings-json`, `intent-doc`, or
`none` on a Claude row and `codex-hooks-json`, `agents-md`, or `none` on a
Codex row. `tier` is the entry's declared `targets.<host>.tier` and must equal
that unit's Units-table `tier` cell. `reason` is one token from the closed
registry below. A `hooks/<entry-id>/source` row uses the entry's `class` with
surface `-`, tier `-`, and reason `-`, because the source document is not
projected anywhere.

Rows sort byte-wise by unit. The row set must equal the plan's hook unit set
exactly: no missing row, no extra row, no duplicate unit.

| Reason | Meaning |
|---|---|
| `shared-event-command` | The event is in the dated shared registry and one command handler serves both hosts |
| `claude-only-event` | The declared event is native on Claude and absent from the Codex event set |
| `codex-only-event` | The declared event is native on Codex and absent from the Claude event set |
| `degraded-standing-instruction` | The Codex counterpart is one managed root `AGENTS.md` block instead of a handler |
| `intent-doc-standing-instruction` | The Claude counterpart is the unconditionally loaded `.claude/rules/hooks.md` prose itself, with zero writes |
| `declared-none` | The entry declares `surface: none` for this host and states no other portability obstacle |
| `decision-not-portable` | The event's decision shape differs between the hosts, so one command cannot serve both |
| `handler-type-not-portable` | The intended handler type is not `command` and is never projected |
| `async-not-portable` | The intent needs asynchronous execution, whose output and timeout semantics differ on both hosts |
| `matcher-domain` | The event's matcher value domain differs between the hosts |
| `codex-matcher-ignored` | Codex ignores matchers for the declared event |
| `platform-command-branch` | The command line needs a per-platform branch through `targets.codex.commandWindows` or `targets.claude.shell` |
| `timeout-cap-differs` | The hosts apply different timeout defaults or caps to the declared event |
| `output-not-delivered` | The host runs the handler but does not deliver its stdout to the model on the declared event |
| `opt-in-pending` | The entry is `gate` or `side-effect` with `enabled: true` and no covering `enabled-by` record |

This section exists because expectation comparison ignores Evidence and
notes. A tier justification recorded only in prose is not mechanically
comparable, and every plan must explain each hook's tier and reason on both
hosts.

## Hook handler adoption decisions

Every document carries a `## Hook adoption decisions` section immediately
after `## Adoption decisions`. It is `- (none)` when no hooks-carrier handler
awaits an ownership decision. Otherwise it is exactly this table:

```markdown
| handler | location | disposition | destination | decision |
|---|---|---|---|---|
```

This is the JSON analogue of the line-span Codex-start table. `handler` is
`handler/<n>` with a one-based decimal `n` allocated in carrier file order
with no gaps. `location` is `<file>#<Event>[<group-index>][<handler-index>]`,
where `<file>` is the repository-relative carrier path, `<Event>` is the
exact-case event name, and both indices are canonical non-negative decimals
in carrier array order. `disposition` is `adopt`, `keep`, or `discard`.
`destination` is `hooks/<entry-id>` for `adopt` and `-` otherwise. `decision`
is `pending` or `confirmed`. Rows serialize in that same carrier file order.
When both carriers contribute handlers, order by carrier path byte-wise
first, so `.claude/settings.json` precedes `.codex/hooks.json`, and then by
file order within each carrier; number `handler/<n>` over that combined
order.

Every handler that a hook decision closure reports as unresolved occupancy
has exactly one row. A pending row uses the pending hook occupancy shape
above: `closure/decision/hooks/<entry-id>`, `not-selected` /
`not-applicable` / `not-selected`, with `decision-required`. `discard` is
destructive and needs its own explicit confirmation. A confirmed `adopt`
writes a new entry into `.claude/rules/hooks.md` inside
`closure/hooks/source` with user-supplied prose bullets; Bridge never invents
`Purpose` or `Failure policy`. Handler ids are operation-local review
handles, never ownership or baseline metadata.

## Formal validation

Every document must pass a formal `sync-plan/v3` validator before it is shown
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
hooks-carrier-composition
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
   supplied operation-lifecycle context, post-only carrier annotation timing
   for `live-activation-unknown`, `restart-may-be-required`, and
   `awaiting-host-trust`, exact unit tiers derived from authenticated public
   input/render source documents including each hook row's declared
   `targets.<host>.tier`, and the explicit temporal context that
   distinguishes an operation-scoped empty-bootstrap result from an
   independent untracked-carrier scan;
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
   `intent-required`, confirmed entry/rule promotion with satisfied
   annotations removed, the five hook decision shapes bound to
   `closure/decision/hooks/<entry-id>`, the narrowed scope of the
   `write capability`, `hook carrier`, and `hook opt-in` gates, and the
   `class: gate` all-or-nothing rule;
8. per-payload-unit migration decisions and candidates, candidate-set
   equality, canonical selected blocked ambiguity, post-migration
   carried/released baseline and annotation state, and exclusion of
   `onboarding/covenant` from the evidence tables;
9. Adoption decisions order, dispositions, destinations, and consistency with
   the Units and Closures tables, including rejection of
   `onboarding/agents-md` without explicit pending segmentation; plus the
   destination/source baseline-state pair for every rename closure;
10. the `## Hook tiers` section: `- (none)` or the exact header, byte-wise
    unit order, exactly one row per plan hook unit with no extra or duplicate
    row, closed `class`, `surface`, `tier`, and `reason` tokens, per-host
    surface legality, and equality between each row's `tier` and its Units
    row `tier`;
11. the `## Hook adoption decisions` section: `- (none)` or the exact header,
    carrier file order, gapless one-based `handler/<n>` numbering, the
    `<file>#<Event>[<i>][<j>]` location grammar, closed dispositions and
    destinations, and consistency with the hook decision closures in the
    Units and Closures tables; and
12. `hooks-carrier-composition`: for every render operation on a hooks
    carrier, recompute the `json-owned-span/v1` composition from the exact
    preimage plus the owned desired models and require byte equality with
    that operation's post value. A postimage that differs anywhere outside
    the located owned spans and insertion points is rejected, and so is any
    postimage produced by reserializing the parsed document.

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
`- expectation: sync-plan/v3` and may omit Evidence and notes. Compare after
normalization N from `source-tree/v5`:

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
7. Hook tiers are both `- (none)` or have byte-identical headers and
   byte-identical complete row sequences in byte-wise unit order;
8. Migration decisions are both `- (none)` or have byte-identical headers and
   byte-identical complete row sequences in byte-wise unit order;
9. Migration candidates are both `- (none)` or have byte-identical headers
   and byte-identical complete row sequences in byte-wise
   `(unit, legacy candidate)` order;
10. Adoption decisions are both `- (none)` or have byte-identical headers and
   byte-identical complete row sequences in normative segment order;
11. Hook adoption decisions are both `- (none)` or have byte-identical
   headers and byte-identical complete row sequences in carrier file order;
12. project, invoked scan-root spelling, date, and Evidence and notes are
   ignored.

`codex-activation-unresolved`, `codex-root-unresolved`,
`conditional-write-unavailable`, `guarded-patch-unavailable`, and
`mode-limited` may depend on effective host or filesystem evidence. A
deterministic fixture must pin or deliberately exclude those inputs; plan
comparison does not silently remove the warnings.

`codex-project-untrusted` depends on live Codex activation inputs and is
pinned in fixture mode by the activation profile named in `report/v5`.
`hook-carrier-absent`, `hooks-carrier-unusable`, `hooks-globally-disabled`,
`local-hooks-present`, and `codex-inline-hooks-conflict` are derived from
repository bytes alone and are never host-dependent.
