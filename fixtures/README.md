# Fixtures

Verification beds for the bridge-sentinel skill. Each fixture is a miniature
project laid out with real host-native file names (`CLAUDE.md`, `AGENTS.md`,
`.claude/`, `.agents/`, `.codex/`). Read-only M1 projects are scanned in
place. Mutation vectors remain inert source data and are materialized only as
lease-bound disposable Git repositories under the operating-system temporary
directory. Authoring rules — containment conventions, byte discipline, and
the reasons behind them — live in
[`.claude/rules/fixtures.md`](../.claude/rules/fixtures.md). All fixture
skills are inert by construction: a `fixture-` name prefix,
harmless bodies, Claude `skillOverrides: "off"`, and Codex
`policy.allow_implicit_invocation: false`. Only the Claude-extension test
fixture carries `disable-model-invocation` in `SKILL.md`.

## Inventory

| Fixture | Purpose |
|---|---|
| [`not-onboarded/`](not-onboarded/) | A project the bridge has never onboarded: a hand-written `AGENTS.md` and a copy-only Codex skill reported as adoption candidates, unprojected entry and rule-shard units, a vacuous hooks surface, and zero drift by construction. |
| [`onboarded/`](onboarded/) | A project carrying the exact two-part `covenant/v2` anchor and exercising the onboarded regime end to end: in-sync, neutral reconcile drift, adoption-candidate, blocked skill-loadability, declared-unsynced hook, marked orphan hook, representative portability lints and behavior degradation, neutral Codex live-activation annotations, claude-only subtraction, strict intent comments, pv2 scoped-rule rendering, and the undeclared-hooks-key and nested-agents-md observation channels. |
| [`dogfood/`](dogfood/) | Expectation only — no fixture tree. Its `expected-report.md` targets this repository itself (see below). |
| [`m2-sync/`](m2-sync/) | Declarative write-side contract vectors. A standard-library harness validates fixture data, materializes replayable inputs into marked OS-temporary Git repositories, and compares an agent-produced sync plan plus exact post-state. Its self-test does not execute the workflow. |
| [`m3-rules/`](m3-rules/) | Declarative `source-tree/v4` reconciliation vectors. Its standard-library harness validates 41 scenarios, capability-bound `sync-plan/v2` expectations, exact named trees and commit DAGs, the 66-case `bridge-live-operation-journal/v2` suite, per-process temporary-session isolation, platform-gated guarded-preflight fault evidence, lease-bound replay, the closed public `sync-plan-diagnostic/v1` warning explainer, and cleanup without executing the workflow. |

The two M1 fixture projects exercise every `report/v4` Sentinel state. M2 and
M3 mutation coverage is inventoried separately in
[`m2-sync/README.md`](m2-sync/README.md) and
[`m3-rules/README.md`](m3-rules/README.md).

## Expectation files and run parameters

Every expectation file (`expected-report.md`) declares its own run
parameters in its header, then its normative content — nothing else:

- `- expectation:` — the report spec version the expectation was written
  against (`report/v4`). A sentinel run producing a different `- spec:`
  value fails the comparison loudly; documents are never compared across
  spec versions.
- `- scan root:` — resolved relative to the directory containing the
  expectation file (`.` means the fixture directory itself; `../..` means
  this repository's root).
- `- scope excludes:` — comma+space-separated glob filters passed to the
  sentinel as a run parameter (gitignore semantics, anchored at the scan
  root), or `(none)`.
- `- activation profile:` — a contained `activation-fixture/v1` JSON file, or
  `environment-dependent` to exclude live-activation and host-capability
  observations from deterministic comparison.
- `- onboarding:` — the expected project-level flag
  (`onboarded`, `not-onboarded`, or `blocked`).

The expected `## Findings` table and `## Observations` lines follow the
header. The acceptance check is the deterministic parse-based comparison
rule defined in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md):
run the sentinel with the declared run parameters, then compare the spec
version, the scope-excludes echo, the onboarding flag, the findings rows
(sorted, multiset semantics, cell-by-cell), and the observation lines.
There are no magic directory names — any future expectation target reuses
the same header mechanism with a different scan root.

## `dogfood/`

`fixtures/dogfood/` contains an expectation and its activation profile, but no
fixture project tree. It declares scan root `../..` — this repository itself,
scanned in repo mode — and scope excludes `fixtures/**`, so fixture-bed growth
in later milestones never touches it. The expectation reflects the current
repository ownership surface; update it in the same change as any
scan-relevant repository bytes outside `fixtures/`.

## Codex hooks shape

The `onboarded/.codex/hooks.json` fixture uses the current official Codex
shape: a top-level object whose `hooks` key holds the event-name map,
carrying the same group/handler family as Claude's `hooks` settings value.
The shape was verified against the official hooks reference and the
openai/codex source on 2026-07-23; research evidence lives in
`knowledge/hooks.md`.
