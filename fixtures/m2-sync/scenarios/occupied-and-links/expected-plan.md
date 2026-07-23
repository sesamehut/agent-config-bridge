# Bridge Sync Plan

- project: occupied-and-links
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
| skills/fixture-extra-files | - | no-baseline | annex-or-keep | user-decision | deferred | - | decision-required; live-activation-unknown |
| skills/fixture-no-skill | - | no-baseline | annex-or-keep | user-decision | deferred | - | decision-required |
| skills/fixture-source-link | - | blocked | resolve-blocker | - | blocked | native | - |
| skills/fixture-target-link | - | blocked | resolve-blocker | - | blocked | native | - |

## Warnings

- unsafe-tree-entry: .agents/skills/fixture-target-link (reparse point)
- unsafe-tree-entry: .claude/skills/fixture-source-link/references/linked.txt (symlink)
- untracked-files-included: .agents/skills/fixture-extra-files/SKILL.md
- untracked-files-included: .agents/skills/fixture-extra-files/agents/openai.yaml
- untracked-files-included: .agents/skills/fixture-extra-files/manual-note.md
- untracked-files-included: .agents/skills/fixture-no-skill/README.md
- untracked-files-included: .agents/skills/fixture-no-skill/agents/openai.yaml
- untracked-files-included: .agents/skills/fixture-target-link
- untracked-files-included: .claude/skills/fixture-extra-files/SKILL.md
- untracked-files-included: .claude/skills/fixture-extra-files/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-no-skill/SKILL.md
- untracked-files-included: .claude/skills/fixture-no-skill/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-source-link/SKILL.md
- untracked-files-included: .claude/skills/fixture-source-link/agents/openai.yaml
- untracked-files-included: .claude/skills/fixture-source-link/references/linked.txt
- untracked-files-included: .claude/skills/fixture-target-link/SKILL.md
- untracked-files-included: .claude/skills/fixture-target-link/agents/openai.yaml
