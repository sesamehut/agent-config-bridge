# Bridge Sync Plan

- project: delete-group-reindex
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
- codex-trust-reindex: .codex/hooks.json (PostToolUse from=0)
- guarded-patch-non-cas: .claude/settings.json
- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .claude/settings.json
- strict-compensation-unavailable: .codex/hooks.json
- undeclared-hooks-key: .codex/hooks.json (PostToolUse matcher=^(Bash)$)
- undeclared-hooks-key: .codex/hooks.json (PostToolUse matcher=^(Read)$)

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
`source-only` `delete` in the source-to-projection direction. The destructive
choice is separately confirmed; a delete is never derived from a missing
entry alone.

`.claude/settings.json` held exactly one `PostToolUse` group and it was the
owned one. Removing it empties the event, so the whole `"PostToolUse": [...]`
member is removed rather than left as an empty array, and the now empty
`hooks` object is left as `"hooks": {}`. The key itself is never removed,
because an absent `hooks` object is what H-NOFILE means and deleting the key
would change the meaning of the carrier. The unrelated `permissions` member
is byte-identical.

`.codex/hooks.json` held three `PostToolUse` groups: the owned group at index
0 and two unowned groups whose matchers are `^(Read)$` and `^(Bash)$`. Only
the owned element span plus exactly one adjacent separator is removed, and
because the removed element is first the following separator is the one
taken. The two unowned groups survive byte-for-byte, keep their original
relative order, and shift to indices 0 and 1. The top-level `description`
member is untouched.

That shift is disclosed as the acknowledged `codex-trust-reindex` with detail
`(PostToolUse from=0)`. Codex persists per-hook trust and the user's own
`/hooks` disable choice under keys that embed the event, group index and
handler index, so the two surviving groups now answer to the keys the removed
group used to hold. Review the Codex `/hooks` list after this write. Bridge
never reorders, sorts, or moves an existing element to avoid that shift,
because reordering would re-point unrelated hooks' trust and could silently
re-enable a hook the user deliberately disabled.

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
