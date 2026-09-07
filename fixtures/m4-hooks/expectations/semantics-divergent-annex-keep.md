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
| hooks/fmt-on-save/claude | closure/decision/hooks/fmt-on-save | selected | - | unchanged | keep | user-decision | not-applicable | deferred | native | - |
| hooks/fmt-on-save/codex | closure/decision/hooks/fmt-on-save | selected | - | no-baseline | keep | user-decision | not-applicable | deferred | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/fmt-on-save | hooks/fmt-on-save/claude; hooks/fmt-on-save/codex | - | selected | not-applicable | deferred |

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
| handler/1 | .codex/hooks.json#PostToolUse[0][0] | keep | - | confirmed |

## Evidence and notes

`inspect-hooks-json --host codex .codex/hooks.json` reports the owned
`(PostToolUse, omitted)` group with exactly one command handler whose declared
fields all equal entry `fmt-on-save`, plus the semantics-changing key
`async: true`. That key is never a passthrough key, so the row is
H-SEMANTICS-DIVERGENT and resolves only through `annex-or-keep`.

The user confirmed `keep`. Both host rows therefore stay in one
`closure/decision/hooks/fmt-on-save`, the entry stays unresolved, and this
operation writes nothing. Bridge never deletes a user key: the exact preimage
of `.codex/hooks.json`, including `async: true`, remains the current carrier
byte image, and the Claude carrier is already handler-equal to the entry.
`keep` is deferred rather than unchanged, so a later run must resolve the same
occupancy decision again from current bytes.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.
