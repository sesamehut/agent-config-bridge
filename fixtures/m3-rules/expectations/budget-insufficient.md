# Bridge Sync Plan

- project: budget-insufficient
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
| entry | closure/decision/entry | selected | 0000000000000000000000000000000000000000 | blocked | resolve-blocker | user-decision | not-applicable | blocked | structural | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/entry | entry | - | selected | not-applicable | blocked |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- agents-md-budget-exceeded: AGENTS.md (2997 bytes of 2200)
- untracked-files-included: .codex/config.toml

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
