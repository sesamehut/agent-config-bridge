# Bridge Sync Plan

- project: multi-unit-batch
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
| skills/fixture-auto-projection | 54a65696fe4f7c531af67648e708c463bafabbec | projection-only | adopt | projection-to-source | applied | native | intent-required; live-activation-unknown; restart-may-be-required |
| skills/fixture-auto-source | 54a65696fe4f7c531af67648e708c463bafabbec | source-only | update | source-to-projection | applied | native | live-activation-unknown; restart-may-be-required |
| skills/fixture-batch-conflict | 54a65696fe4f7c531af67648e708c463bafabbec | both-changed | conflict | user-decision | deferred | native | decision-required; live-activation-unknown |
| skills/fixture-batch-other | 54a65696fe4f7c531af67648e708c463bafabbec | unchanged | unchanged | - | unchanged | native | live-activation-unknown |

## Warnings

- unrelated-dirty-preserved: work.txt
