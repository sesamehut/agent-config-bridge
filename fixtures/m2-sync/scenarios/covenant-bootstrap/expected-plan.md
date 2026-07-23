# Bridge Sync Plan

- project: covenant-bootstrap
- scan root: .
- date: 2026-07-23
- expectation: sync-plan/v1
- contracts: covenant/v1, source-tree/v3, report/v3, reconciliation/v1
- phase: post-write
- onboarding: blocked
- authorization: confirmed

## Units

| unit | baseline | state | action | direction | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|
| onboarding/covenant | - | no-baseline | create | source-to-projection | applied | - | - |
| skills/fixture-covenant-bootstrap | - | no-baseline | create | source-to-projection | applied | native | live-activation-unknown; restart-may-be-required |

## Warnings

- untracked-files-included: .claude/skills/fixture-covenant-bootstrap/SKILL.md
- untracked-files-included: .claude/skills/fixture-covenant-bootstrap/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-covenant-bootstrap/bridge-intent.yaml
