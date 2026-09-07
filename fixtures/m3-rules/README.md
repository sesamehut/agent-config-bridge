# M3 reconciliation fixtures

These declarative vectors exercise `covenant/v3`, `source-tree/v5`,
`report/v5`, `reconciliation/v3`, and `sync-plan/v3` entry/rule behavior.
The harness validates the matrix, named trees, exact plan grammar, fixture-only
capability attestations, write protocols, rendered proposals, expected
post-state, safeguards, lease-bound materialization, live-journal schema, and
cleanup. Its `self-test` never invokes `bridge-sync`. It does execute the
fixture-only guarded-preflight adapter in separate CLI processes. Windows
executes the same-mode arm/inject/persistence barrier under its independent
name-to-handle attestation. POSIX validates the declaration and retained read,
then rejects target mutation before entering the mutation path. That is
adapter evidence, not a Bridge workflow result.

## Safe commands

Run every command from the repository root:

```text
python -B fixtures/m3-rules/fixture_harness.py list
python -B fixtures/m3-rules/fixture_harness.py self-test
python -B fixtures/m3-rules/fixture_harness.py materialize scoped-project
python -B fixtures/m3-rules/journal_validator_tests.py --mode single
python -B fixtures/m3-rules/journal_validator_tests.py --mode concurrent
```

`materialize` accepts an `agent` replay-input id. Most ids equal their scenario
id; the Codex-first branches use `codex-first-pending` and
`codex-first-confirmed`. The command creates one direct child of the resolved
operating-system temporary directory, initializes and commits a disposable Git
repository, applies the input tree, and installs canonical, single-link plain
files under the retained `.git` directory: the exact closed
`activation-fixture/v1` profile, the bound `write-capability-fixture/v1`
document, an optional `fault-schedule-fixture/v1`, the
`replay-bundle-commitment/v1` operation binding, and the
`bridge-m3-replay-envelope/v2` envelope. The marker and envelope both name the
same commitment. That commitment binds marker identity, suite, scenario,
replay id, resolved root, nonce, baseline and live HEAD, lease SHA-256,
activation profile, capability, optional schedule, payload, and phase-evidence
spec under `canonical-json/v1`. Its lease-keyed HMAC detects accidental
cross-operation substitution; because the caller holds the lease, it is not a
signature or a caller-authentication boundary. Scenarios with history
requirements create their declared real commit DAG before applying the input
snapshot. Never run a mutation against the checked-in fixture sources.

Read the bound blind input before invoking the skill:

```text
python -B fixtures/m3-rules/fixture_harness.py replay-input scoped-project <worktree> --lease <lease>
```

`replay-input` validates the complete canonical marker/lease/commitment chain
and constructs a dedicated, recursively closed allowlist DTO. It emits only
the bound identity, input bytes, activation-profile facts, decision facts,
capability facts, optional fault schedule, and rendered proposal operations.
It never serializes the internal envelope wholesale and never emits expectation
ids or paths, plan files, planned-state names, post-state names, golden/oracle
aliases, or expectation content. A fixture capability is valid only inside
that one materialized replay input; it is not evidence for PowerShell, Claude
Code tools, Codex `apply_patch`, Python I/O, or any live host adapter.

Validate an independently serialized plan against that same public replay
binding and lifecycle. If validation fails, request the separately versioned
diagnostic envelope:

```text
python -B fixtures/m3-rules/fixture_harness.py validate-plan <replay-input> <worktree> --lease <lease> --plan <plan.md> --operation-lifecycle <lifecycle>
python -B fixtures/m3-rules/fixture_harness.py explain-plan <replay-input> <worktree> --lease <lease> --plan <plan.md> --operation-lifecycle <lifecycle>
```

`validate-plan` remains the closed `sync-plan-validator/v1` admission
contract. `explain-plan` is the independent `sync-plan-diagnostic/v1`
companion; it does not change the validator response. It repeats the exact
plan and context hashes and reports the validator failure ids plus closed,
deterministically sorted diagnostics. Warning diagnostics distinguish
`missing`, `extra`, `invalid-order`, `cardinality`, `token`, and `path`;
non-warning failures remain `generic`. Required warning lines are derived
only from the installed public replay bundle, live Git state, capability and
render operations, decision, temporal context, and supplied lifecycle.
Neither command reads an expectation id, path, plan, post-state alias,
matrix result, golden value, or oracle content.

The executable guarded-preflight scenario has an additional, phase-bound
fixture adapter on Windows. After the agent has emitted and the user has
confirmed the exact pre-write plan, arm it and then consume the schedule once:

```text
python -B fixtures/m3-rules/fixture_harness.py arm-fault guarded-preflight-mismatch <worktree> --lease <lease> --plan <confirmed-plan.md> --operation-id <operation-id>
python -B fixtures/m3-rules/fixture_harness.py apply-fault guarded-preflight-mismatch <worktree> --lease <lease> --operation-id <operation-id>
```

`arm-fault` snapshots and validates the exact confirmed plan, committed input
tree, one guarded root `AGENTS.md` target, preimage, mode, and retained root,
leaf, and plan identities. `apply-fault` accepts no caller-supplied phase or
target. On Windows it probes, reads, and exclusively creates the append-only
`armed -> claim -> injected` receipts relative to one retained `.git` parent.
Every receipt authenticates its creation-time file and parent identities,
mode, link count, and reparse status; each later state also binds the prior
receipt's raw digest and complete identity evidence. A valid interrupted claim
resumes from the exact preimage or finalizes evidence from the exact postimage;
every other recovery shape fails closed.

POSIX retained root/leaf handles still prove the read that `arm-fault` records,
but they do not atomically prove that the current root-child name still maps to
that leaf at mutation time. The POSIX adapter is therefore declarative-only:
`apply-fault` rejects before claim creation or target mutation. It does not
claim swapped-path resistance or an executable injected result. Windows keeps
its existing same-mode capability because its retained handles deny delete
sharing and revalidate the current name/handle pair; mode changes remain
declarative-only on every platform. After a successful Windows injection, the
agent must run the final full-file preflight, emit a post-write plan whose
affected closure is exactly `failed`, and make zero Bridge writes.

After an agent runs `$bridge-sync` against only that disposable repository and
saves the emitted plan outside this repository, compare both the plan and
post-state:

```text
python -B fixtures/m3-rules/fixture_harness.py compare scoped-project <worktree> --lease <lease> --expectation applied --actual-plan <actual-plan.md>
python -B fixtures/m3-rules/fixture_harness.py cleanup scoped-project <worktree> --lease <lease>
```

Cleanup is permanent. It validates the exact suite, scenario, resolved root,
baseline, and lease-bound marker before deleting one named project. It never
enumerates or broadly cleans the temporary directory.

If, and only if, the lease for an M3 synthetic fixture was lost, the
Windows-only test-recovery command has a separate contract:

```text
python -B fixtures/m3-rules/fixture_harness.py cleanup-stale <scenario> <absolute-worktree> --marker-sha256 <raw-marker-sha256> --nonce <nonce> --acknowledge-lost-lease --acknowledge-no-active-external-operation
```

`cleanup-stale` is fixture recovery, not product cleanup and not a substitute
for normal lease cleanup. Both acknowledgements are mandatory. The second is
an explicit caller assertion at the fixture-cooperation boundary: M3 live
journals use separate OS-temporary lease directories, and the recovery command
deliberately does not enumerate temporary-directory siblings, so absence of an
older external journal is not mechanically proven. The command reports that
operator-attested boundary as
`operator-attested/fixture-cooperative` in its closed result. The recovery
claim blocks later cooperating harness entrypoints; it does not retroactively
cancel an operation that already passed the claim gate.

The command accepts exactly one already-canonical direct OS-temporary child
whose basename, scenario, nonce, raw marker SHA-256, closed marker schema,
marker root, Git top-level/directory/common directory/object format, baseline,
and live HEAD all agree. It rejects alternates, gitlinks, nested Git
repositories, symlinks, reparse points, hardlinks, special files, locks,
journals, and any fault-phase or prior recovery claim. Before quarantine it
creates an exclusive, retained `.git` recovery claim; all M3 replay, fault,
journal-allocation, plan, compare, and normal-cleanup entrypoints refuse a
claimed fixture.

Deletion is permanent. A retained Windows parent/root handle pair denies
delete sharing and verifies the final path, volume, file id, and reparse
status. `SetFileInformationByHandle` atomically renames that exact root to an
unpredictable, no-replace tombstone in the same retained parent. The original
name is never followed again. Only the verified tombstone is traversed. Before
deleting anything, the recovery operation opens every descendant with
`DELETE` access, no delete sharing, and no-follow reparse semantics; retains
all of those handles; then re-enumerates the complete exact name-to-file-id
set. It disposes descendants postorder through those same handles and deletes
the empty root through its pinned root handle. No path-based unlink/rmdir
fallback exists. A child present at final revalidation, a same-name replacement
attempt, held descendant, unknown type, or missing capability fails closed
before any disposition. A non-cooperating namespace mutation after final
revalidation is outside the mechanical proof and may produce `state=partial`
after some dispositions; this is why `cleanup-stale` relies on the
operator-attested fixture-cooperation boundary described above. A
pre-disposition failure reports `state=quarantined` with the exact tombstone;
an interrupted disposition reports `state=partial`, `recoverable=false`, the
removed entries, and any remaining tombstone. A new object at the old name is
preserved. Non-Windows platforms fail closed. The main `self-test` includes
the 43-case stale-recovery contract matrix and a sibling canary.

## Replay boundary

The matrix contains 41 independent scenarios, 42 replay inputs, and 42
expectation branches. Thirty-nine scenarios (40 replay inputs) are
agent-replayable. Two remain declarative-only:

- `guarded-postverify-race` needs a deterministic mutation inside the guarded
  host-call/postverification window;
- `verify-failure-no-compensation` needs a deterministic post-write,
  pre-verification fault barrier.

Their plans, exact trees, faults, and safeguards are still schema-validated.
They are not executable workflow results.
This matrix count is platform-neutral. On POSIX,
`guarded-preflight-mismatch` remains materializable for plan/declaration
validation, but its fixture target mutation is additionally
declarative-only under the platform capability gate above.

## Contract data

[`scenario-matrix.json`](scenario-matrix.json) uses
`bridge-m3-rules-matrix/v2`; each scenario uses
`bridge-m3-rules-scenario/v2`. [`tree-manifest.json`](tree-manifest.json) is a
named `bridge-fixture-tree-set/v1` graph. Trees may extend one earlier tree
and apply ordered safe write, delete, or symlink operations resolved by the
shared product-neutral helper in [`../_support/`](../_support/).

Every expectation names one `sync-plan/v3` document and one exact post-state
tree. A budget warning also names `planned_state`; the harness derives the
complete planned `AGENTS.md` byte count from that tree and checks the warning's
threshold relation. A syntactically valid all-zero baseline in an expectation
is a fixture placeholder only when its `baseline_ref` binds it to the
materialized commit; the harness substitutes that exact commit before
comparison. Plan comparison checks the complete headers, unit and closure
tables, capability-profile bindings, ordered physical path operations,
migration decisions and complete candidate sets, adoption decisions,
warnings, outcomes, registries, ordering, and cross-field invariants.

Every serialized capability row must be exactly derivable from the scenario's
closed declaration under [`capabilities/`](capabilities/). Positive profiles
carry fixture-scoped host/version/tool/platform/filesystem facts plus explicit
protocol proof, operations, and exact repository paths; absent proof stays
`unavailable`. Confirmed closure authorization and Codex-first segmentation
come only from closed fixtures under [`decisions/`](decisions/). Applied
desired bytes must equal the replay input's independently resolved render.
Guarded rows carry the non-CAS and unavailable-strict-compensation
acknowledgements; strict-required negative rows remain `unavailable`. Parser
adversarials cover numeric, first-use bindings and reject byte-wise, gapped,
out-of-first-use, and unreferenced profiles. Guarded region adversarials cover
Unicode replacement, insertion, deletion, and a mid-code-point offset.
[`journal_validator.py`](journal_validator.py) is the fixture-bound contract
validator for the current live-journal contract, not a product runtime
implementation: `bridge-live-operation-journal/v2` validated by
`bridge-live-operation-journal-validator/v2`.
[`journal_validator_tests.py`](journal_validator_tests.py) exercises 66
positive and negative cases covering exact pre/intended/observed values,
step/protocol/binding fields, guarded region offset and bytes, repo-external
OS-temporary operation leases, exact closed-journal cleanup, sibling
preservation, retained partial evidence, and explicit v1 rejection. Each test
process owns one unique session temp root and removes only that exact root.
`--mode concurrent` starts two single-suite processes together and requires
2/2 PASS, 66 cases per worker (132 total), two unique session roots, and two
successful session cleanups. One monotonic deadline covers launch, collection,
and bounded terminate/kill/wait reaping before any worker result is validated;
failure diagnostics retain each worker's case, PID, session, return code, and
bounded stdout/stderr evidence: full byte length and digest, a fixed-size UTF-8
excerpt, and an explicit truncation flag. `--mode worker-matrix` exercises dual
success, partial launch failure, communicate timeout with kill, and malformed
JSON after all workers are reaped. It also proves launch-before-collect
ordering, one shared monotonic deadline, exact timeout reaping order, complete
bounded peer diagnostics, oversized stream truncation, and invalid UTF-8
safety. The main harness `self-test` runs the single 66-case v2 suite and binds
its journal spec, validator spec, count, and PASS result in output.
It does not pretend to execute or compensate a product write.

Coverage includes bootstrap, its independent still-untracked rescan boundary,
and tracked rerun, Claude-first and Codex-first flows,
scoped rendering and reverse adoption, protected spans, source authority,
conflict and partial selection, marker and import blockers, live activation
blockers and budgets, intent repair, delete and rename, real v1 migration
history and ambiguous DAGs, guarded-patch preflight/postverification races,
strict create/delete/rename gates, semantic review, and no-optimistic-
compensation outcomes. Use `list` for the authoritative scenario inventory.
