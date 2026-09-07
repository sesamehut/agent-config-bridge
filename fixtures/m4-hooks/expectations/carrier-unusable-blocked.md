# Bridge Sync Plan

- project: carrier-unusable-blocked
- scan root: .
- date: 2026-09-07
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: pre-write
- onboarding: onboarded
- authorization: required

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| hooks/fmt-on-save/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | required | planned | native | - |
| hooks/fmt-on-save/codex | closure/hooks/codex | selected | - | blocked | resolve-blocker | user-decision | not-applicable | blocked | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/fmt-on-save/claude | - | selected | required | planned |
| closure/hooks/codex | hooks/fmt-on-save/codex | - | selected | not-applicable | blocked |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- authorization-incomplete: .
- claude-hooks-shared-execution: .claude/settings.json
- guarded-patch-non-cas: .claude/settings.json
- hook-projection-asymmetric: .codex/hooks.json (hooks/fmt-on-save/codex)
- hooks-carrier-unusable: .codex/hooks.json (duplicate-key)
- strict-compensation-unavailable: .claude/settings.json

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

`.codex/hooks.json` declares the object key `command` twice inside
`hooks.SessionStart[0].hooks[0]`. A duplicate object key makes the
correspondence between a byte span and a value non-unique, so
`locate-json-span` cannot prove which occurrence Bridge would own and a bridge
that guessed could silently drop the user's hook. This fails closed with
`hooks-carrier-unusable (duplicate-key)`, which is a closure-scoped blocker:
`closure/hooks/codex` keeps `selected` with authorization `not-applicable` and
outcome `blocked`, and is never relabelled `not-selected`.

Entry `fmt-on-save` is `class: observation`, so the all-or-nothing rule of a
`class: gate` entry does not apply and the sibling carrier may proceed.
`.claude/settings.json` carries no `hooks` key at all, so the Claude row is
H-MISSING with action `create` while the physical operation on the existing
file is `replace`. The asymmetry is disclosed once as
`hook-projection-asymmetric`. Bridge provides no cross-carrier atomicity, so
after this plan is confirmed the Claude hook can be active while the Codex
carrier still holds no owned group at all.

Resolving the blocker is a user edit of `.codex/hooks.json` outside Bridge.
A later run must reconstruct a fresh plan from the corrected bytes and
reachable Git; this plan authorizes nothing on the Codex carrier.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.
