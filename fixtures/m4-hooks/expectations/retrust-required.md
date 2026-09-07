# Bridge Sync Plan

- project: retrust-required
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
| hooks/wrap-up-note/claude | closure/decision/hooks/wrap-up-note | selected | 0000000000000000000000000000000000000000 | unchanged | unchanged | - | not-applicable | unchanged | native | - |
| hooks/wrap-up-note/codex | closure/hooks/codex | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | applied | native | awaiting-host-trust |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/wrap-up-note | hooks/wrap-up-note/claude | - | selected | not-applicable | unchanged |
| closure/hooks/codex | hooks/wrap-up-note/codex | - | selected | confirmed | applied |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/codex | .codex/hooks.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |

## Warnings

- codex-hook-retrust-required: .codex/hooks.json (SessionEnd group=0 handler=0)
- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .codex/hooks.json

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/wrap-up-note/claude | observation | settings-json | native | shared-event-command |
| hooks/wrap-up-note/codex | observation | codex-hooks-json | native | timeout-cap-differs |

## Migration decisions

- (none)

## Migration candidates

- (none)

## Adoption decisions

- (none)

## Hook adoption decisions

- (none)

## Evidence and notes

The entry keeps the shared `timeout: 30` and raises only
`targets.codex.timeout` from `2` to `3`, under the unchanged
`override-reason: timeout-cap`, because Codex clamps `SessionEnd` handlers to
one through three seconds while Claude does not. The Claude projection is
therefore identical to its carrier bytes and its row is `unchanged` with no
write, no Write capabilities row and no `hook-format-preserved` line: the
bytes are equal, not merely semantically equal.

Only `.codex/hooks.json` changes. Inside the owned `SessionEnd` group the
single edited scalar is `timeout`. The handler keeps `type`, `command`
`bridge-fixture-noop wrap-up-note` and `statusMessage`
`[bridge:wrap-up-note]` byte-for-byte. `statusMessage` is outside the edited
field set on an existing Codex handler because it is inside the Codex trust
identity, and Bridge writes the `[bridge:<id>]` marker on Codex only at
creation. The top-level `description` member is untouched.

`timeout` is a normalized field of the Codex trust identity, so the handler's
identity changes and the acknowledged `codex-hook-retrust-required` names its
exact position, `(SessionEnd group=0 handler=0)`. Codex lists a new or
modified hook as requiring review and silently skips it at dispatch until the
user re-trusts it, with no prompt, so this handler goes dark until the user
reviews it in `/hooks`. That is what `awaiting-host-trust` records; it is
neutral and is not a trust state. This is an identity change, not a
`commandWindows`-only replacement, so `codex-trust-blind-change` does not
apply and the two are mutually exclusive for one handler.

The pinned `activation-fixture/v2` profile resolves Codex project trust as
`trusted` and the Codex hooks feature as `enabled`, so neither
`codex-project-untrusted` nor `codex-hooks-feature-disabled` is emitted. That
is a pinned fixture input, never an observation from repository bytes.

The forward replacement uses `guarded-patch/v1` and has no attested strict
inverse, so no automatic compensation would be attempted.

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine.
