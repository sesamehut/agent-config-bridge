# Bridge sync plan specification

Spec version: sync-plan/v1.

This file defines the deterministic M2 pre-write plan and post-write result
for [`reconciliation/v1`](reconciliation-spec.md).

## Contract header

Every document uses:

```markdown
# Bridge Sync Plan

- project: <directory name of repository root>
- scan root: <path as invoked>
- date: <YYYY-MM-DD>
- spec: sync-plan/v1
- contracts: covenant/v1, source-tree/v3, report/v3, reconciliation/v1
- phase: <pre-write|post-write>
- onboarding: <onboarded|bootstrap-required|blocked>
- authorization: <required|confirmed|not-applicable>

## Units

| unit | baseline | state | action | direction | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|
<rows>

## Warnings

<warning lines or "- (none)">

## Evidence and notes

<free-form>
```

Unit ids are `onboarding/covenant` or `skills/<name>`. Sort rows byte-wise by
unit. `baseline` is `-` or the full lowercase 40- or 64-hex Git object id.
Empty cells use `-`. Cell padding and annotation sorting follow `report/v3`.

## State registry

| Token | Meaning |
|---|---|
| `unchanged` | Current managed carriers are equal and require no write |
| `source-only` | Only source differs from the unique baseline |
| `projection-only` | Only projection differs from the unique baseline |
| `both-changed` | Both differ from the same baseline and current trees differ |
| `no-baseline` | No current-contract managed baseline is provable |
| `contract-migration` | A safe, tracked, coherent older/different contract pair requires explicit migration |
| `offboarding` | Both covenant halves disappeared after provable onboarding |
| `blocked` | Safety, malformed ownership, or ambiguous evidence prevents a write |

## Action registry

| Token | Meaning |
|---|---|
| `create` | Create a missing covenant pair or projection from a valid source |
| `repair` | Resolve safety/trackability or restore a partial, malformed, modified, or incoherent covenant pair before tuple migration |
| `restore` | Restore both current covenant halves after an unconfirmed historical disappearance |
| `update` | Propagate a source-only semantic change |
| `reproject` | User confirms source should repair an accidental/mechanical projection change |
| `adopt` | Copy a projection-only managed intent to source and append its intent record |
| `conflict` | Both sides carry different new intent; write neither |
| `delete` | Converge a proven managed deletion in the stated direction |
| `rename` | Atomically rename an old/new managed unit closure |
| `annex-or-keep` | Unknown occupancy requires an explicit ownership decision |
| `annex` | User explicitly establishes ownership using the recorded authority |
| `keep` | Leave unknown occupancy untouched for this run and unresolved |
| `migrate` | Explicitly replace one contract tuple with another |
| `offboard` | Explicitly remove the Bridge covenant and managed ownership |
| `resolve-blocker` | No write until the named safety/evidence problem is resolved |
| `unchanged` | No write |

## Direction registry

`-`, `source-to-projection`, `projection-to-source`, and `user-decision`.
Delete and rename rows use the direction of the intent. A conflict,
annex-or-keep, repair, restore, migration choice, or unresolved offboarding
uses `user-decision`.

## Outcome registry

| Token | Phase | Meaning |
|---|---|---|
| `planned` | pre-write | Authorized action has not run yet |
| `applied` | post-write | Write and all verification passed |
| `unchanged` | either | No write was needed |
| `deferred` | either | Conflict, keep, or decision remains unresolved |
| `blocked` | either | Safety/evidence gate prevented the write |
| `failed` | post-write | Execution failed before mutation and the closure is proven unchanged |
| `compensated` | post-write | Mutation began, failed, and automatic operation-local compensation restored and verified the complete pre-write closure |
| `partial` | post-write | Mutation began and the complete applied or pre-write closure cannot be proven after compensation stopped or failed |
| `not-attempted` | post-write | The closure did not run because an earlier closure failed/was partial or a dependency closure did not execute |
| `rolled-back` | post-write | User-confirmed operation-local rollback verified |

Pre-write actions that could mutate use `planned` even before authorization;
the header distinguishes `required` from `confirmed`. `conflict`,
`annex-or-keep`, and `keep` use `deferred`. `resolve-blocker` uses `blocked`.
`keep` never uses `unchanged`. `blocked` means a pre-write safety or evidence
gate selected the closure; `failed` means execution was attempted but no
mutation survived; `not-attempted` means execution never began.
`compensated` is automatic failure handling already authorized by the
confirmed plan. `rolled-back` is a later, separately confirmed operation.

## Tier and annotation registries

`tier` is `native` for managed skill rows and `-` for onboarding or unresolved
unmanaged rows.

Annotations are sorted byte-wise and joined by `; `:

- `behavior-degraded`
- `decision-required`
- `intent-required`
- `live-activation-unknown`
- `restart-may-be-required`

`live-activation-unknown` is neutral: it is not a trust state.
`restart-may-be-required` is attached after a Codex skill carrier may have
changed, because repository bytes do not reveal session cache state.

## Warning registry

Each line is `- <token>: <repo-relative-path>` with optional parenthesized
detail, sorted byte-wise as a complete line:

| Token | Condition |
|---|---|
| `ignored-files-excluded` | Relevant ignored paths were excluded and not read or copied |
| `mode-limited` | A proposed write requires an executable/worktree-only mode that Git/filesystem cannot prove or realize on the target |
| `sensitive-or-generated-blocked` | Suspected secret, credential, private key, or generated payload blocks copying |
| `unrelated-dirty-preserved` | The repository has out-of-scope dirty changes that the plan preserves |
| `unsafe-tree-entry` | Symlink, reparse point, gitlink, special file, case collision, or path escape blocks a unit |
| `untracked-files-included` | Relevant non-ignored untracked files participate in the current snapshot and plan |
| `validator-profile-mismatch` | Current Codex validator profile rejects otherwise separately classified content |

Warnings never grant write authority. Evidence and notes may cite commands,
intent records, commit ids, manual-zone hashes held only for this operation,
and user decisions; it is free-form and not a token registry.

## Deterministic expectation comparison

A fixture expectation replaces `- spec:` with
`- expectation: sync-plan/v1` and may omit Evidence and notes. Compare after
normalization N from `source-tree/v3`:

1. expectation/spec, contracts, phase, onboarding, and authorization match;
2. the Units header is byte-identical and sorted row multisets are identical;
3. sorted Warning line multisets are identical;
4. project, invoked scan-root spelling, date, and Evidence and notes are
   ignored.

No warning token is environment-dependent in `sync-plan/v1`.
