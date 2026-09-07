# Bridge Sync Plan

- project: reverse-adopt-command
- scan root: .
- date: 2026-09-07
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: post-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| hooks/fmt-on-save/claude | closure/hooks/source | selected | 0000000000000000000000000000000000000000 | projection-only | adopt | projection-to-source | confirmed | applied | native | - |
| hooks/fmt-on-save/codex | closure/hooks/codex | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | applied | native | awaiting-host-trust |
| hooks/fmt-on-save/source | closure/hooks/source | selected | 0000000000000000000000000000000000000000 | projection-only | adopt | projection-to-source | confirmed | applied | - | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/codex | hooks/fmt-on-save/codex | closure/hooks/source | selected | confirmed | applied |
| closure/hooks/source | hooks/fmt-on-save/claude; hooks/fmt-on-save/source | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |
| capability/2 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/source | .claude/rules/hooks.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/2 | unavailable | - |

## Warnings

- codex-hook-retrust-required: .codex/hooks.json (PostToolUse group=0 handler=0)
- guarded-patch-non-cas: .claude/rules/hooks.md
- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .claude/rules/hooks.md
- strict-compensation-unavailable: .codex/hooks.json
- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/fmt-on-save/claude | observation | settings-json | native | shared-event-command |
| hooks/fmt-on-save/codex | observation | codex-hooks-json | native | shared-event-command |
| hooks/fmt-on-save/source | observation | - | - | - |

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)

## Evidence and notes

The baseline commit carries the converged pair, so `compare-hook-handler
--event PostToolUse` proves a unique managed baseline for both carriers. Only
`.claude/settings.json` differs from it: its owned handler now runs
`bridge-fixture-noop fmt-on-save-hand`. That is H-FIELD-DIFF with a proven
baseline on the projection side alone, so the entry is `projection-only` and
the confirmed direction is `projection-to-source`. Bridge writes no byte of
`.claude/settings.json`: the hand-edited value is the value being adopted, and
after the source is updated the Claude carrier is already handler-equal to it.

The adoption changes the shared scalar `command` in
`.claude/rules/hooks.md`, so both the projection row and the source row belong
to `closure/hooks/source`, which is the only closure that writes that file.
Adoption also requires a source intent record, so the confirmed source bytes
append a second dated `intent` entry beside the initial declaration; the row
carried `intent-required` until those exact bytes existed and no longer does.

Before confirmation the plan showed the exact rerendered
`.codex/hooks.json` bytes that the adopted source produces, composed with
`json-owned-span/v1` from the current preimage rather than by reserializing the
parsed document, so the user reviewed the other host's result rather than a
description of it. `closure/hooks/codex` depends on `closure/hooks/source` and
runs after it in step order, so the Codex carrier is never rendered from a
source the user has not accepted. The unowned `SessionStart` group with matcher
`startup` and the file level `description` are outside every owned span and are
byte-identical after the write.

Changing `command` changes the Codex normalized trust identity of
`.codex/hooks.json#PostToolUse[0][0]`, so the handler is listed as modified and
is silently skipped at dispatch until the user reviews it in `/hooks`. That is
`codex-hook-retrust-required` plus `awaiting-host-trust` on the Codex row, and
neither is a trust state. Both guarded replacements leave a residual race
between preflight and postverification, and neither has an attested strict
inverse, so no automatic compensation would be attempted.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.
