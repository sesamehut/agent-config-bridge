# Bridge Sync Plan

- project: invalid-rule-paths
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
| rules/invalid | closure/decision/rules/invalid | selected | - | blocked | resolve-blocker | user-decision | not-applicable | blocked | semantic | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/rules/invalid | rules/invalid | - | selected | not-applicable | blocked |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- invalid-rule-paths: .claude/rules/invalid.md (no-op-universal)
- untracked-files-included: .claude/rules/invalid.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
