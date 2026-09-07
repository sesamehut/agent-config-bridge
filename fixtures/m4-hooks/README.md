# M4 hook projection fixtures

These declarative vectors exercise the write side of `covenant/v3`,
`source-tree/v5`, `report/v5`, `reconciliation/v3`, and `sync-plan/v3` for hook
intents on both native hook carriers, on the Claude `intent-doc` surface, and on
the Codex `agents-md` degradation surface.

`hooks_harness.py` owns no plan grammar of its own. It inserts
`fixtures/m3-rules` on `sys.path`, imports `fixture_harness` exactly as
[`../m3-rules/journal_validator.py`](../m3-rules/journal_validator.py) does, and
calls the M3 plan document parser, validator, comparison, materialization,
replay-input, replay envelope and cleanup machinery with M4 parameters. There is
one implementation of the `sync-plan/v3` document grammar and it lives in
[`../m3-rules/fixture_harness.py`](../m3-rules/fixture_harness.py). The
`bridge-live-operation-journal/v2` contract is bound by reference: its 66-case
suite belongs to M3 and is not re-run here, and `self-test` asserts the token
instead.

Five shared checks reject a hook shape M4 introduces. `hooks_harness.py` widens
exactly those five from the specs for the duration of a call and edits nothing
under `../m3-rules/`: it authenticates a hook row's tier against
`targets.<host>.tier` in the same `.claude/rules/hooks.md` entry rather than
the rule path a non-hook unit uses, admits the narrowed blocker scope
`selected` / `not-applicable` / `blocked` on a hook carrier row, follows
`live-activation-unknown` and `restart-may-be-required` to the root `AGENTS.md`
degradation carrier of a `hooks/<entry-id>/codex` row, treats
`behavior-degraded` as a neutral hook annotation in the conflict-row check, and
lets a warning detail carry the parentheses of a declared regular-expression
matcher such as `^(Edit)$`. The same neutral annotation token widens the fifth
check, the hook decision-shape gate: the `surface-none` shape `selected` /
`not-applicable` / `unchanged` requires no annotation at all, so under the
unwidened M3 set a row carrying `behavior-degraded` would resolve to no shape.
A sibling rule the shared function already carries, such as
`awaiting-host-trust` following the `.codex/hooks.json` write, is delegated
rather than restated, and every non-hook row still reaches the shared function
untouched.

A managed deletion is the one row whose declaration has left the working tree,
so its tier is read from the `.claude/rules/hooks.md` reachable at the marker's
baseline commit, through `git cat-file`. That oracle is independent of the
document under validation. Only when the baseline commit itself never declared
the entry, and the row serializes the closed `source-only` / `delete` /
`source-to-projection` shape, does the tier fall back to the plan's own
`## Hook tiers` row.

## Safe commands

Run every command from the repository root:

```text
python -B fixtures/m4-hooks/hooks_harness.py validate-matrix --trees-only
python -B fixtures/m4-hooks/hooks_harness.py validate-matrix --scenario native-both-applied
python -B fixtures/m4-hooks/hooks_harness.py validate-matrix --scenario codex-blind-change --scenario delete-event-emptied
python -B fixtures/m4-hooks/hooks_harness.py check-hook-fence
python -B fixtures/m4-hooks/hooks_harness.py self-test
python -B fixtures/m4-hooks/hooks_harness.py self-test --scenario retrust-required
```

`validate-matrix --trees-only` validates the matrix, every named tree, every
activation profile, every write-capability document, and every declared fault,
and reads no expectation, decision, or plan document. Repeating `--scenario`
restricts expectation, decision, and plan validation to those scenarios while
the trees, profiles and capabilities stay fully validated. `self-test` takes the
same repeatable `--scenario` filter and materializes only the selected
scenarios. Both flags accept any scenario id from the inventory below and reject
an unknown one. `validate-matrix` refuses `--trees-only` together with
`--scenario`: the first reads no expectation at all, so the combination would
silently mean less than it reads like.

`self-test` runs the complete accounting in one process. It spawns only `git`,
inside the leased operating-system temporary materialization and to read a
baseline blob; it never invokes `bridge-sync`, never starts either host, and
never runs a hook command. Its `check_accounting` block sums to `checks`.
`scenarios` and `expectations` count what the run actually drove, so a filtered
run reports fewer than the `matrix_scenarios` and `matrix_expectations`
inventory totals beside them; the coverage, safeguard, replay and replay-input
counts stay whole-matrix inventory. Every expectation must pass the closed
`sync-plan-validator/v1` admission contract and also leave the
`sync-plan-diagnostic/v1` companion empty, so a warning line an expectation
emits or drops against the public evidence the replay context derives fails
the suite.

## Materialize, read, validate, compare, clean up

```text
python -B fixtures/m4-hooks/hooks_harness.py materialize native-both-applied
python -B fixtures/m4-hooks/hooks_harness.py replay-input native-both-applied <worktree> --lease <lease>
python -B fixtures/m4-hooks/hooks_harness.py validate-plan native-both-applied <worktree> --lease <lease> --plan <plan.md> --operation-lifecycle <lifecycle>
python -B fixtures/m4-hooks/hooks_harness.py compare native-both-applied <worktree> --lease <lease> --expectation applied --actual-plan <actual-plan.md>
python -B fixtures/m4-hooks/hooks_harness.py cleanup native-both-applied <worktree> --lease <lease>
```

`materialize` accepts an `agent` replay-input id. Most ids equal their scenario
id; `semantics-divergent-annex` splits into `semantics-divergent-annex-keep` and
`semantics-divergent-annex-pending`. The command creates one direct child of the
resolved operating-system temporary directory, initializes and commits a
disposable Git repository, applies the input tree, and installs the canonical
`activation-fixture/v2` profile, the bound `write-capability-fixture/v1`
document, the `replay-bundle-commitment/v1` operation binding, and the replay
envelope under the retained `.git` directory. `migration-v2-v3` creates its
declared two-commit v2 ownership DAG before applying the input snapshot. Never
run a mutation against the checked-in fixture sources.

`replay-input` validates the complete canonical marker, lease and commitment
chain and emits only the closed public allowlist DTO: bound identity, input
bytes, activation-profile facts, decision facts, capability facts and rendered
proposal operations. It never emits an expectation id or path, a plan document,
a post-state name, or any golden or oracle value.

`validate-plan` is the closed `sync-plan-validator/v1` admission contract as the
M3 harness implements it, bound to this suite's replay input. `compare` checks
the independently serialized plan against the expectation and the worktree
against the expected post-state tree. `cleanup` is permanent: it validates the
exact suite, scenario, resolved root, baseline and lease-bound marker before
deleting one named project, and never enumerates the temporary directory.

## Scenario inventory

| id | purpose | replay |
|---|---|---|
| `native-both-applied` | Project one declared hook into an existing hand-formatted Claude carrier and an existing Codex carrier without touching one unowned byte. | agent |
| `idempotent-rerun` | Re-plan against the applied post-state and prove the idempotence law leaves both carriers byte-identical. | agent |
| `format-preserved-unchanged` | Leave a semantically equal but four-space, tab-mixed owned group exactly as the author wrote it. | agent |
| `codex-create-blocked` | Block the absent Codex carrier on the missing strict create while the Claude carrier closure still proceeds. | agent |
| `gate-all-or-nothing` | Force the sibling carrier closure of a class gate entry to zero writes while the blocked carrier closure keeps its scoped blocker. | agent |
| `opt-in-pending` | Ask for the dated opt-in record before projecting a side-effect entry that declares enabled true. | agent |
| `opt-in-confirmed` | Append the confirmed enabled-by record through the source closure and then project both carriers in step order. | agent |
| `acknowledgement-missing-blocked` | Block only the Claude carrier closure when the intent document carries no file-level shared-execution acknowledgement. | agent |
| `degrade-codex-agents-md` | Carry a Claude-only event reminder as one managed root AGENTS.md block while the Claude carrier stays native. | agent |
| `intent-doc-claude` | Carry a Codex-only Interrupt observation as the unconditionally loaded intent document itself, with zero Claude writes. | agent |
| `declared-unsynced-gate` | Serialize a declared-unsynced Codex row for a PermissionRequest gate whose Claude carrier is already converged. | agent |
| `passthrough-preserved` | Update the shared command while both host passthrough keys survive byte-for-byte and in place. | agent |
| `semantics-divergent-annex` | Route an owned Codex handler carrying async true to annex-or-keep and leave the user key untouched. | agent |
| `foreign-handler-keep` | Route an mcp_tool handler inside an owned Claude group to annex-or-keep and never delete it. | agent |
| `guarded-region-nonunique-blocked` | Block a Claude carrier replacement whose resolved write capability attests no replace protocol, and keep that closure selected with its scoped blocker. | agent |
| `carrier-unusable-blocked` | Fail closed on a duplicate object key in the Codex carrier while the Claude carrier closure still proceeds. | agent |
| `inline-hooks-conflict-blocked` | Block the Codex closure when the same Codex layer also declares hooks inline in config.toml. | agent |
| `reverse-adopt-command` | Adopt a hand-edited Claude command into the shared scalar and rerender the Codex carrier from the adopted source. | agent |
| `reverse-adopt-override` | Adopt a hand-edited Codex commandWindows as a per-host override instead of collapsing it into the shared scalar. | agent |
| `both-carriers-conflict` | Defer a two-sided hook conflict in one entry-level decision closure and write neither carrier. | agent |
| `delete-group-reindex` | Converge a proven managed deletion, remove the emptied event member whole, and disclose the positional trust shift. | agent |
| `retrust-required` | Change a Codex timeout override and disclose that the handler goes dark until the user re-trusts it. | agent |
| `migration-v2-v3` | Keep the covenant v2 migration closure limited to entry and rule units and carry zero hook units across the version barrier. | agent |
| `partial-two-carrier` | Report partial without attempting an optimistic inverse after the Codex post-write verification fails and strict compensation is unavailable. | declarative-only |
| `codex-blind-change` | Replace only the Codex commandWindows of a converged handler and disclose the change the trust identity does not cover. | agent |
| `delete-event-emptied` | Remove the only owned group of each carrier, drop both emptied event members whole, and leave each hooks object present and empty. | agent |

The inventory keeps the design record's table order, not byte-wise id order, so
the matrix reads as the record does, and appends any scenario added after the
record was written rather than interleaving it. `validate-matrix` asserts that
exact order. The last two rows are such additions: `codex-blind-change` pins
`codex-trust-blind-change`, the informational warning that is mutually
exclusive with `codex-hook-retrust-required` and which the record's table left
unassigned, and `delete-event-emptied` pins the Codex half of the deletion
rule, where the emptied `"<Event>": [...]` member goes whole because Codex
trust keys are per event, while `"hooks": {}` stays.
`partial-two-carrier` is the one declarative-only scenario: the agent workflow
exposes no reliable fault barrier inside the Codex guarded host call between the
write and its post-write verification, so its plan, exact trees, declared fault
and safeguards are schema-validated instead of executed.

`guarded-region-nonunique-blocked` keeps a historical id. Its coverage token is
`hooks-guarded-patch-unavailable`, and what blocks the closure is the resolved
write capability, which attests neither a strict nor a guarded replace
protocol, rather than a region the outward-only extension rule failed to make
unique. The scenario still carries the `context-never-shortened` safeguard,
because its evidence reaches that capability only after extending the region
outward through the distinguishing matcher line, never by shortening context;
no scenario in this suite blocks on region non-uniqueness itself, because
outward extension over a finite carrier always terminates at a unique region.

## Contract data

[`scenario-matrix.json`](scenario-matrix.json) uses `bridge-m4-hooks-matrix/v1`
and each scenario uses `bridge-m4-hooks-scenario/v1`.
[`tree-manifest.json`](tree-manifest.json) is a named
`bridge-fixture-tree-set/v1` graph resolved by the shared product-neutral helper
in [`../_support/`](../_support/). Every carrier byte a plan may write is a
checked-in tree file under [`shared/`](shared/), rendered with the hook
mechanics in
[`../../skills/bridge-sentinel/scripts/sentinel_mechanics.py`](../../skills/bridge-sentinel/scripts/sentinel_mechanics.py):
`render-hook-group` and `compose-hooks-json` for the two JSON carriers, and
`render-hook-degradation` for the root `AGENTS.md` block. An expectation
therefore pins exact post-state bytes rather than a described shape.

No scenario's post-state adds a repository path that its baseline tree does not
already carry, so no expectation in this suite serializes an
`untracked-files-included` warning.

The activation profiles under [`profiles/`](profiles/) are
`activation-fixture/v2` documents. `default.json` pins `unknown` for both Codex
inputs and emits neither `codex-project-untrusted` nor
`codex-hooks-feature-disabled`; `codex-trusted.json` resolves both so the
`retrust-required` story stays deterministic. Every serialized capability row
must be exactly derivable from the scenario's closed declaration under
[`capabilities/`](capabilities/); absent proof stays `unavailable`. Confirmed
closure authorization comes only from closed `replay-decision-fixture/v1`
documents under `decisions/`.

This suite ships no `fault-schedules/` directory. `fault-schedule-fixture/v1`
binds an executable, phase-bound fixture adapter whose only phase is
`after-confirmation-before-final-preflight`, and M4 ships no such adapter, so
`partial-two-carrier` declares its post-write verification boundary through the
scenario `fault` object instead, exactly as the M3
`verify-failure-no-compensation` scenario does.

## The fixture hook fence

Every `command` and `commandWindows` value anywhere under `fixtures/` must match
`^bridge-fixture-noop( [a-z0-9-]+)?$`, a program that exists on no machine, so
an accidental run is a harmless ENOENT. `check-hook-fence` runs the public
`scan_hook_fence` over the complete `fixtures/` tree, which covers every
`.claude/settings.json`, `.claude/settings.local.json`, `.codex/hooks.json`,
`.codex/config.toml`, and `.claude/rules/hooks.md`. A `shared/` tree file is
stored under an authoring name rather than a carrier name, so the command also
discovers every `<suite>/shared` tree under `fixtures/` (`m2-sync/`,
`m3-rules/` and `m4-hooks/` today) and mirrors every `.json`, `.md` and `.toml`
file they hold into a temporary tree under the carrier name its bytes stand
for, then scans that too. The suites are discovered rather than listed, so the
shared tree of a new suite is inside the fence from its first run instead of
from the day someone remembers to extend a list. It exits non-zero on any
command outside the grammar.

Every carrier is scanned twice. The structured scan reads a carrier through the
reader its host would use, and a byte scan then re-reads the raw bytes of every
carrier that scan visited or failed to read, matching JSON `"command"` and
`"commandWindows"` string values, TOML `command`, `command_windows` and
`commandWindows` string values, and yaml `command:` and `commandWindows:`
lines. All three patterns run over every carrier, so a JSON command spelled
inside an intent document is caught as well. `check-hook-fence` reports both
value counts and the union of the violations, and fails when either scan finds
one. The byte scan is what closes the holes a parser leaves: a carrier that is
unreadable JSON contributes no structured value at all, a duplicate `command`
key shadows every value but the last, and a node the structured reader does not
model contributes nothing, yet in each case the bytes are still fenced.

The fence fails closed rather than quietly shrinking. A shared tree that is
missing, and a shared file whose suffix is neither mirrored nor in the explicit
ignore set, are refusals, not skips. The unreadable list is an informational
census rather than an allowlisted gap: `self-test` pins it to the one
deliberately invalid JSON in `fixtures/hooks-broken-json/`, and separately
requires that the byte scan still read command values out of that carrier, so
the deliberately broken file stays fenced instead of exempt. Adding a second
deliberately broken carrier is therefore an explicit edit of
`FENCE_UNREADABLE_ALLOWLIST`. `self-test` also holds both scans to a
carrier-count and value-count floor, requires the byte scan to reach every
carrier the structured scan touched, and requires it to read at least as many
values as the structured scan. Each floor equals what the closed fixture tree
scans today, so a carrier that disappears fails the run instead of shrinking
the scan silently, and a change that adds carriers raises the floors in the
same change. The Codex hook-trust bypass flag named in
[`../../.claude/rules/fixtures.md`](../../.claude/rules/fixtures.md) appears in
no fixture and in no CI path.

Fixture hook keys are real host-native keys. No fixture or harness step starts
either host against fixture source data or against a materialized fixture tree,
and no work session may set its current working directory inside `fixtures/` or
inside a materialized fixture tree.

## Evidence boundary

- `self-test` never runs `bridge-sync`, never starts a host, and never runs a
  hook command. The only subprocess it spawns is `git`, against the disposable
  leased repository it materializes and deletes. It validates declarations,
  leased materialization, expected trees, `sync-plan/v3` shape and the hook
  fence. An agent must run `$bridge-sync` against a materialized project for
  every agent scenario.
- `bridge-live-operation-journal/v2` is bound by reference. Its fields are
  path-kind generic and `json-owned-span/v1` adds no journal field, so the
  66-case suite in [`../m3-rules/`](../m3-rules/) is the only place it runs.
- A fixture capability is valid only inside the one materialized replay input
  that binds it. It is not evidence for PowerShell, Claude Code tools, Codex
  `apply_patch`, Python file I/O, or any live host adapter.
- Hook bytes are verified only as repository carriers. Codex activation is
  subject to project and per-hook trust, and Claude activation depends on the
  global hook switch after settings precedence, on managed policy settings, and
  on per-run flags. Neither is observable from repository bytes, and no fixture
  result may be read as a runtime guarantee. The exact hedge sentences a report
  or plan must reproduce live in
  [`../../skills/bridge-sentinel/references/report-spec.md`](../../skills/bridge-sentinel/references/report-spec.md).
- On the same Windows machine Claude runs `command` under Git Bash while Codex
  runs `commandWindows` under `pwsh -NoProfile -Command` (collected
  2026-09-07). A shared command must therefore be valid in both shells, which
  is why every fixture command is a plain program invocation with at most one
  lowercase argument.
- Hooks committed to a repository run for everyone who clones it. The
  `bridge:hooks-shared-execution` acknowledgement and the dated `enabled-by`
  record these fixtures exercise are review checkpoints in Git, never
  enforcement boundaries, and Bridge classification is author-declared metadata,
  not a sandbox.
