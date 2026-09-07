# Bridge Sync Plan

- project: codex-create-blocked
- scan root: .
- date: 2026-09-07
- expectation: sync-plan/v3
- contracts: covenant/v3, source-tree/v5, report/v5, reconciliation/v3
- phase: pre-write
- onboarding: onboarded
- authorization: required

## Units

| unit | closure | selection | baseline | state | action | direction | authorization | outcome | tier | annotations |
|---|---|---|---|---|---|---|---|---|---|---|
| hooks/fmt-on-save/claude | closure/hooks/claude | selected | - | no-baseline | create | source-to-projection | required | planned | native | - |
| hooks/fmt-on-save/codex | closure/hooks/codex | selected | - | no-baseline | create | source-to-projection | not-applicable | blocked | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/fmt-on-save/claude | - | selected | required | planned |
| closure/hooks/codex | hooks/fmt-on-save/codex | - | selected | not-applicable | blocked |

## Capability profiles

| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
| capability/1 | capability-profile/v1 | other | fixture-guarded-v1 | exact-literal-edit/v1 | other | existing-regular-utf8/v1; unique-exact-region/v1 |

## Write capabilities

| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
| 1 | closure/hooks/claude | .claude/settings.json | replace | guarded-patch/v1 | capability/1 | unavailable | - |
| 2 | closure/hooks/codex | .codex/hooks.json | create | unavailable | - | unavailable | - |

## Warnings

- authorization-incomplete: .
- claude-hooks-shared-execution: .claude/settings.json
- conditional-write-unavailable: .codex/hooks.json
- guarded-patch-non-cas: .claude/settings.json
- hook-carrier-absent: .codex/hooks.json
- hook-projection-asymmetric: .codex/hooks.json (hooks/fmt-on-save/codex)
- strict-compensation-unavailable: .claude/settings.json

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

`.codex/hooks.json` does not exist in this project. An absent hooks carrier is
a `create`, and `create` accepts only `strict-create/v1`, which no attested
live adapter supplies today. The row therefore keeps action `create` with
`unavailable` forward and inverse protocols and outcome `blocked`. Bridge does
not create the carrier with an unconditional write and does not invent a
create-after-check.

The `write capability` gate is one of the three closed exceptions to the
project-wide apply prohibition, so it is scoped to `closure/hooks/codex` and
to every closure that depends on it. Nothing depends on it: hook carrier
closures never depend on one another. `closure/hooks/claude` therefore still
proceeds, and the blocked Codex closure keeps `selected` with authorization
`not-applicable` and outcome `blocked`. It is never relabelled `not-selected`,
because a capability failure must stay inside header-authorization derivation
and inside every gate. The entry's `class` is `observation`, so the class-gated
all-or-nothing rule does not apply and one carrier may apply while the sibling
is unavailable, under the acknowledged
`hook-projection-asymmetric: .codex/hooks.json (hooks/fmt-on-save/codex)`.

Bridge provides no cross-carrier atomicity. Once the Claude closure is
confirmed and applied, the Claude hook is active while the Codex carrier is
still absent, so the two hosts deliberately disagree until the user creates the
Codex file.

To create the missing carrier, paste exactly these bytes into
`.codex/hooks.json`, as UTF-8 without a BOM, with LF line endings and one final
newline:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bridge-fixture-noop fmt-on-save",
            "timeout": 10,
            "statusMessage": "[bridge:fmt-on-save]"
          }
        ]
      }
    ]
  }
}
```

Those bytes are `render-hook-group` for host `codex` under the default
two-space style with `--creating`, wrapped in the minimal
`hooks.PostToolUse` carrier shape. `statusMessage` appears because the handler
is created here; Bridge never adds, changes, or removes a Codex
`statusMessage` on an already converged handler. After the file exists, a fresh
plan reclassifies the Codex row as an ordinary `replace` of an existing
carrier.

`.claude/settings.json` exists and holds `permissions`, `env`, and a 33-entry
`skillOverrides` map with no `hooks` key, so its Claude row is H-MISSING and
its operation is a `guarded-patch/v1` replacement that appends one new
top-level `hooks` member. That replacement is acknowledged with
`guarded-patch-non-cas` and has no attested strict inverse, hence
`strict-compensation-unavailable`. The Claude closure is still `required`, so
the plan also carries `authorization-incomplete` and no write may run before
the exact serialized closure is confirmed.

Formal validation record: contract `sync-plan-validator/v1`. The plan
SHA-256, the validation-context SHA-256 and the PASS result are recorded by
the live operation that serializes this document, not by this expectation.
