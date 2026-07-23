# Bridge Sync Plan

- project: manual-copy-decision
- scan root: .
- date: 2026-07-23
- expectation: sync-plan/v1
- contracts: covenant/v1, source-tree/v3, report/v3, reconciliation/v1
- phase: pre-write
- onboarding: onboarded
- authorization: required

## Units

| unit | baseline | state | action | direction | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|
| skills/fixture-manual-copy | - | no-baseline | annex-or-keep | user-decision | deferred | - | decision-required; live-activation-unknown |

## Warnings

- untracked-files-included: .agents/skills/fixture-manual-copy/SKILL.md
- untracked-files-included: .agents/skills/fixture-manual-copy/agents/openai.yaml
