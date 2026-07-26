# Bridge Sync Plan

- project: guarded-patch-unavailable
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| entry | closure/agents-md | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | blocked | structural | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | entry | - | selected | confirmed | blocked |

## Capability profiles

- (none)

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | AGENTS.md | replace | unavailable | - | unavailable | - |

## Warnings

- guarded-patch-unavailable: AGENTS.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
