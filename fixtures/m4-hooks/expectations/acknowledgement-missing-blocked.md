# Bridge Sync Plan

- project: acknowledgement-missing-blocked
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
| hooks/fmt-on-save/claude | closure/hooks/claude | selected | - | blocked | resolve-blocker | user-decision | not-applicable | blocked | native | - |
| hooks/fmt-on-save/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | required | planned | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/fmt-on-save/claude | - | selected | not-applicable | blocked |
| closure/hooks/codex | hooks/fmt-on-save/codex | - | selected | required | planned |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- authorization-incomplete: .
- guarded-patch-non-cas: .codex/hooks.json
- hook-acknowledgement-missing: .claude/rules/hooks.md
- hook-projection-asymmetric: .claude/settings.json (hooks/fmt-on-save/claude)
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

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.

`.claude/rules/hooks.md` carries the `bridge:intent` comment on line 1 but no
file-level `bridge:hooks-shared-execution` comment, so the entry heading sits
on line 5 and the fenced `yaml` block opens on line 13. Entry `fmt-on-save`
declares `targets.claude.surface: settings-json`, so the first Claude hook
carrier write of this project would commit a command that every clone runs
without a trust prompt while nobody has recorded that they accepted it.
`shared-execution-unacknowledged` is one of the two non-invalidating reasons of
the `source-tree/v5` reason registry: it emits no `intent-doc-anomaly`, leaves
every unit row of the entry intact, and is reported by the write side as
`hook-acknowledgement-missing` on `closure/hooks/claude`.

The `hook opt-in` gate is one of the three closure-scoped gates, so the
prohibition covers `closure/hooks/claude` and every closure that depends on it
and nothing else. `closure/hooks/codex` depends on no other closure, so it
stays selected and proceeds. The blocked Claude closure keeps `selected` with
authorization `not-applicable` and outcome `blocked`; it is never relabelled
`not-selected`, because a gate failure must stay inside header-authorization
derivation and inside every gate. `class` is `observation`, so the
all-or-nothing rule of a `gate` entry does not apply and the acknowledged
`hook-projection-asymmetric` discloses the asymmetry instead.

Resolving the blocker is the user's write, not Bridge's: add the byte-exact
line

```text
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->
```

to `.claude/rules/hooks.md` and re-plan. That is why the Claude row uses action
`resolve-blocker` with direction `user-decision` rather than a mutating action
Bridge is not authorized to run.

`.codex/hooks.json` already carries one hand-written `SessionStart` group whose
matcher is `startup`. No valid entry declares that `(event, matcher)` pair and
no handler in it is marked `[bridge:<id>]`, so it is reported once as
`undeclared-hooks-key` and Bridge never touches it. The planned Codex write
appends the owned `PostToolUse` group at the closing bracket of the `hooks`
object and reorders nothing.

Bridge provides no cross-carrier atomicity. If the Codex closure is confirmed
and applied while the acknowledgement is still missing, the Codex hook is
active for every clone while the Claude carrier holds no handler at all.

Hook bytes are verified only as repository carriers. Codex activation is
subject to project trust and per-hook trust, and neither is observable from
repository bytes.
