# Bridge Sync Plan

- project: covenant-partial-blocked
- scan root: .
- date: 2026-07-23
- expectation: sync-plan/v1
- contracts: covenant/v1, source-tree/v3, report/v3, reconciliation/v1
- phase: pre-write
- onboarding: blocked
- authorization: required

## Units

| unit | baseline | state | action | direction | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|
| onboarding/covenant | - | blocked | repair | user-decision | planned | - | decision-required |
| skills/fixture-covenant-partial | - | blocked | resolve-blocker | - | blocked | native | - |

## Warnings

- untracked-files-included: .claude/skills/fixture-covenant-partial/SKILL.md
- untracked-files-included: .claude/skills/fixture-covenant-partial/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-covenant-partial/bridge-intent.yaml
