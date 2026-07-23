# Bridge Sync Plan

- project: manual-copy-decision
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
| skills/fixture-manual-copy | - | no-baseline | annex | projection-to-source | applied | native | intent-required; live-activation-unknown; restart-may-be-required |

## Warnings

- untracked-files-included: .agents/skills/fixture-manual-copy/SKILL.md
- untracked-files-included: .agents/skills/fixture-manual-copy/agents/openai.yaml
