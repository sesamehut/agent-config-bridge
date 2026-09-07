# Bridge Sync Plan

- project: semantics-divergent-annex
- scan root: .
- date: 2026-09-07
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: pre-write
- onboarding: onboarded
- authorization: not-applicable

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| hooks/fmt-on-save/claude | closure/decision/hooks/fmt-on-save | not-selected | - | unchanged | unchanged | - | not-applicable | not-selected | native | decision-required |
| hooks/fmt-on-save/codex | closure/decision/hooks/fmt-on-save | not-selected | - | no-baseline | annex-or-keep | user-decision | not-applicable | not-selected | native | decision-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/fmt-on-save | hooks/fmt-on-save/claude; hooks/fmt-on-save/codex | - | not-selected | not-applicable | not-selected |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- (none)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/fmt-on-save/claude | observation | settings-json | native | shared-event-command |
| hooks/fmt-on-save/codex | observation | codex-hooks-json | native | shared-event-command |

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

| handler | location | disposition | destination | decision |
|---|---|---|---|---|
| handler/1 | .codex/hooks.json#PostToolUse[0][0] | keep | - | pending |

## Evidence and notes

`inspect-hooks-json --host codex .codex/hooks.json` reports the owned
`(PostToolUse, omitted)` group with exactly one command handler whose declared
fields all equal entry `fmt-on-save`, plus the semantics-changing key
`async: true`. Claude honors neither the stdout nor the JSON decision of an
async handler and does not enforce its timeout, and Codex runs it in the
background, so classifying the key as passthrough would report `in-sync` while
the projected semantics diverge from the intent document.

No ownership decision has been recorded yet, so both host rows stay in one
not-selected `closure/decision/hooks/fmt-on-save` and the proposed disposition
`keep` for `.codex/hooks.json#PostToolUse[0][0]` is still `pending`. This plan
writes nothing on either host and proposes no capability. The user must choose
`annex` or `keep` before any Codex carrier write is planned, and `discard`
would be destructive and would need its own explicit confirmation.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.
