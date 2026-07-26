# Bridge Sync Plan

- project: fallback-shadow
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: bootstrap-required
- authorization: not-applicable

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| onboarding/covenant | closure/decision/onboarding/covenant | selected | - | blocked | resolve-blocker | user-decision | not-applicable | blocked | - | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/onboarding/covenant | onboarding/covenant | - | selected | not-applicable | blocked |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- fallback-shadow: BRIDGE_FALLBACK.md
- untracked-files-included: .codex/config.toml
- untracked-files-included: BRIDGE_FALLBACK.md
- untracked-files-included: CLAUDE.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
