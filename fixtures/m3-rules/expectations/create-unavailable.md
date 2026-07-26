# Bridge Sync Plan

- project: create-unavailable
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: bootstrap-required
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| onboarding/covenant | closure/agents-md | selected | - | no-baseline | create | source-to-projection | confirmed | blocked | - | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | onboarding/covenant | - | selected | confirmed | blocked |

## Capability profiles

- (none)

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | .claude/rules/bridge-covenant.md | create | unavailable | - | unavailable | - |
| 2 | closure/agents-md | AGENTS.md | create | unavailable | - | unavailable | - |

## Warnings

- conditional-write-unavailable: .claude/rules/bridge-covenant.md
- conditional-write-unavailable: AGENTS.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
