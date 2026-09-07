# Bridge Sync Plan

- project: delete-event-emptied
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
| hooks/stale-check/claude | closure/hooks/claude | selected | 0000000000000000000000000000000000000000 | source-only | delete | source-to-projection | confirmed | applied | native | - |
| hooks/stale-check/codex | closure/hooks/codex | selected | 0000000000000000000000000000000000000000 | source-only | delete | source-to-projection | confirmed | applied | native | awaiting-host-trust |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/stale-check/claude | - | selected | confirmed | applied |
| closure/hooks/codex | hooks/stale-check/codex | - | selected | confirmed | applied |

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

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/stale-check/claude | observation | settings-json | native | shared-event-command |
| hooks/stale-check/codex | observation | codex-hooks-json | native | shared-event-command |

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)

## Evidence and notes

The `stale-check` entry was removed from `.claude/rules/hooks.md` while both
owned groups were still converged with the deleted declaration, so the
deletion has a unique proven managed baseline on both hosts and is a
`source-only` `delete` in the source-to-projection direction. The declaration
that states each host's tier survives only at the baseline commit, which is
where it is read. The destructive choice is separately confirmed; a delete is
never derived from a missing entry alone.

Each carrier held exactly one `PostToolUse` group and it was the owned one.
Removing it empties the event on both hosts, so the whole
`"PostToolUse": [...]` member is removed rather than left as an empty array,
and the now empty `hooks` object is left as `"hooks": {}` in
`.claude/settings.json` and in `.codex/hooks.json` alike. The key itself is
never removed, because an absent `hooks` object is what H-NOFILE means and
deleting the key would change the meaning of the carrier. On Codex the whole
member is what goes, rather than an empty array, because the persisted trust
keys are per event. The unrelated `permissions` member and the top-level
`description` member are byte-identical.

No element survives in either emptied event, so nothing re-indexes and no
`codex-trust-reindex` line applies. No unowned group is present in either
carrier, so no `undeclared-hooks-key` line applies either.

Both replacements use `guarded-patch/v1`, whose complete-file preflight and
postverification filter and detect races but do not close the race inside the
host call, and neither has an attested strict inverse, so no automatic
compensation would be attempted. `awaiting-host-trust` records only that the
Codex carrier was written; it is not a trust state.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.
