# Fixtures

Verification beds for the bridge-sentinel skill. Each fixture is a miniature
project laid out with real host-native file names (`CLAUDE.md`, `AGENTS.md`,
`.claude/`, `.agents/`, `.codex/`). Read-only M1 projects are scanned in
place. Mutation vectors remain inert source data and are materialized only as
lease-bound disposable Git repositories under the operating-system temporary
directory. Authoring rules, containment conventions, byte discipline, and
the reasons behind them live in
[`.claude/rules/fixtures.md`](../.claude/rules/fixtures.md). All fixture
skills are inert by construction: a `fixture-` name prefix,
harmless bodies, Claude `skillOverrides: "off"`, and Codex
`policy.allow_implicit_invocation: false`. Only the Claude-extension test
fixture carries `disable-model-invocation` in `SKILL.md`. All fixture hooks
are inert the same way; see [Hook fence](#hook-fence) below.

## Inventory

| Fixture | Purpose |
|---|---|
| [`not-onboarded/`](not-onboarded/) | A project the bridge has never onboarded: a hand-written `AGENTS.md` and a copy-only Codex skill reported as adoption candidates, unprojected entry and rule-shard units, a vacuous hooks surface, and zero drift by construction. |
| [`onboarded/`](onboarded/) | A project carrying the exact two-part `covenant/v3` anchor and exercising the onboarded regime end to end: in-sync, neutral reconcile drift, adoption-candidate, blocked skill-loadability, representative portability lints and behavior degradation, neutral Codex live-activation annotations, claude-only subtraction, strict intent comments, pv2 scoped-rule rendering, and the nested-agents-md observation channel. Its `source-tree/v5` intent document carries the file-level `bridge:hooks-shared-execution` acknowledgement, a `class` on every entry, and a dated `enabled-by` record on its one `gate`. Hook coverage: one in-sync native pair on `sentinel-stop` plus a Claude-only in-sync native row on `sandbox-guard`, a drift/reconcile pair for the declared but unprojected `fmt-on-save`, the `declared-unsynced` Codex row of `sandbox-guard`, the marked orphan Codex handler, the user-owned undeclared `SessionStart` group, `awaiting-host-trust` on the in-sync Codex row, and the `hook-output-not-delivered` and `matcher-grammar-divergent` observations. |
| [`hooks-cases/`](hooks-cases/) | Claude carrier discrimination on `.claude/settings.json`: H-EXTRA-KEYS, H-FIELD-ABSENT, H-FIELD-DIFF, and H-MULTI. Its pinned profile is the only read-side one that resolves both Codex live inputs (`codex_project_trust: untrusted`, `codex_hooks_feature: disabled`), so `codex-project-untrusted` and `codex-hooks-feature-disabled` are deterministically compared. |
| [`hooks-broken-json/`](hooks-broken-json/) | Unreadable and unmodelled hook carriers: a `.codex/hooks.json` that is valid UTF-8 but invalid JSON, which emits `json-parse-error` and drives the Codex rows to H-NOFILE while the Claude rows are still evaluated, plus a sibling carrier with a duplicate object key, which emits `hooks-carrier-unmodelled (duplicate-key)`. |
| [`hooks-doc-anomalies/`](hooks-doc-anomalies/) | Intent-document schema violations in one document: a missing prose bullet, two `yaml` blocks in one entry, a duplicate id, a duplicate `(event, effective-matcher, host)` ownership triple, an override without `override-reason`, a `native` tier on `Interrupt` for Claude, and a `class: side-effect` entry with `enabled: true` and no `enabled-by`. Every invalidating violation emits one `intent-doc-anomaly` line and its entry emits no unit row. |
| [`hooks-disabled/`](hooks-disabled/) | Inertness signals side by side: H-DISABLED-OK and H-DISABLED-PRESENT, a tracked settings carrier whose global hook switch is off (`hooks-globally-disabled`), and a tracked `.claude/settings.local.json` carrying a `hooks` key (`local-hooks-present`). |
| [`hooks-prose/`](hooks-prose/) | Both prose surfaces: `intent-doc` on Claude (H-DOC, zero carrier bytes) and `agents-md` on Codex (H-DEGRADED-OK, H-DEGRADED-DIFF, H-DEGRADED-MISSING, H-DEGRADED-NATIVE-PRESENT) with the closed `hd1` block template, plus an orphan `hooks/<id>` block in `AGENTS.md` that hits case A8. |
| [`hooks-inline-codex/`](hooks-inline-codex/) | A tracked `.codex/config.toml` declaring an inline `[hooks.Stop]` table beside a valid `.codex/hooks.json` (`codex-inline-hooks-present (Stop)`). Detection is the shallow byte scan, never a TOML parse. |
| [`hooks-inline-codex-pointer/`](hooks-inline-codex-pointer/) | The sibling project for the legacy form of the same hazard: the only hooks bytes in its tracked `.codex/config.toml` are the top-level `hooks = "<path>"` pointer key (`codex-inline-hooks-present (pointer-key)`). It is a separate scan root, so neither project reports the other as a nested marker. |
| [`hooks-foreign/`](hooks-foreign/) | Host keys outside the declared schema: H-FOREIGN-HANDLER (a `mcp_tool` handler inside an owned group), H-SEMANTICS-DIVERGENT (`async: true` on an owned Claude handler), and a passthrough `additionalContextLimit` that must still report H-OK with `behavior-degraded`. |
| [`dogfood/`](dogfood/) | Expectation only, no fixture tree. Its `expected-report.md` targets this repository itself (see below). |
| [`m2-sync/`](m2-sync/) | Declarative write-side contract vectors. A standard-library harness validates fixture data, materializes replayable inputs into marked OS-temporary Git repositories, and compares an agent-produced sync plan plus exact post-state. Its self-test does not execute the workflow. |
| [`m3-rules/`](m3-rules/) | Declarative `source-tree/v5` reconciliation vectors. Its standard-library harness validates 41 scenarios, capability-bound `sync-plan/v3` expectations including the two pinned hook sections, exact named trees and commit DAGs, the 66-case `bridge-live-operation-journal/v2` suite, per-process temporary-session isolation, platform-gated guarded-preflight fault evidence, lease-bound replay, the closed public `sync-plan-diagnostic/v1` warning explainer, and cleanup without executing the workflow. |
| [`m4-hooks/`](m4-hooks/) | Declarative hook-projection vectors: the 26-scenario, 27-expectation `bridge-m4-hooks-matrix/v1` suite covering byte-stable `json-owned-span/v1` composition, both carrier closures, the opt-in and acknowledgement blockers, degradation, adoption and reverse adoption, and the Codex re-trust disclosures. `hooks_harness.py` imports `m3-rules/fixture_harness.py` for the plan grammar, validator, comparison, materialization, and replay machinery instead of reimplementing them, binds `bridge-live-operation-journal/v2` by reference rather than re-running its suite, and adds `check-hook-fence` over the complete fixture tree. |
| [`_support/`](_support/) | Shared product-neutral harness helpers: named tree-manifest materialization, disposable Git repositories, exact post-tree and structural plan comparison, and no-follow root-child access. Imported by `m3-rules/fixture_harness.py` and, through it, by the M4 harness; `m2-sync/` predates it and stays self-contained. Not a fixture project and never scanned as one. |

The two M1 projects and the eight hook projects together exercise every
`report/v5` Sentinel state, every H-case except `H-T4-PRESENT`, and every
read-side hook observation token. Two read-side gaps stay open and are
tracked here rather than claimed as covered: no fixture pairs a
`surface: none` target with a carrier handler that occupies its candidate
group, so the `H-T4-PRESENT` branch that turns a `declared-unsynced` row into
`drift`/`reconcile` is never taken; and `hooks-carrier-unmodelled` is
exercised only in its `(duplicate-key)` detail, never `(unmodelled-shape)`.
M2, M3, and M4 mutation coverage is inventoried separately in
[`m2-sync/README.md`](m2-sync/README.md),
[`m3-rules/README.md`](m3-rules/README.md), and
[`m4-hooks/README.md`](m4-hooks/README.md).

## Expectation files and run parameters

Every expectation file (`expected-report.md`) declares its own run
parameters in its header, then its normative content and nothing else:

- `- expectation:` is the report spec version the expectation was written
  against (`report/v5`). A sentinel run producing a different `- spec:`
  value fails the comparison loudly; documents are never compared across
  spec versions.
- `- scan root:` is resolved relative to the directory containing the
  expectation file (`.` means the fixture directory itself; `../..` means
  this repository's root).
- `- scope excludes:` is a comma+space-separated list of glob filters passed
  to the sentinel as a run parameter (gitignore semantics, anchored at the
  scan root), or `(none)`.
- `- activation profile:` is a contained `activation-fixture/v2` JSON file, or
  `environment-dependent` to exclude live-activation and host-capability
  observations from deterministic comparison. `activation-fixture/v2` adds the
  required `codex_project_trust` (`trusted`, `untrusted`, `unknown`) and
  `codex_hooks_feature` (`enabled`, `disabled`, `unknown`) keys.
  `hooks-cases/` is the one read-side fixture that resolves both, pinning
  `untrusted` and `disabled` so the two Codex inertness observations are
  compared; every other read-side profile declares `unknown` for both, which
  emits neither observation. The write-side profile
  `m4-hooks/profiles/codex-trusted.json` resolves both as `trusted` and
  `enabled`.
- `- onboarding:` is the expected project-level flag
  (`onboarded`, `not-onboarded`, or `blocked`).

The expected `## Findings` table and `## Observations` lines follow the
header. The acceptance check is the deterministic parse-based comparison
rule defined in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md):
run the sentinel with the declared run parameters, then compare the spec
version, the scope-excludes echo, the onboarding flag, the findings rows
(sorted, multiset semantics, cell-by-cell), and the observation lines.
There are no magic directory names: any future expectation target reuses
the same header mechanism with a different scan root.

## `dogfood/`

`fixtures/dogfood/` contains an expectation and its activation profile, but no
fixture project tree. It declares scan root `../..`, this repository itself,
scanned in repo mode, and scope excludes `fixtures/**`, so fixture-bed growth
in later milestones never touches it. The expectation reflects the current
repository ownership surface; update it in the same change as any
scan-relevant repository bytes outside `fixtures/`. This repository declares no
hook intent document and no `hooks` key in any carrier, so its hooks surface
stays vacuous; hook dogfooding is deferred to a dedicated M6 example project,
never to arming this repository's own carriers.

## Codex hooks shape

The `onboarded/.codex/hooks.json` fixture uses the current official Codex
shape: a top-level object whose `hooks` key holds the event-name map,
carrying the same group/handler family as Claude's `hooks` settings value.
An optional top-level `description` string is the user's only metadata slot;
Bridge never writes, creates, repairs, or reformats it. The shape was verified
against the official hooks reference and the openai/codex source on
2026-07-23, and the top-level-only strictness of `deny_unknown_fields` was
scoped against the same source on 2026-09-07: an unknown key inside a matcher
group or a handler object is silently ignored rather than rejecting the file.
Research evidence and collection dates live in
[`../knowledge/hooks.md`](../knowledge/hooks.md).

## Hook fence

Every `command` and `commandWindows` value anywhere under `fixtures/` matches
`^bridge-fixture-noop( [a-z0-9-]+)?$`, a program that exists on no machine, so
an accidental run is a harmless ENOENT. No fixture command predates the fence
and no fixture or harness step ever starts a host against fixture bytes with
hooks enabled. The binding rules, including the never-execute clause and the
ban on the Codex per-hook trust bypass flag, live in
[`.claude/rules/fixtures.md`](../.claude/rules/fixtures.md).

The mechanical check is narrower than the rule, so read it as a floor rather
than a proof. `scan_hook_fence()` in `sentinel_mechanics.py`, run over the
whole tree by `m4-hooks/hooks_harness.py check-hook-fence`, reads
`.claude/settings.json`, `.claude/settings.local.json`, `.codex/hooks.json`,
`.codex/config.toml`, and `.claude/rules/hooks.md`, plus every
`m3-rules/shared/` and `m4-hooks/shared/` authoring file mirrored under the
carrier name its bytes stand for. Two classes stay outside it and are reviewed
by hand: a carrier it cannot parse, which it reports as unreadable rather than
as a violation, such as the deliberately invalid JSON in `hooks-broken-json/`;
and carrier snippets quoted inside `m4-hooks/expectations/*.md`.
