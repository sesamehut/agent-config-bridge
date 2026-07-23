# Bridge Sync Plan

- project: untracked-ignore
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
| skills/fixture-untracked | 9931658e8cffe387f02b2439eda7bf089eb61d9f | source-only | update | source-to-projection | applied | native | live-activation-unknown; restart-may-be-required |

## Warnings

- ignored-files-excluded: .claude/skills/fixture-untracked/assets/generated.tmp
- untracked-files-included: .claude/skills/fixture-untracked/references/new.md
