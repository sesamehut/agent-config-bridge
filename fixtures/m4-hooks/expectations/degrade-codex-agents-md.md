# Bridge Sync Plan

- project: degrade-codex-agents-md
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
| hooks/notify-reminder/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | event-unverified |
| hooks/notify-reminder/codex | closure/agents-md | selected | - | no-baseline | create | source-to-projection | confirmed | applied | semantic | behavior-degraded; event-unverified; live-activation-unknown; restart-may-be-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/agents-md | hooks/notify-reminder/codex | - | selected | confirmed | applied |
| closure/hooks/claude | hooks/notify-reminder/claude | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |
| capability/2 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/agents-md | AGENTS.md | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/2 | unavailable | - |

## Warnings

- claude-hooks-shared-execution: .claude/settings.json
- guarded-patch-non-cas: .claude/settings.json
- guarded-patch-non-cas: AGENTS.md
- hook-output-not-delivered: .claude/rules/hooks.md (entry notify-reminder)
- manual-zone-guarded: AGENTS.md
- strict-compensation-unavailable: .claude/settings.json
- strict-compensation-unavailable: AGENTS.md

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/notify-reminder/claude | reminder | settings-json | native | claude-only-event |
| hooks/notify-reminder/codex | reminder | agents-md | semantic | degraded-standing-instruction |

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

Entry `notify-reminder` declares `event: Notification`, which is outside the 12
names of `shared-events/2026-09-07`. It is therefore proven non-native on Codex
and unknown to the registry, so both host rows carry `event-unverified`:
Bridge cannot prove either host fires it, and the Claude row carries the
annotation as well even though its `## Hook tiers` reason is
`claude-only-event`. The entry is `class: reminder` on an event outside the
shared stdout-delivering set `{SessionStart, UserPromptSubmit}`, so the
informational `hook-output-not-delivered` records that Claude runs the handler
without delivering its stdout to the model.

Degradation is admissible because `class` is `reminder` and the event is proven
non-native on Codex. The Codex counterpart is one managed root `AGENTS.md`
block rendered by the `hd1` template with block id `hooks/notify-reminder` and
source `.claude/rules/hooks.md`. It interpolates all five prose bullets, so the
Trigger, Purpose, Command, Environment and Failure policy lines of the entry
are part of the compared value. The rendered block occupies lines 49 to 63 of
the post-state `AGENTS.md`; the covenant block on lines 1 to 47 and the manual
zone on lines 64 to 68, whose `## Project notes` heading is line 65, are
byte-identical to the input.

The degraded row is an ordinary member of the existing `closure/agents-md`;
hooks introduce no separate prose-carrier closure id. The two closures do not
depend on each other, because deferring a prose block must never make an
executable carrier unexecutable. Step order alone places the explanation before
the executable hook: `AGENTS.md` is step 1 and `.claude/settings.json` is
step 2.

`guarded-patch/v1` on `AGENTS.md` includes every non-selected span in the
complete pre and post images but cannot prove the absence of a lost concurrent
edit, which is what `manual-zone-guarded` records. Neither forward operation
has an attested strict inverse, so no automatic compensation would have been
attempted.

The Codex row carries `behavior-degraded` because a prose surface cannot
execute the command: nothing runs automatically on Codex for this entry. It
also carries `live-activation-unknown` and `restart-may-be-required` because
its root `AGENTS.md` carrier was written. Start a new Codex run/session before
testing the updated project instructions or skill.

Hook bytes are verified only as repository carriers. Whether the Claude handler
runs depends on `disableAllHooks` after settings precedence, on managed policy
settings, and on per-run flags, none of which are observable from repository
bytes.
