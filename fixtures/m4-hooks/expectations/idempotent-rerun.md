# Bridge Sync Plan

- project: idempotent-rerun
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
| hooks/fmt-on-save/claude | closure/decision/hooks/fmt-on-save | selected | 0000000000000000000000000000000000000000 | unchanged | unchanged | - | not-applicable | unchanged | native | - |
| hooks/fmt-on-save/codex | closure/decision/hooks/fmt-on-save | selected | 0000000000000000000000000000000000000000 | unchanged | unchanged | - | not-applicable | unchanged | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/fmt-on-save | hooks/fmt-on-save/claude; hooks/fmt-on-save/codex | - | selected | not-applicable | unchanged |

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

- (none)

## Evidence and notes

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.

This is the idempotence law of the `native-both-applied` result. The scan runs
against that scenario's exact post-state, so the proven managed baseline is the
initial commit and both host rows carry it.

Both owned groups are H-OK: `.claude/settings.json` holds exactly one command
handler in the owned `(PostToolUse, no matcher)` group, it is handler-equal to
the entry, and no key outside the Claude passthrough set is present;
`.codex/hooks.json` holds the same shape. `compose-hooks-json` reports
`changed: false` on both carriers, and each owned group's bytes are already
byte-identical to `render-hook-group` for that carrier's own style, so no
`hook-format-preserved` line is emitted. That warning is reserved for a group
that parses equal while its bytes differ; here nothing differs at all.

Because nothing is written, both host rows of the entry share one
`closure/decision/hooks/fmt-on-save` so a two-host decision is never split
across two closures, and that closure is a selected zero-write closure with
authorization `not-applicable`. The header authorization derives from selected
mutating closures only, so it is `not-applicable` and there is no
`authorization-incomplete` line. Both `Capability profiles` and
`Write capabilities` are `- (none)`.

The unowned `SessionStart` group whose matcher is `startup` is still neither
owned by a valid entry nor marked with a Bridge id, so it is reported once as
the informational `undeclared-hooks-key: .codex/hooks.json (SessionStart
matcher=startup)`. No `claude-hooks-shared-execution` line is emitted, because
that acknowledgement is required only when the plan selects a Claude hook
carrier write.

Formal validation record: contract `sync-plan-validator/v1`. The plan
SHA-256, the validation-context SHA-256 and the PASS result are recorded by
the live operation that serializes this document, not by this expectation.
