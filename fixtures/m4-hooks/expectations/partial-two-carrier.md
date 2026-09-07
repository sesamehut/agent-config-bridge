# Bridge Sync Plan

- project: partial-two-carrier
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
| hooks/fmt-on-save/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | - |
| hooks/fmt-on-save/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | confirmed | partial | native | awaiting-host-trust |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/fmt-on-save/claude | - | selected | confirmed | applied |
| closure/hooks/codex | hooks/fmt-on-save/codex | - | selected | confirmed | partial |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |
| capability/2 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/2 | unavailable | - |

## Warnings

- claude-hooks-shared-execution: .claude/settings.json
- guarded-patch-non-cas: .claude/settings.json
- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .claude/settings.json
- strict-compensation-unavailable: .codex/hooks.json
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

This scenario is `replay: declarative-only`. Its bound fault kind is
`post-write-verification` at the checkpoint "after the Codex carrier write
and before post-write verification". The agent workflow exposes no reliable
fault barrier inside the Codex guarded host call between the write and its
verification, so the declared outcome is validated rather than executed. No
fault adapter runs and no host is started.

Step 1 wrote the owned `PostToolUse` group into `.claude/settings.json`, and
its complete-image postverification passed, so `closure/hooks/claude` is
`applied`. Step 2 wrote `.codex/hooks.json` and its post-write verification
did not reproduce the intended complete post value, so the exact applied or
exact pre-write state of that closure cannot be proven and
`closure/hooks/codex` is `partial`. `partial` is the correct outcome, not
`failed`: mutation began. `awaiting-host-trust` records only that the Codex
carrier was written or may have been written; it is neutral and is not a
trust state.

No compensation was attempted. Both forward operations use
`guarded-patch/v1`, guarded patch is never an inverse protocol, and neither
operation has an attested strict inverse, which is exactly what the two
acknowledged `strict-compensation-unavailable` lines say. Automatic
compensation is attempted only when every required inverse row is strict, so
Bridge did not try an optimistic reverse write over a value it cannot prove.
Any later reverse operation needs a new plan and a new confirmation
reconstructed from current bytes plus reachable Git; this journal is not a
rollback store and is never reused.

Asymmetric enforcement statement. Bridge provides no cross-carrier
atomicity, so this repository is now in a state where the Claude hook is
active and the Codex counterpart is unproven. That is acceptable here only
because `fmt-on-save` is `class: observation`, for which one carrier may
apply while the sibling carrier is blocked, unavailable or partial. Had the
entry been `class: gate`, the entry would be all-or-nothing: a blocked or
unavailable carrier forces the sibling carrier closure to `not-selected`
with zero writes, because asymmetric enforcement is worse than no
enforcement. Review both carriers before relying on this hook.

Hook execution is observed but not guaranteed on either host, so no Bridge
state may be read as a runtime guarantee.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.
