# Bridge Sync Plan

- project: inline-hooks-conflict-blocked
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
- codex-inline-hooks-conflict: .codex/config.toml (SessionStart)
- guarded-patch-non-cas: .claude/settings.json
- hook-projection-asymmetric: .codex/hooks.json (hooks/fmt-on-save/codex)
- strict-compensation-unavailable: .claude/settings.json
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

The shallow byte scan of `.codex/config.toml` finds the table header
`[hooks.SessionStart]` at line 4 and no top-level `hooks =` pointer key, so the
same Codex layer declares hooks both inline and in `.codex/hooks.json`. Codex
merges the two forms within one layer, and the persisted trust key embeds the
source path together with `{event}:{group_index}:{handler_index}`, so the two
forms register as two distinct keys while sharing one normalized hash. The
double-execution hazard is concrete: a hook Bridge writes into
`.codex/hooks.json` would run once for the file and once for the inline table,
and silently doubling a teammate's hook execution is exactly the harm the
non-overwrite discipline exists to prevent. The scan is a byte scan and not a
TOML parse, and it fails closed when it cannot prove the absence of a hooks
section.

`codex-inline-hooks-conflict` is therefore a closure-scoped blocker.
`closure/hooks/codex` keeps `selected` with authorization `not-applicable` and
outcome `blocked` and is never relabelled `not-selected`; Bridge writes no
TOML and removes nothing the user declared. Entry `fmt-on-save` is
`class: observation`, so the sibling Claude carrier may still apply under the
acknowledged `hook-projection-asymmetric`, and Bridge provides no
cross-carrier atomicity. `.claude/settings.json` carries no `hooks` key, so the
Claude row is H-MISSING with action `create` while the operation on the
existing file is `replace`. The unowned `SessionStart` group with matcher
`startup` in `.codex/hooks.json` is disclosed once and never rewritten.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.
