# Bridge Sync Plan

- project: format-preserved-unchanged
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

- hook-format-preserved: .claude/settings.json
- hook-format-preserved: .codex/hooks.json

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

Both carriers were written by hand with a four-space outer indent,
tab-indented handler bodies and handler keys in a different order than Bridge
renders. `.claude/settings.json` writes `statusMessage` before `timeout` and
`command`; `.codex/hooks.json` writes `timeout` before `command`. Neither
difference is semantic: `source-tree/v5` compares parsed scalar values after
stripping leading and trailing ASCII whitespace, and key order in a JSON object
carries no meaning.

Both owned groups are therefore H-OK and both host rows are
`unchanged`/`unchanged` with the proven initial-commit baseline.
`compose-hooks-json` reports `changed: false` and `idempotent: true` for both
carriers, so the composed image equals the preimage byte for byte and Bridge
writes nothing. Comparing each owned group's bytes with `render-hook-group`
under that carrier's own observed style shows they are not equal, which is
exactly the `hook-format-preserved` condition: the group already parses equal
to its desired model while its bytes differ. One informational line is emitted
per affected carrier.

Bridge never reformats a converged group. Reindenting or reordering the handler
keys here would be a pure churn write, and on the Codex carrier it would also
change the normalized trust identity and force a re-trust of a handler the user
already reviewed.

The zero-write rows share one `closure/decision/hooks/fmt-on-save`, the header
authorization is `not-applicable`, and both `Capability profiles` and
`Write capabilities` are `- (none)`. `.codex/hooks.json` in this fixture holds
only the owned `PostToolUse` group, so no `undeclared-hooks-key` line applies.

Formal validation record: contract `sync-plan-validator/v1`. The plan
SHA-256, the validation-context SHA-256 and the PASS result are recorded by
the live operation that serializes this document, not by this expectation.
