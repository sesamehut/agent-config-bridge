# Bridge Sync Plan

- project: rename-rule
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: pre-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| rules/new | closure/agents-md | selected | - | no-baseline | rename | source-to-projection | confirmed | blocked | structural | - |
| rules/old | closure/agents-md | selected | 0000000000000000000000000000000000000000 | source-only | rename | source-to-projection | confirmed | blocked | structural | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | rules/new; rules/old | - | selected | confirmed | blocked |

## Capability profiles

- (none)

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | .claude/rules/old.md | delete | unavailable | - | unavailable | - |
| 2 | closure/agents-md | AGENTS.md | replace | unavailable | - | unavailable | - |

## Warnings

- conditional-write-unavailable: .claude/rules/old.md
- conditional-write-unavailable: AGENTS.md
- untracked-files-included: .claude/rules/new.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
