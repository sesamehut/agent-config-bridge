# M2 sync contract fixtures

These declarative vectors define expected write-side projection and adoption
contracts without turning `fixtures/` into a writable test repository. The
fixture harness validates contract data, materialization, deterministic plan
comparison, exact tree comparison, and cleanup mechanics. Its `self-test`
does not invoke `bridge-sync` and does not claim that workflow behavior passed.
Each scenario versions four kinds of evidence:

- a declarative git baseline;
- the input working tree layered over that baseline;
- one or more exact expected plans;
- an exact expected post-state for every plan branch.

Versioned history manifests are the only synthetic history. A baseline
candidate proves one managed skill unit under the current covenant with
identical source and projection git trees. Selection is by ancestry-maximal
reachable candidates, never timestamps; incomparable maximal candidates
block the unit. A scenario with no candidate does not provide directional
evidence: a source-only unit may be created, a copy-only unit needs an
annex-or-keep decision, and two unequal existing trees must stop.

## Isolation contract

Never run a mutation against files below this directory and never launch
Claude Code or Codex with a current working directory below `fixtures/`.
Use the harness from the repository root:

```text
python -B fixtures/m2-sync/fixture_harness.py self-test
python -B fixtures/m2-sync/fixture_harness.py materialize create-rerun
```

The first command is a reproducible contract-fixture self-test. A successful
result explicitly says that no `bridge-sync` workflow was executed.
`materialize` creates a new directory under the operating system temporary
directory, writes the scenario baseline, initializes and commits a
disposable git repository, and only then applies the input state. It prints
JSON containing the absolute worktree path and baseline commit.

## Agent replay

One agent-driven replay is complete only after all of these steps:

1. Run `self-test` from this repository root.
2. Run `materialize <scenario>` and retain the returned absolute worktree.
3. From outside `fixtures/`, load `skills/bridge-sync/SKILL.md`, run that
   workflow against only the returned worktree, and save its exact produced
   `sync-plan/v1` Markdown to a regular file under the OS temporary directory.
4. Compare both the produced plan and the resulting tree:

```text
python -B fixtures/m2-sync/fixture_harness.py compare create-rerun <temp-path> --expectation first-run --actual-plan <actual-plan.md>
```

5. After inspecting any mismatch, permanently remove the disposable project:

```text
python -B fixtures/m2-sync/fixture_harness.py cleanup <temp-path>
```

`compare` applies the `sync-plan/v1` deterministic expectation rule, validates
cross-field plan combinations and the expectation's assigned coverage tokens,
and compares exact post-state bytes, paths, links, and modes. Plan-only or
tree-only equality is not a replay pass.

The harness accepts only a direct child of the resolved OS temporary
directory named `bridge-sync-<known-scenario>-<nonce>`. It rejects the temp
root itself, repository-contained temp roots, links/reparse points, and any
marker that does not bind `bridge-sync-fixture-marker/v1`, resolved root,
scenario, nonce, and synthetic commits. Cleanup never traverses links or
reparse points. It clears read-only bits before removing ordinary entries,
and any cleanup failure fails the command. Cleanup is permanent.

The `create-rerun` scenario models the normal commit boundary between runs.
After the first comparison, create its synthetic test-only checkpoint before
the rerun:

```text
python -B fixtures/m2-sync/fixture_harness.py checkpoint create-rerun <temp-path> --expectation first-run
```

The Bridge workflow itself never stages or commits; this command belongs only
to disposable fixture orchestration.

`write-verify-failure` is deliberately `declarative-only`. The harness has no
real write-after-operation/before-verification barrier in an agent-driven
workflow, so it refuses to materialize or compare that scenario. Its plan,
post-tree, fault data, and coverage remain machine-validated contract data;
they are not an executable workflow result.

## Scenario format

Every `scenarios/<name>/scenario.json` uses
`bridge-sync-scenario/v1`. It names baseline and input tree manifests,
coverage claims, expectations, and optional fault operations. Each
expectation points to a `sync-plan/v1` Markdown expectation, a post-state tree
manifest, and a non-empty `covers` subset. The union of expectation coverage
must equal the scenario coverage exactly. `baseline_ref` binds every non-empty
plan baseline to the actual synthetic initial, history, or checkpoint commit.
`replay: declarative-only` requires an explicit reason and validated fault
workflow data.

Tree manifests use `bridge-sync-tree/v1`. They may extend one earlier
manifest in the same scenario and apply ordered operations:

- `write`: copy bytes from one scenario-relative `source`, concatenate a
  `sources` array, or decode inline `base64`; `mode` is `100644` or `100755`;
- `delete`: remove one path and all descendants from the logical tree;
- `symlink`: create a link/reparse-point test input with a relative target.

Paths are POSIX-style, project-relative, and may not be absolute, traverse
above the project, use backslashes, or name `.git`. Resolution produces a
complete logical tree before any bytes are written. Exact comparison covers
file bytes, missing and extra paths, link targets, and executable policy on
platforms that expose it. Binary files are never decoded as text.

Every initial-snapshot expectation must enumerate its complete scoped Git
untracked and ignored evidence with `untracked-files-included` and
`ignored-files-excluded`; the self-test compares those warning paths with the
materialized repository's Git status. An ordinary untracked file has safe
prospective mode `100644`, including on Windows. `mode-limited` is reserved
for a directional executable mismatch or an explicit executable requirement
whose mode cannot be proved or realized.

Scenario-local `source` paths resolve within that scenario. The reserved
`@shared/` prefix resolves within `m2-sync/shared/` and is used only for exact
cross-scenario contract assets such as the covenant pair.

Every materialized fixture skill is inert:

- its name begins `fixture-`;
- its body states that it is an inert fixture;
- it carries `agents/openai.yaml` with
  `policy.allow_implicit_invocation: false`;
- its materialized project settings and this repository's root settings
  disable the name through `skillOverrides`.

## Inventory

| Scenario | Declared vector |
|---|---|
| `create-rerun` | Source-only first projection followed by a byte-for-byte idempotent rerun. |
| `source-reproject` | A proven baseline followed by source replacements, deletions, ordinary untracked additions, binary changes, and separate directional executable-mode-supported and mode-limited expectations. |
| `projection-adopt` | Projection-only replacement and addition, adoption into the master with a new intent record, then exact reprojection. |
| `conflict-zero-write` | Different edits on both sides of one proven unit; the unit reports conflict and receives zero writes. |
| `manual-copy-decision` | A copy-only hand-written skill remains untouched before the annex-or-keep decision, with explicit annex and keep branches. |
| `occupied-and-links` | Targets without `SKILL.md`, targets with extra manual files, and source/target symlink or reparse-point guards. |
| `untracked-ignore` | Non-ignored untracked source files join the plan; ignored files stay out and produce a warning. |
| `multi-unit-batch` | Confirmed independent `update` and `adopt` units proceed while a conflicting unit is isolated; unrelated dirty files, manual `AGENTS.md`, and another skill remain exact. |
| `covenant-bootstrap` | Covenant bytes are bootstrapped without hooks and a pre-existing `AGENTS.md` manual zone is preserved byte-for-byte; the post-write header remains blocked until the new pair is tracked outside Bridge. |
| `write-verify-failure` | Declarative-only: a post-write mismatch yields `partial`, later closures are `not-attempted`, and reviewable evidence remains. |
| `behavior-degraded` | Mechanical native copy with a behavioral-degradation warning and a neutral live-activation note. |
| `baseline-dag-ambiguous` | Two mutually incomparable ancestry-maximal synchronized commits in a merge DAG; time ordering is forbidden and the unit receives zero writes. |
| `covenant-partial-blocked` | A lone tracked covenant half blocks the project and produces an explicitly confirmed atomic repair plan; it proves neither onboarding nor ownership. |

Plan vocabulary is pinned by the M2 sync-plan specification. The fixture
self-test rejects any expectation whose header, unit table, registry token,
cross-field combination, annotation order, warning order, or synthetic
baseline does not match `sync-plan/v1`.

[`verification-safeguards.json`](verification-safeguards.json) records
machine-validated declarative zero-write, transaction, compensation, failure,
and rollback invariants that do not need another large byte tree. Its explicit
schema,
closed registries, sorted unique IDs, and complete required-case set are part
of `self-test`. These review contracts do not execute `bridge-sync` and do not
substitute for agent replay of the 12 replayable vectors.
Successful automatic operation-local compensation is `compensated`, not
`rolled-back`; the latter is a later operation with a new plan and new user
confirmation. A compensation guard, restore, or proof failure is `partial`
and preserves its reviewable diff.
An untracked covenant carrying an older tuple must pass through an explicitly
confirmed repair and a subsequent tracked-closure proof first; only a later
explicit plan may migrate it.
