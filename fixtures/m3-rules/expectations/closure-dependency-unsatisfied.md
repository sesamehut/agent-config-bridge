# Bridge Sync Plan

- project: closure-dependency-unsatisfied
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: onboarded
- authorization: required

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| skills/fixture-consumer | closure/skill/fixture-consumer | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | planned | native | - |
| skills/fixture-prerequisite | closure/skill/fixture-prerequisite | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | required | planned | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/skill/fixture-consumer | skills/fixture-consumer | closure/skill/fixture-prerequisite | selected | confirmed | planned |
| closure/skill/fixture-prerequisite | skills/fixture-prerequisite | - | selected | required | planned |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/skill/fixture-prerequisite | .agents/skills/fixture-prerequisite/SKILL.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/skill/fixture-prerequisite | .agents/skills/fixture-prerequisite/bridge-intent.yaml | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 3 | closure/skill/fixture-consumer | .agents/skills/fixture-consumer/SKILL.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 4 | closure/skill/fixture-consumer | .agents/skills/fixture-consumer/bridge-intent.yaml | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- authorization-incomplete: .
- closure-dependency-unsatisfied: .
- guarded-patch-non-cas: .agents/skills/fixture-consumer/SKILL.md
- guarded-patch-non-cas: .agents/skills/fixture-consumer/bridge-intent.yaml
- guarded-patch-non-cas: .agents/skills/fixture-prerequisite/SKILL.md
- guarded-patch-non-cas: .agents/skills/fixture-prerequisite/bridge-intent.yaml
- strict-compensation-unavailable: .agents/skills/fixture-consumer/SKILL.md
- strict-compensation-unavailable: .agents/skills/fixture-consumer/bridge-intent.yaml
- strict-compensation-unavailable: .agents/skills/fixture-prerequisite/SKILL.md
- strict-compensation-unavailable: .agents/skills/fixture-prerequisite/bridge-intent.yaml

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
