# Bridge Sync Plan

- project: codex-blind-change
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
| hooks/session-banner/claude | closure/decision/hooks/session-banner | selected | 0000000000000000000000000000000000000000 | unchanged | unchanged | - | not-applicable | unchanged | native | - |
| hooks/session-banner/codex | closure/hooks/codex | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | applied | native | awaiting-host-trust |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/session-banner | hooks/session-banner/claude | - | selected | not-applicable | unchanged |
| closure/hooks/codex | hooks/session-banner/codex | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- codex-trust-blind-change: .codex/hooks.json (SessionStart group=1 handler=0)
- guarded-patch-non-cas: .codex/hooks.json
- platform-branch-divergence: .claude/rules/hooks.md (entry session-banner)
- strict-compensation-unavailable: .codex/hooks.json
- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/session-banner/claude | reminder | settings-json | native | shared-event-command |
| hooks/session-banner/codex | reminder | codex-hooks-json | native | platform-command-branch |

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)

## Evidence and notes

The entry keeps the shared `command` `bridge-fixture-noop session-banner` and
retargets only `targets.codex.commandWindows`, from
`bridge-fixture-noop session-banner-windows` to
`bridge-fixture-noop session-banner-windows-v2`, under the unchanged
`override-reason: platform-command`. Claude has no counterpart field, so the
Claude projection is byte-identical to its carrier and its row is `unchanged`
with no write, no Write capabilities row and no `hook-format-preserved` line:
the bytes are equal, not merely semantically equal.

Only `.codex/hooks.json` changes, and inside the owned `SessionStart` group
the single replaced value is `commandWindows`. The handler keeps `type`,
`command` and `statusMessage` `[bridge:session-banner]` byte-for-byte, and the
top-level `description` member is untouched.

`commandWindows` is outside the normalized Codex trust identity, so the
handler's identity does not change and Codex will keep dispatching it under
the trust the user already granted, now running different Windows code. That
is disclosed as the informational `codex-trust-blind-change` with the exact
position `(SessionStart group=1 handler=0)`. It is the mutually exclusive
counterpart of `codex-hook-retrust-required`: an identity change emits the
first, a `commandWindows`-only replacement the second, and never both for one
handler. `awaiting-host-trust` records only that the Codex carrier was
written; it is not a trust state.

`SessionStart` is inside the dated `shared-events/2026-09-07` registry and
inside the stdout-delivering set on both hosts, so no `event-unverified` and
no `hook-output-not-delivered` line applies. `platform-branch-divergence` is
an acknowledged warning, not an apply blocker: Windows runs `commandWindows`
under `pwsh -NoProfile -Command` while POSIX runs `command`, so the two
platforms run different code by explicit declaration.

The unowned `SessionStart` group whose matcher is `startup` stays exactly
where the team wrote it and keeps its index 0.

The replacement uses `guarded-patch/v1` and has no attested strict inverse, so
no automatic compensation would be attempted.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.
