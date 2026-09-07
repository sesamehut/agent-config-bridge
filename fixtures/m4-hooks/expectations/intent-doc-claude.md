# Bridge Sync Plan

- project: intent-doc-claude
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
| hooks/interrupt-note/claude | closure/decision/hooks/interrupt-note | selected | - | unchanged | unchanged | - | not-applicable | unchanged | semantic | behavior-degraded |
| hooks/interrupt-note/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | awaiting-host-trust |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/interrupt-note | hooks/interrupt-note/claude | - | selected | not-applicable | unchanged |
| closure/hooks/codex | hooks/interrupt-note/codex | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .codex/hooks.json
- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/interrupt-note/claude | observation | intent-doc | semantic | intent-doc-standing-instruction |
| hooks/interrupt-note/codex | observation | codex-hooks-json | native | codex-only-event |

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

Entry `interrupt-note` declares `event: Interrupt`, the single Codex-only name
of `shared-events/2026-09-07`. `Interrupt` is inside that dated registry, so no
row carries `event-unverified`; it is proven non-native on Claude, so a
`native` Claude tier would be the `tier-unsupported-event` schema violation and
the degradation to a prose surface is admissible for this `class: observation`
entry.

The Claude surface is `intent-doc`, which means `.claude/rules/hooks.md` is
itself the carrier. There is no second Claude artifact to compare, so the row
is H-DOC, vacuously `in-sync`, and Bridge writes nothing at all on the Claude
side. That is why `.claude/settings.json` appears in no Write capabilities row,
why no `claude-hooks-shared-execution` line is emitted, and why the row sits in
the entry's zero-write `closure/decision/hooks/interrupt-note`. The row keeps
`behavior-degraded`, because a prose surface cannot execute the command: on
Claude the intent is a standing instruction the model reads, not a handler the
host runs.

The document carries no file-level `bridge:hooks-shared-execution` comment and
needs none, because no target declares the Claude `settings-json` surface. Its
entry heading is therefore on line 5 and its fenced `yaml` block opens on line
13.

The Codex projection is native. `timeout: 2` is inside the 1 to 3 range Codex
clamps `Interrupt` into, so Bridge declares a value the host will not rewrite.
The write is a `json-owned-span/v1` composition of the exact preimage: the user
`description` and the hand-written `SessionStart` group with matcher `startup`
keep every byte, and the new `Interrupt` member is inserted ahead of
`SessionStart` in ascending member order. That `SessionStart` group is neither
owned by a valid entry nor marked with a Bridge id, so it is reported once as
`undeclared-hooks-key` and left untouched.

Codex binds per-hook trust to a normalized handler identity, so the created
`Interrupt` handler is listed as new and is silently skipped at dispatch until
the user reviews it. `awaiting-host-trust` records that fact; it is not a trust
state and never selects a plan state. The forward guarded replacement has no
attested strict inverse, so no automatic compensation would have been
attempted.

Hook bytes are verified only as repository carriers. Codex activation is
subject to project trust and per-hook trust, and neither is observable from
repository bytes.
