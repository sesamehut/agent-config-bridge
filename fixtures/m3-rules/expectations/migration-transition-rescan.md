# Bridge Sync Plan

- project: migration-transition-rescan
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: onboarded
- authorization: not-applicable

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| skills/fixture-legacy-carry | closure/decision/skills/fixture-legacy-carry | selected | 0000000000000000000000000000000000000000 | unchanged | unchanged | - | not-applicable | unchanged | native | - |
| skills/fixture-legacy-repair | closure/decision/skills/fixture-legacy-repair | selected | 0000000000000000000000000000000000000000 | unchanged | unchanged | - | not-applicable | unchanged | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/skills/fixture-legacy-carry | skills/fixture-legacy-carry | - | selected | not-applicable | unchanged |
| closure/decision/skills/fixture-legacy-repair | skills/fixture-legacy-repair | - | selected | not-applicable | unchanged |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- (none)

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
