# Bridge Sync Plan

- project: source-update
- scan root: .
- date: 2026-07-24
- spec: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| entry | closure/agents-md | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | planned | structural | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | entry | - | selected | confirmed | planned |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | AGENTS.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- guarded-patch-non-cas: AGENTS.md
- manual-zone-guarded: AGENTS.md
- strict-compensation-unavailable: AGENTS.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
