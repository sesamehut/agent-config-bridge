# Bridge Sync Plan

- project: skill-delete-unavailable
- scan root: .
- date: 2026-07-24
- expectation: sync-plan/v2
- contracts: covenant/v2, source-tree/v4, report/v4, reconciliation/v2
- phase: pre-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| skills/fixture-consumer | closure/skill/fixture-consumer | selected | 0000000000000000000000000000000000000000 | source-only | delete | source-to-projection | confirmed | blocked | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/skill/fixture-consumer | skills/fixture-consumer | - | selected | confirmed | blocked |

## Capability profiles

- (none)

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/skill/fixture-consumer | .agents/skills/fixture-consumer/SKILL.md | delete | unavailable | - | unavailable | - |
| 2 | closure/skill/fixture-consumer | .agents/skills/fixture-consumer/agents/openai.yaml | delete | unavailable | - | unavailable | - |
| 3 | closure/skill/fixture-consumer | .agents/skills/fixture-consumer/bridge-intent.yaml | delete | unavailable | - | unavailable | - |

## Warnings

- conditional-write-unavailable: .agents/skills/fixture-consumer/SKILL.md
- conditional-write-unavailable: .agents/skills/fixture-consumer/agents/openai.yaml
- conditional-write-unavailable: .agents/skills/fixture-consumer/bridge-intent.yaml

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)
