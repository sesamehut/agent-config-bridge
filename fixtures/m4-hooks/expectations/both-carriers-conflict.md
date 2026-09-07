# Bridge Sync Plan

- project: both-carriers-conflict
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
| hooks/fmt-on-save/claude | closure/decision/hooks/fmt-on-save | selected | 0000000000000000000000000000000000000000 | both-changed | conflict | user-decision | required | deferred | native | decision-required |
| hooks/fmt-on-save/codex | closure/decision/hooks/fmt-on-save | selected | 0000000000000000000000000000000000000000 | both-changed | conflict | user-decision | required | deferred | native | decision-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/fmt-on-save | hooks/fmt-on-save/claude; hooks/fmt-on-save/codex | - | selected | required | deferred |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

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

Both owned `PostToolUse` handlers were hand-edited after the proven managed
baseline, and they were edited to different values. `.claude/settings.json`
now runs `bridge-fixture-noop fmt-on-save-hand` and `.codex/hooks.json` now
runs `bridge-fixture-noop fmt-on-save-codex-hand`, while
`.claude/rules/hooks.md` still declares the shared scalar
`bridge-fixture-noop fmt-on-save`. Two hosts carry two different new intents
for one entry, so neither carrier is the projection of the other and no
reverse adoption is derivable: mapping either value into the shared scalar
would silently discard the other host's edit, and Bridge never picks a host.

Both host rows share one `closure/decision/hooks/fmt-on-save` so a two-host
decision is never split across two closures. The closure is selected,
`required` and `deferred` with zero writes, so both capability sections are
`- (none)`, the header stays `- authorization: not-applicable`, and no
`authorization-incomplete` line is emitted: header authorization derives from
selected mutating closures only and a zero-write decision closure cannot
mutate.

Resolving this needs an explicit user choice per host: adopt one value into
the shared `command`, record each value as a `targets.<host>.command` override
with its own `override-reason`, or reproject the declared source over both
carriers. Every one of those is a separate confirmed plan; nothing here
authorizes a write.

No byte of either carrier changes in this plan. The unowned `SessionStart`
group whose matcher is `startup` and the Codex top-level `description` member
stay exactly as the team wrote them.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.
