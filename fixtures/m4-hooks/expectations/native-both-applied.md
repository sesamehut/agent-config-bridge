# Bridge Sync Plan

- project: native-both-applied
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
| hooks/fmt-on-save/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | - |
| hooks/fmt-on-save/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | confirmed | applied | native | awaiting-host-trust |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/fmt-on-save/claude | - | selected | confirmed | applied |
| closure/hooks/codex | hooks/fmt-on-save/codex | - | selected | confirmed | applied |

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

The opt-in record is a review checkpoint in Git, not an enforcement boundary.
Bridge classification is author-declared metadata, not a sandbox. Claude Code
runs hooks from committed settings without a trust prompt in `-p` and SDK
sessions, so anyone who can commit to this repository can run commands on a
teammate's machine. Hook execution is also observed-but-not-guaranteed on both
hosts, so no Bridge state may be read as a runtime guarantee.

Source: `.claude/rules/hooks.md` declares one entry, `fmt-on-save`, on
`PostToolUse` with no matcher, `class: observation`, `enabled: true`, shared
command `bridge-fixture-noop fmt-on-save`, and `timeout: 10`. Both targets
declare a native JSON carrier, so both host rows use tier `native` and the
`## Hook tiers` reason `shared-event-command`: `PostToolUse` is in
`shared-events/2026-09-07` and one command handler serves both hosts.

Read side: `.claude/settings.json` carries `permissions`, `env`, and a
33-entry `skillOverrides` map and no `hooks` key at all, so the owned
`(PostToolUse, no matcher)` group is absent and the Claude row is H-MISSING.
`.codex/hooks.json` carries a user `description` and one unowned
`SessionStart` group whose matcher is `startup`, so the Codex row is also
H-MISSING. The project is onboarded, so both rows are `drift`/`reconcile` on
the read side and `no-baseline`/`create` here: the projection member is
missing while both carrier files already exist, which is why the Write
capabilities operation is `replace` and the Units action is `create`.

Both postimages are produced by `json-owned-span/v1` composition, never by
reserializing the parsed carrier. On `.claude/settings.json` the composition
appends one new top-level `hooks` member after `skillOverrides`; every
`permissions`, `env`, and `skillOverrides` byte, key order and indentation is
unchanged. On `.codex/hooks.json` the composition inserts the `PostToolUse`
event member ahead of the existing `SessionStart` member in ascending member
order; the user `description` string and the complete unowned `SessionStart`
group survive byte for byte. `statusMessage` is written on both carriers
because both handlers are created here; Bridge never adds, changes, or removes
a Codex `statusMessage` on an already converged handler.

The unowned `SessionStart` group in `.codex/hooks.json` is neither owned by a
valid entry nor marked with a Bridge id, so it is reported once as the
informational `undeclared-hooks-key: .codex/hooks.json (SessionStart
matcher=startup)` and is never touched.

Both replacements use `guarded-patch/v1`, whose preflight and postverification
leave a residual race, and neither has an attested strict inverse, so
`guarded-patch-non-cas` and `strict-compensation-unavailable` are acknowledged
once per exact path. Automatic compensation is therefore not attempted; a
later reverse operation needs a new confirmed plan reconstructed from current
bytes and reachable Git.

`awaiting-host-trust` is attached only to the Codex row and only in this
post-write result. Codex binds per-hook trust to a normalized handler identity,
so the newly created handler is listed as new and is skipped at dispatch until
the user reviews it in `/hooks`. The annotation is neutral and is not a trust
state. The Claude carrier needs no such review, which is exactly why
`claude-hooks-shared-execution` is acknowledged for `.claude/settings.json`.

Formal validation record: contract `sync-plan-validator/v1`. The plan
SHA-256, the validation-context SHA-256 and the PASS result are recorded by
the live operation that serializes this document, not by this expectation.
