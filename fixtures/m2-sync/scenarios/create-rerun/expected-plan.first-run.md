# Bridge Sync Plan

- project: create-rerun
- scan root: .
- date: 2026-07-23
- expectation: sync-plan/v1
- contracts: covenant/v1, source-tree/v3, report/v3, reconciliation/v1
- phase: post-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | baseline | state | action | direction | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|
| skills/fixture-create | - | no-baseline | create | source-to-projection | applied | native | live-activation-unknown; restart-may-be-required |

## Warnings

- untracked-files-included: .claude/skills/fixture-create/SKILL.md
- untracked-files-included: .claude/skills/fixture-create/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-create/bridge-intent.yaml
