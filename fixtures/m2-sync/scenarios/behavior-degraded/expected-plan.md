# Bridge Sync Plan

- project: behavior-degraded
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
| skills/fixture-allowed-tools | - | no-baseline | create | source-to-projection | applied | native | behavior-degraded; live-activation-unknown; restart-may-be-required |
| skills/fixture-at-path-static | - | no-baseline | create | source-to-projection | applied | native | live-activation-unknown; restart-may-be-required |
| skills/fixture-dynamic-content | - | no-baseline | create | source-to-projection | applied | native | behavior-degraded; live-activation-unknown; restart-may-be-required |

## Warnings

- untracked-files-included: .claude/skills/fixture-allowed-tools/SKILL.md
- untracked-files-included: .claude/skills/fixture-allowed-tools/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-allowed-tools/bridge-intent.yaml
- untracked-files-included: .claude/skills/fixture-at-path-static/SKILL.md
- untracked-files-included: .claude/skills/fixture-at-path-static/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-at-path-static/bridge-intent.yaml
- untracked-files-included: .claude/skills/fixture-at-path-static/references/example.md
- untracked-files-included: .claude/skills/fixture-dynamic-content/SKILL.md
- untracked-files-included: .claude/skills/fixture-dynamic-content/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-dynamic-content/bridge-intent.yaml
- validator-profile-mismatch: .claude/skills/fixture-dynamic-content/SKILL.md
