# Bridge Sync Plan

- project: intent-missing
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: post-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| entry | closure/agents-md | selected | 0000000000000000000000000000000000000000 | intent-missing | update | source-to-projection | confirmed | applied | structural | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | entry | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | CLAUDE.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- guarded-patch-non-cas: CLAUDE.md
- strict-compensation-unavailable: CLAUDE.md

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
