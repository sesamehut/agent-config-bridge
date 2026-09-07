# Bridge Sync Plan

- project: opt-in-pending
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
| hooks/journal-writer/claude | closure/decision/hooks/journal-writer | selected | - | no-baseline | opt-in-or-skip | user-decision | required | deferred | native | decision-required; opt-in-required |
| hooks/journal-writer/codex | closure/decision/hooks/journal-writer | selected | - | no-baseline | opt-in-or-skip | user-decision | required | deferred | native | decision-required; opt-in-required |

## Closures

| closure | members | depends on | selection | authorization | outcome |
|---|---|---|---|---|---|
| closure/decision/hooks/journal-writer | hooks/journal-writer/claude; hooks/journal-writer/codex | - | selected | required | deferred |

## Capability profiles

- (none)

## Write capabilities

- (none)

## Warnings

- hook-opt-in-required: .claude/rules/hooks.md (entry journal-writer)
- undeclared-hooks-key: .codex/hooks.json (SessionStart matcher=startup)

## Hook tiers

| unit | class | surface | tier | reason |
|---|---|---|---|---|
| hooks/journal-writer/claude | side-effect | settings-json | native | opt-in-pending |
| hooks/journal-writer/codex | side-effect | codex-hooks-json | native | opt-in-pending |

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

`.claude/rules/hooks.md` declares one entry, `journal-writer`, on `SessionEnd`
with no matcher, `class: side-effect`, `enabled: true`, `timeout: 3`, and both
targets on a native JSON carrier. It carries no `enabled-by` list at all.

The exact command line being enabled is:

```text
bridge-fixture-noop journal-writer
```

The author declares that a real command in this position would write one file
into the project journal and read no environment variable. That declaration is
review metadata, not a sandbox: nothing in Bridge constrains what the command
actually does once it is projected into a committed carrier.

A `gate` or `side-effect` entry with `enabled: true` and no covering
`enabled-by` record is `opt-in-or-skip`. Both host rows of the entry share one
`closure/decision/hooks/journal-writer` so the two-host decision is never split
across two closures, and the closure is the closed opt-in-pending decision
shape: `selected` / `required` / `deferred` with `decision-required;
opt-in-required` on every row. The blocker is reported once per entry as
`hook-opt-in-required: .claude/rules/hooks.md (entry journal-writer)` and is
scoped to that decision closure and the two carrier closures it stands in for.

A hook decision closure is zero-write, so the header authorization stays
derived from selected mutating closures only. It is `not-applicable`, there is
no `authorization-incomplete` line, and both `Capability profiles` and
`Write capabilities` are `- (none)`. Nothing is written on either host.

`## Hook tiers` records the reason `opt-in-pending` on both host rows: the
entry is `side-effect` with `enabled: true` and no covering record, so its
declared native tier is not yet realized anywhere.

An opt-in decision is resolved by writing, not by discussion. Confirming it
produces a `hooks/journal-writer/source` row in `closure/hooks/source` that
appends the dated `enabled-by` record to `.claude/rules/hooks.md` with action
`update`, direction `user-decision` and tier `-`, plus the two carrier rows
that depend on that closure. Until those bytes exist, `opt-in-required` stays
attached to every hook row of the entry; the annotation is never removed
because the user discussed the choice. Skipping instead leaves the entry
declared and unprojected.

`.codex/hooks.json` carries one unowned `SessionStart` group whose matcher is
`startup`. It is neither owned by a valid entry nor marked with a Bridge id, so
it is reported once as the informational `undeclared-hooks-key:
.codex/hooks.json (SessionStart matcher=startup)` and is never touched.

Formal validation record: contract `sync-plan-validator/v1`. The plan
SHA-256, the validation-context SHA-256 and the PASS result are recorded by
the live operation that serializes this document, not by this expectation.
