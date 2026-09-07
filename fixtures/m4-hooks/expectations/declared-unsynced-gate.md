# Bridge Sync Plan

- project: declared-unsynced-gate
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
| hooks/permission-gate/claude | closure/decision/hooks/permission-gate | selected | 0000000000000000000000000000000000000000 | unchanged | unchanged | - | not-applicable | unchanged | native | - |
| hooks/permission-gate/codex | closure/decision/hooks/permission-gate | selected | - | declared-unsynced | unchanged | - | not-applicable | unchanged | declared-unsynced | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/permission-gate | hooks/permission-gate/claude; hooks/permission-gate/codex | - | selected | not-applicable | unchanged |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- (none)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/permission-gate/claude | gate | settings-json | native | shared-event-command |
| hooks/permission-gate/codex | gate | none | declared-unsynced | decision-not-portable |

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

Entry `permission-gate` declares `class: gate` on `PermissionRequest` with a
dated `enabled-by` record from 2026-09-07, so the opt-in gate is satisfied and
no `hook-opt-in-required` line is emitted. The Claude carrier
`.claude/settings.json` already carries the owned `PermissionRequest` group
whose single command handler is handler-equal to the entry, so the Claude row
is H-OK and `unchanged`.

`targets.codex.surface` is `none` with tier `declared-unsynced`, so Codex has
no counterpart to converge. No handler in any Codex carrier is marked
`[bridge:permission-gate]` and the project ships no `.codex/hooks.json`, so
H-T4-PRESENT does not fire and the Codex row stays H-T4. The two hosts decide a
permission request through different decision shapes, which is why the
`## Hook tiers` reason is `decision-not-portable` rather than a portability
obstacle Bridge could remove.

Both rows share one `closure/decision/hooks/permission-gate` so the entry's
two-host decision is never split. The closure is zero-write, so header
authorization stays `not-applicable`, both capability sections are `- (none)`,
and no `authorization-incomplete` line is emitted.

Hook bytes are verified only as repository carriers. Whether the Claude handler
runs depends on `disableAllHooks` after settings precedence, on managed policy
settings, and on per-run flags, none of which are observable from repository
bytes.
