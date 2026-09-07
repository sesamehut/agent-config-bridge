# Bridge Sync Plan

- project: gate-all-or-nothing
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
| hooks/repo-guard/claude | closure/hooks/claude | not-selected | - | no-baseline | create | source-to-projection | not-applicable | not-selected | native | - |
| hooks/repo-guard/codex | closure/hooks/codex | not-selected | - | no-baseline | create | source-to-projection | not-applicable | not-selected | native | - |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/repo-guard/claude | - | not-selected | not-applicable | not-selected |
| closure/hooks/codex | hooks/repo-guard/codex | - | not-selected | not-applicable | not-selected |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- hook-carrier-absent: .codex/hooks.json

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/repo-guard/claude | gate | settings-json | native | shared-event-command |
| hooks/repo-guard/codex | gate | codex-hooks-json | native | shared-event-command |

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

`.claude/rules/hooks.md` declares one entry, `repo-guard`, on `PreToolUse` with
matcher `^(Bash)$`, `class: gate`, `enabled: true`, shared command
`bridge-fixture-noop repo-guard`, `timeout: 30`, and a dated `enabled-by`
record from 2026-09-07 that states the reviewer accepted repository-wide
execution. The opt-in gate is therefore satisfied and no
`hook-opt-in-required` line applies; the class gate rule is the only thing that
stops this plan.

Both targets declare a native JSON carrier, but `.codex/hooks.json` does not
exist. An absent hooks carrier is a `create`, and `create` accepts only
`strict-create/v1`, which no attested live adapter supplies, so the Codex
carrier of this entry is unavailable. The missing file is reported once as the
informational `hook-carrier-absent: .codex/hooks.json`.

For an entry whose `class` is `reminder`, `observation`, or `side-effect`, one
carrier may apply while the sibling is blocked or unavailable, under the
acknowledged `hook-projection-asymmetric`. For `class: gate` the entry is
all-or-nothing, because a rule that vetoes a shell call on one host and
silently permits it on the other is worse than no enforcement at all.
Asymmetric enforcement is never shipped. The class gate rule is decided before
selection, so the unavailable Codex carrier takes the whole entry out of this
plan: `closure/hooks/claude` and `closure/hooks/codex` are both `not-selected`
/ `not-applicable` / `not-selected`, and each unit row repeats its closure's
shape. No carrier proceeds, so this plan emits no `hook-projection-asymmetric`
line and neither host is projected.

Because neither carrier closure is selected, no operation reaches the `write
capability` gate: the unavailable `strict-create/v1` create is never planned,
no `conditional-write-unavailable` line is emitted, and `Write capabilities`
is `- (none)`. That is what separates this plan from `codex-create-blocked`,
where the same absent carrier belongs to a `class: observation` entry, the
Codex closure stays `selected` / `not-applicable` / `blocked` under the
closure-scoped gate with the matching `unavailable` capability row, and the
Claude closure still applies.

No closure is selected, so no selected closure can mutate. Both `Capability
profiles` and `Write capabilities` are `- (none)`, the header authorization
derives to `not-applicable`, and no `authorization-incomplete` line is
emitted. `.claude/settings.json` is not written, so no
`claude-hooks-shared-execution` acknowledgement is required either; it carries
no `hooks` key and no unowned group, so no `undeclared-hooks-key` line
applies.

To create the missing carrier, paste exactly these bytes into
`.codex/hooks.json`, as UTF-8 without a BOM, with LF line endings and one final
newline:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Bash)$",
        "hooks": [
          {
            "type": "command",
            "command": "bridge-fixture-noop repo-guard",
            "timeout": 30,
            "statusMessage": "[bridge:repo-guard]"
          }
        ]
      }
    ]
  }
}
```

Those bytes are `render-hook-group` for host `codex` under the default
two-space style with `--creating`, wrapped in the minimal `hooks.PreToolUse`
carrier shape. Pasting them does not enable the guard on its own: a `gate`
entry reaches both hosts or neither, so the file has to exist before a plan
may select the Claude carrier at all.

The rows stay in the two carrier closures rather than in a hook decision
closure: nothing about this entry's ownership is undecided, and there is no
`decision-required` annotation to record. Creating `.codex/hooks.json` is the
one resolution, after which a fresh plan may select both carriers together.

Formal validation record: contract `sync-plan-validator/v1`. The plan
SHA-256, the validation-context SHA-256 and the PASS result are recorded by
the live operation that serializes this document, not by this expectation.
