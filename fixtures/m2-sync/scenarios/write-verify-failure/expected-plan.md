# Bridge Sync Plan

- project: write-verify-failure
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
| skills/fixture-write-first | afc07dd3b9bd18b58613e5e2d1d59767315036af | source-only | update | source-to-projection | partial | native | live-activation-unknown; restart-may-be-required |
| skills/fixture-write-second | afc07dd3b9bd18b58613e5e2d1d59767315036af | source-only | update | source-to-projection | not-attempted | native | live-activation-unknown |

## Warnings

- (none)
