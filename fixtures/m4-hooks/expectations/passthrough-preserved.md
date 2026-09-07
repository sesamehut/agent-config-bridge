# Bridge Sync Plan

- project: passthrough-preserved
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
| hooks/shell-preview/claude | closure/hooks/claude | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | applied | native | behavior-degraded |
| hooks/shell-preview/codex | closure/hooks/codex | selected | 0000000000000000000000000000000000000000 | source-only | update | source-to-projection | confirmed | applied | native | awaiting-host-trust; behavior-degraded |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/hooks/claude | hooks/shell-preview/claude | - | selected | confirmed | applied |
| closure/hooks/codex | hooks/shell-preview/codex | - | selected | confirmed | applied |

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
- codex-hook-retrust-required: .codex/hooks.json (PreToolUse group=0 handler=0)
- guarded-patch-non-cas: .claude/settings.json
- guarded-patch-non-cas: .codex/hooks.json
- strict-compensation-unavailable: .claude/settings.json
- strict-compensation-unavailable: .codex/hooks.json

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/shell-preview/claude | observation | settings-json | native | shared-event-command |
| hooks/shell-preview/codex | observation | codex-hooks-json | native | shared-event-command |

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

The baseline commit carries entry `shell-preview` with
`command: bridge-fixture-noop shell-preview` and both carriers converged on
that value. The input document changes the shared scalar to
`bridge-fixture-noop shell-preview-v2` and appends a second dated `intent`
record. Only the source differs from the unique proven baseline, so both host
rows are `source-only` / `update` / `source-to-projection`. Each carrier holds
one command handler in the owned `(PreToolUse, ^(Bash)$)` group whose `command`
now differs from the effective command, which is H-FIELD-DIFF on both hosts.

Both handlers carry a host passthrough key. The Claude handler carries `if` and
the Codex handler carries `additionalContextLimit: 4096`. Passthrough keys are
excluded from handler equality, are never written and never removed, and are
preserved byte-for-byte in place: after the write each key keeps its exact
bytes and its exact position inside its handler object, immediately after
`statusMessage`. Because a passthrough key changes host behavior Bridge cannot
model, both rows carry `behavior-degraded`. Neither key is
`codex-handler-unknown-key`: `additionalContextLimit` is a documented Codex
key in the closed passthrough set, so no unknown-key line is emitted.

`additionalContextLimit` participates in the Codex normalized trust identity,
so treating it as drift and rewriting it would force a re-trust on a deliberate
user choice. Bridge leaves it alone. The `command` replacement is itself an
identity field, so this write does change the handler's normalized identity and
emits `codex-hook-retrust-required: .codex/hooks.json (PreToolUse group=0
handler=0)`. Only one of `codex-hook-retrust-required` and
`codex-trust-blind-change` may name one handler, and an identity change selects
the first. Until the user re-trusts it, the Codex handler is listed as modified
and is silently skipped at dispatch, which is what `awaiting-host-trust`
records.

Both writes are `json-owned-span/v1` compositions of their exact preimages:
only the located owned group spans are edited, `statusMessage` keeps its
`[bridge:shell-preview]` marker, the Codex `description` member is untouched,
and neither document is reparsed and reserialized. The matcher `^(Bash)$` uses
characters outside Claude's `[A-Za-z0-9_ ,|-]` mode-switch class, so Claude
compiles it as an unanchored regular expression exactly as Codex does and no
`matcher-grammar-divergent` line is emitted.

Neither guarded replacement has an attested strict inverse, so no automatic
compensation would have been attempted and both forward operations carry
`strict-compensation-unavailable`.

Hook bytes are verified only as repository carriers. Whether the Claude handler
runs depends on `disableAllHooks` after settings precedence, on managed policy
settings, and on per-run flags, none of which are observable from repository
bytes.
