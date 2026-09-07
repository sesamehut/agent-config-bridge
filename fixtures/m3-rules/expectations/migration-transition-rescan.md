# Bridge Sync Plan

- project: migration-transition-rescan
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
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

## Hook tiers

- (none)

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)
