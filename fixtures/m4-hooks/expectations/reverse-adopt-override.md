# Bridge Sync Plan

- project: reverse-adopt-override
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
| hooks/session-banner/codex | closure/hooks/source | selected | 0000000000000000000000000000000000000000 | projection-only | adopt | projection-to-source | confirmed | applied | native | - |
| hooks/session-banner/source | closure/hooks/source | selected | 0000000000000000000000000000000000000000 | projection-only | adopt | projection-to-source | confirmed | applied | - | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/session-banner | hooks/session-banner/claude | - | selected | not-applicable | unchanged |
| closure/hooks/source | hooks/session-banner/codex; hooks/session-banner/source | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/source | .claude/rules/hooks.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- guarded-patch-non-cas: .claude/rules/hooks.md
- platform-branch-divergence: .claude/rules/hooks.md (entry session-banner)
- strict-compensation-unavailable: .claude/rules/hooks.md
- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/session-banner/claude | reminder | settings-json | native | shared-event-command |
| hooks/session-banner/codex | reminder | codex-hooks-json | native | platform-command-branch |
| hooks/session-banner/source | reminder | - | - | - |

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)

## Evidence and notes

The user hand-edited only `commandWindows` of the owned `SessionStart` handler
in `.codex/hooks.json`, from `bridge-fixture-noop session-banner-windows` to
`bridge-fixture-noop session-banner-windows-hand`. The Claude carrier has no
counterpart field, so the other host's value is neither unchanged-and-equal nor
adoptable, and the changed value never collapses into the shared `command`
scalar. It is adopted as `targets.codex.commandWindows` with
`override-reason: platform-command`, and the entry appends the dated
`bridge:intent` record that the adoption requires. The shared scalar
`bridge-fixture-noop session-banner` is byte-identical before and after the
write.

Only `.claude/rules/hooks.md` is written. Neither hook carrier is touched:
`.claude/settings.json` and `.codex/hooks.json` are byte-identical to their
input bytes, so no rerender of the other host's carrier is needed and no
`codex-hook-retrust-required` or `codex-trust-blind-change` line applies. The
Codex trust identity does not cover `commandWindows`, which is why the file the
user edited already carries the value Bridge now records.

`SessionStart` is inside the dated `shared-events/2026-09-07` registry and
inside the stdout-delivering set on both hosts, so no `event-unverified` and no
`hook-output-not-delivered` line applies. `platform-branch-divergence` is an
acknowledged warning, not an apply blocker: Windows runs `commandWindows` under
`pwsh -NoProfile -Command` while POSIX runs `command`, so the two platforms run
different code by explicit declaration.

The unowned `SessionStart` group whose matcher is `startup` stays exactly where
the team wrote it, and the top-level `description` member is untouched.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.
