# Bridge Sync Plan

- project: guarded-region-nonunique-blocked
- scan root: .
- date: 2026-09-07
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: pre-write
- onboarding: onboarded
- authorization: confirmed

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| hooks/fmt-on-save/claude | closure/hooks/claude | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | not-applicable | blocked | native | - |
| hooks/fmt-on-save/codex | closure/decision/hooks/fmt-on-save | selected | - | declared-unsynced | unchanged | - | not-applicable | unchanged | declared-unsynced | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/fmt-on-save | hooks/fmt-on-save/codex | - | selected | not-applicable | unchanged |
| closure/hooks/claude | hooks/fmt-on-save/claude | - | selected | not-applicable | blocked |

## Capability profiles

- (none)

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/claude | .claude/settings.json | replace | unavailable | - | unavailable | - |

## Warnings

- claude-hooks-shared-execution: .claude/settings.json
- guarded-patch-unavailable: .claude/settings.json
- undeclared-hooks-key: .claude/settings.json (PostToolUse matcher=^(Edit)$)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/fmt-on-save/claude | observation | settings-json | native | shared-event-command |
| hooks/fmt-on-save/codex | observation | none | declared-unsynced | declared-none |

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)

## Evidence and notes

Entry `fmt-on-save` declares `matcher: ^(Write)$`, so its owned Claude group is
`(PostToolUse, ^(Write)$)`, which is element 0 of
`.claude/settings.json#PostToolUse`. Element 1 declares matcher `^(Edit)$` and
is neither owned by a valid entry nor marked with a Bridge id, so it is
disclosed once as `undeclared-hooks-key` and is never rewritten.

The source updates the shared command scalar to the `-v2` fixture no-op, so
the Claude row is H-FIELD-DIFF and `source-only`/`update`. The two group
bodies are byte-identical apart from their matcher line, so the minimal old
region that covers the changed command line occurs twice in the complete
preimage. `guarded-patch/v1` requires one exact-literal, unique-match,
non-regex, non-fuzzy replacement, and the region may be extended only at code
point boundaries and only outward: context is never shortened to force a
unique match. In these bytes the region first occurs once after it is
extended upward through the distinguishing `"matcher": "^(Write)$",` line, so
the region rule alone does not block this replacement.

The block is declared by the resolved write capability, not by the region.
The capability in force attests no protocol for `replace` on
`.claude/settings.json`: the forward and the inverse protocol are both
`unavailable` and no `capability-profile/v1` binding backs them, so this
eligible existing-file replacement has neither a strict nor a guarded
protocol. `guarded-patch-unavailable` is therefore serialized with an
`unavailable` forward and inverse row. The user's confirmation of this exact
replacement is on record and cannot upgrade a protocol token, so the closure
keeps `selected` with authorization `not-applicable` and outcome `blocked`,
and is never relabelled `not-selected`, because a capability failure must
stay inside header-authorization derivation and inside every gate. No byte of
`.claude/settings.json` is written, and there is nothing to compensate. The
Codex target declares `surface: none`, so its row is the zero-write
`declared-unsynced` decision shape and the entry is not projected there at
all.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.
