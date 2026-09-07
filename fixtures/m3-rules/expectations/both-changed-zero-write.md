# Bridge Sync Plan

- project: both-changed-zero-write
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
| entry | closure/decision/entry | selected | 0000000000000000000000000000000000000000 | both-changed | conflict | user-decision | required | deferred | structural | decision-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/entry | entry | - | selected | required | deferred |

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
