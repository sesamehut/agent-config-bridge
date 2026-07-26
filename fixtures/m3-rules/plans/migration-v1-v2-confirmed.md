# Bridge Sync Plan

- project: migration-v1-v2
- scan root: .
- date: 2026-07-24
- spec: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: blocked
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| onboarding/covenant | closure/migration | selected | - | contract-migration | migrate | user-decision | confirmed | planned | - | migration-transition-required |
| skills/fixture-legacy-carry | closure/migration | selected | 0000000000000000000000000000000000000000 | contract-migration | migrate | user-decision | confirmed | planned | native | migration-transition-required |
| skills/fixture-legacy-release | closure/migration | selected | - | contract-migration | migrate | user-decision | confirmed | planned | native | - |
| skills/fixture-legacy-repair | closure/migration | selected | 0000000000000000000000000000000000000000 | contract-migration | migrate | user-decision | confirmed | planned | native | migration-transition-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/migration | onboarding/covenant; skills/fixture-legacy-carry; skills/fixture-legacy-release; skills/fixture-legacy-repair | - | selected | confirmed | planned |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/migration | .claude/rules/bridge-covenant.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/migration | .agents/skills/fixture-legacy-repair/SKILL.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 3 | closure/migration | AGENTS.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- guarded-patch-non-cas: .agents/skills/fixture-legacy-repair/SKILL.md
- guarded-patch-non-cas: .claude/rules/bridge-covenant.md
- guarded-patch-non-cas: AGENTS.md
- manual-zone-guarded: AGENTS.md
- strict-compensation-unavailable: .agents/skills/fixture-legacy-repair/SKILL.md
- strict-compensation-unavailable: .claude/rules/bridge-covenant.md
- strict-compensation-unavailable: AGENTS.md

## Migration decisions

| unit | legacy baseline | current relation | disposition | decision |
|---|---|---|---|---|
| skills/fixture-legacy-carry | 0000000000000000000000000000000000000000 | converged | carry-forward | derived |
| skills/fixture-legacy-release | 0000000000000000000000000000000000000000 | missing | release | confirmed |
| skills/fixture-legacy-repair | 0000000000000000000000000000000000000000 | repair-required | repair-and-carry | confirmed |

## Migration candidates

| unit | legacy candidate |
|---|---|
| skills/fixture-legacy-carry | 0000000000000000000000000000000000000000 |
| skills/fixture-legacy-release | 0000000000000000000000000000000000000000 |
| skills/fixture-legacy-repair | 0000000000000000000000000000000000000000 |

## Adoption decisions

- (none)
