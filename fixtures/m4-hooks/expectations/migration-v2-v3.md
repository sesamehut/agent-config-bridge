# Bridge Sync Plan

- project: migration-v2-v3
- scan root: .
- date: 2026-09-07
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: pre-write
- onboarding: blocked
- authorization: not-applicable

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| entry | closure/migration | selected | 0000000000000000000000000000000000000000 | contract-migration | resolve-blocker | user-decision | not-applicable | blocked | structural | migration-transition-required |
| hooks/fmt-on-save/claude | closure/hooks/claude | selected | - | blocked | resolve-blocker | user-decision | not-applicable | blocked | native | - |
| hooks/fmt-on-save/codex | closure/hooks/codex | selected | - | blocked | resolve-blocker | user-decision | not-applicable | blocked | native | - |
| onboarding/covenant | closure/migration | selected | - | contract-migration | resolve-blocker | user-decision | not-applicable | blocked | - | migration-transition-required |
| rules/review | closure/migration | selected | 0000000000000000000000000000000000000000 | contract-migration | resolve-blocker | user-decision | not-applicable | blocked | structural | migration-transition-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/fmt-on-save/claude | - | selected | not-applicable | blocked |
| closure/hooks/codex | hooks/fmt-on-save/codex | - | selected | not-applicable | blocked |
| closure/migration | entry; onboarding/covenant; rules/review | - | selected | not-applicable | blocked |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- migration-closure-incomplete: .
- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/fmt-on-save/claude | observation | settings-json | native | shared-event-command |
| hooks/fmt-on-save/codex | observation | codex-hooks-json | native | shared-event-command |

## Migration decisions

| unit | legacy baseline | current relation | disposition | decision |
|---|---|---|---|---|
| entry | 0000000000000000000000000000000000000000 | converged | carry-forward | derived |
| rules/review | 0000000000000000000000000000000000000000 | converged | carry-forward | derived |

## Migration candidates

| unit | legacy candidate |
|---|---|
| entry | 0000000000000000000000000000000000000000 |
| rules/review | 0000000000000000000000000000000000000000 |

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)

## Evidence and notes

Both covenant halves are tracked, mutually coherent, and exact for the
archived `covenant/v2` pair, so the pair classifies as `contract-migration`
and the header onboarding value is `blocked` until the required tracked
postcondition is observed. The archived-pair recognizer is the closed
two-member set of `templates/covenant/v1/` and `templates/covenant/v2/`; it
is read only to identify one explicit whole-pair migration to the current
tuple, and never as a second runtime contract.

The legacy-owned set derived from the reachable archived-tuple DAG contains
exactly the unit classes `entry`, `rules/<id>`, and `skills/<name>`. Here it
is `entry` and `rules/review`, each with exactly one ancestry-maximal
candidate, the `v2-owned` commit that established them. Both already satisfy
their current-contract relation, so both are `converged` and
`carry-forward` / `derived`, and neither may silently disappear from the
migration. `onboarding/covenant` stays an indivisible member of
`closure/migration` and is excluded from both evidence tables, and no
covenant commit is serialized as a scalar baseline for the whole migration.

No `hooks/*` unit appears in Migration decisions or Migration candidates.
`reconciliation/v2` forbade every hook write, so no reachable archived-era
commit can prove a hook baseline. This tree nevertheless carries owned,
converged `fmt-on-save` groups in both carriers inside the same reachable
`v2-owned` commit, and the entry's own record says so. That is evidence of an
out-of-contract write, not a carriable baseline, so both host rows are
`blocked` / `resolve-blocker` with `user-decision`, zero writes, and their
own carrier closures outside `closure/migration`. They are a proven managed
occupancy that the closed migration set cannot carry, which is what
`migration-closure-incomplete` reports, and that gate prevents the whole
migration.

The user resolves it explicitly. After the covenant pair and the closed
carried set are prepared and the user records one reachable Git commit whose
tree carries the exact current pair and the complete closed set, a fresh scan
reconciles `fmt-on-save` through ordinary `no-baseline` / `create`
reconciliation under `source-tree/v5`, with its own initial intent record and
its own opt-in and acknowledgement gates.

`migration-transition-uncommitted` is deliberately absent. It is not emitted
merely because an old-pair pre-write plan has not yet prepared the transition
bytes; the desired current-tuple bytes do not exist in this tree yet. It
becomes required only after those bytes are prepared and while the closed
transition commit is still unreachable.

Both capability sections are `- (none)`: this plan authorizes no write, so
the migration byte preparation is not staged here and Bridge does not commit.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.
