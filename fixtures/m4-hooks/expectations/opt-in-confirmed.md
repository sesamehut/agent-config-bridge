# Bridge Sync Plan

- project: opt-in-confirmed
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
| hooks/journal-writer/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | - |
| hooks/journal-writer/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | awaiting-host-trust |
| hooks/journal-writer/source | closure/hooks/source | selected | - | no-baseline | update | user-decision | confirmed | applied | - | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/journal-writer/claude | closure/hooks/source | selected | confirmed | applied |
| closure/hooks/codex | hooks/journal-writer/codex | closure/hooks/source | selected | confirmed | applied |
| closure/hooks/source | hooks/journal-writer/source | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |
| capability/2 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |
| capability/3 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/source | .claude/rules/hooks.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/2 | unavailable | - |
| 3 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/3 | unavailable | - |

## Warnings

- claude-hooks-shared-execution: .claude/settings.json
- guarded-patch-non-cas: .claude/rules/hooks.md
- guarded-patch-non-cas: .claude/settings.json
- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .claude/rules/hooks.md
- strict-compensation-unavailable: .claude/settings.json
- strict-compensation-unavailable: .codex/hooks.json
- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/journal-writer/claude | side-effect | settings-json | native | shared-event-command |
| hooks/journal-writer/codex | side-effect | codex-hooks-json | native | shared-event-command |
| hooks/journal-writer/source | side-effect | - | - | - |

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

The exact command line enabled by this operation is
`bridge-fixture-noop journal-writer`, declared by entry `journal-writer` on
`SessionEnd` with no matcher and `timeout: 3`. `class` is `side-effect` and
`enabled` is `true`, so the input document's missing `enabled-by` record made
the entry a selected zero-write decision closure with action `opt-in-or-skip`
and the blocker warning `hook-opt-in-required`. The user confirmed the opt-in
against those exact bytes, so this operation first appends

```text
enabled-by:
  - date: 2026-09-07
    note: reviewed the exact command line and accepted repository-wide execution
```

to `.claude/rules/hooks.md`, together with the second dated `intent` record
that states the same fact. An opt-in is resolved by writing, not by discussion,
so `opt-in-required` disappears only because those bytes now exist.

Step order is source first and carriers last: `.claude/rules/hooks.md`, then
`.claude/settings.json`, then `.codex/hooks.json`. Both carrier closures depend
on `closure/hooks/source`, which is selected and confirmed, so no
`closure-dependency-unsatisfied` line is emitted. The two carrier closures do
not depend on each other, because deferring one executable carrier must never
make the other unexecutable.

Both carrier writes are `json-owned-span/v1` compositions of their exact
preimages. `.claude/settings.json` gains a new top-level `hooks` member after
the hand-formatted `permissions`, `env` and 33-entry `skillOverrides` map, and
every unowned byte, key order and indentation of that file is unchanged.
`.codex/hooks.json` keeps the user `description` and the hand-written
`SessionStart` group byte-identical; the new `SessionEnd` member is inserted
ahead of `SessionStart` in ascending member order and no existing element is
reordered or moved. That `SessionStart` group is neither owned by a valid entry
nor marked with a Bridge id, so it is reported once as `undeclared-hooks-key`
and left untouched.

Codex binds per-hook trust to a normalized handler identity, so the created
`SessionEnd` handler is listed as new and is silently skipped at dispatch until
the user reviews it. `awaiting-host-trust` on the Codex row records that fact;
it is not a trust state and never selects a plan state.

Neither guarded replacement has an attested strict inverse, so no automatic
compensation would have been attempted and each of the three forward
operations carries `strict-compensation-unavailable`. `guarded-patch/v1`
preflight and postverification filter and detect races; they do not close the
race inside the host call.

Hook bytes are verified only as repository carriers. Whether the Claude handler
runs depends on `disableAllHooks` after settings precedence, on managed policy
settings, and on per-run flags, none of which are observable from repository
bytes.
