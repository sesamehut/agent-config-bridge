# Bridge Sync Plan

- project: migration-ambiguous-dag
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: blocked
- authorization: not-applicable

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| onboarding/covenant | closure/migration | selected | - | contract-migration | resolve-blocker | user-decision | not-applicable | blocked | - | migration-transition-required |
| skills/fixture-legacy-carry | closure/migration | selected | - | contract-migration | resolve-blocker | user-decision | not-applicable | blocked | native | decision-required |
| skills/fixture-legacy-release | closure/migration | selected | - | contract-migration | resolve-blocker | user-decision | not-applicable | blocked | native | migration-transition-required |
| skills/fixture-legacy-repair | closure/migration | selected | - | contract-migration | resolve-blocker | user-decision | not-applicable | blocked | native | migration-transition-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/migration | onboarding/covenant; skills/fixture-legacy-carry; skills/fixture-legacy-release; skills/fixture-legacy-repair | - | selected | not-applicable | blocked |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- ambiguous-baseline: .
- migration-closure-incomplete: .

## Migration decisions

| unit | legacy baseline | current relation | disposition | decision |
|---|---|---|---|---|
| skills/fixture-legacy-carry | - | ambiguous | block | pending |
| skills/fixture-legacy-release | 3333333333333333333333333333333333333333 | converged | carry-forward | derived |
| skills/fixture-legacy-repair | 3333333333333333333333333333333333333333 | converged | carry-forward | derived |

## Migration candidates

| unit | legacy candidate |
|---|---|
| skills/fixture-legacy-carry | 1111111111111111111111111111111111111111 |
| skills/fixture-legacy-carry | 2222222222222222222222222222222222222222 |
| skills/fixture-legacy-release | 3333333333333333333333333333333333333333 |
| skills/fixture-legacy-repair | 3333333333333333333333333333333333333333 |

## Adoption decisions

- (none)
