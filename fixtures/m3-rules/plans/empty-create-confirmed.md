# Bridge Sync Plan

- project: empty-create
- scan root: .
- date: 2026-07-24
- spec: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: bootstrap-required
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| onboarding/covenant | closure/agents-md | selected | - | no-baseline | create | source-to-projection | confirmed | planned | - | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | onboarding/covenant | - | selected | confirmed | planned |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-create-v1 | python-exclusive-create/v1 | other | exclusive-create/v1; safe-parent/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | .claude/rules/bridge-covenant.md | create | strict-create/v1 | capability/1 | unavailable | - |
| 2 | closure/agents-md | AGENTS.md | create | strict-create/v1 | capability/1 | unavailable | - |

## Warnings

- strict-compensation-unavailable: .claude/rules/bridge-covenant.md
- strict-compensation-unavailable: AGENTS.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
