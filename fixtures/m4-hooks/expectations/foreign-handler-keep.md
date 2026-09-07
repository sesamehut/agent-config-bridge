# Bridge Sync Plan

- project: foreign-handler-keep
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
| hooks/fmt-on-save/claude | closure/decision/hooks/fmt-on-save | not-selected | - | no-baseline | annex-or-keep | user-decision | not-applicable | not-selected | native | decision-required |
| hooks/fmt-on-save/codex | closure/decision/hooks/fmt-on-save | not-selected | - | unchanged | unchanged | - | not-applicable | not-selected | native | decision-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/fmt-on-save | hooks/fmt-on-save/claude; hooks/fmt-on-save/codex | - | not-selected | not-applicable | not-selected |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

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
| handler/1 | .claude/settings.json#PostToolUse[0][1] | keep | - | pending |

## Evidence and notes

`inspect-hooks-json --host claude .claude/settings.json` reports the owned
`(PostToolUse, omitted)` group with two handlers: handler 0 is a command
handler that is handler-equal to entry `fmt-on-save`, and handler 1 declares
`type: mcp_tool` with `server`, `tool` and a nested `input` object. A
non-command handler makes the group occupied rather than empty, so
H-FOREIGN-HANDLER runs before H-MISSING and the Claude row is routed to
`annex-or-keep`.

`mcp_tool` is in the never-project set, so Bridge writes no such handler and,
above all, never deletes one. Until the user records an ownership decision for
`.claude/settings.json#PostToolUse[0][1]`, both host rows stay in one
not-selected `closure/decision/hooks/fmt-on-save`, this plan writes nothing on
either host, and both capability sections stay empty. `discard` would be
destructive and would need its own explicit confirmation.

The Codex carrier is already handler-equal to the entry, so its row is
`unchanged`. Its `SessionStart` group with matcher `startup` is neither owned
by a valid entry nor marked with a Bridge id, so it is disclosed once as
`undeclared-hooks-key` and is never rewritten.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.
