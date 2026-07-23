# Fixtures

Verification beds for the bridge-sentinel skill. Each fixture is a miniature
project laid out with real host-native file names (`CLAUDE.md`, `AGENTS.md`,
`.claude/`, `.agents/`, `.codex/`) and is scanned in place — never copied to
scratch, never renamed. Authoring rules — containment conventions, byte
discipline, and the reasons behind them — live in
[`.claude/rules/fixtures.md`](../.claude/rules/fixtures.md). All fixture
skills are inert by construction: a `fixture-` name prefix,
harmless bodies, Claude `skillOverrides: "off"`, and Codex
`policy.allow_implicit_invocation: false`. Only the Claude-extension test
fixture carries `disable-model-invocation` in `SKILL.md`.

## Inventory

| Fixture | Purpose |
|---|---|
| [`not-onboarded/`](not-onboarded/) | A project the bridge has never onboarded: a hand-written `AGENTS.md` reported as an adoption candidate, unprojected entry and rule-shard units, vacuous hooks and skills surfaces, and zero drift by construction. |
| [`onboarded/`](onboarded/) | A bridge-managed project exercising the onboarded regime end to end: in-sync rows on all three surfaces, all three drift resolutions (adopt-to-source, reproject-from-source, conflict), a skill adoption candidate, a declared-unsynced hook target, a marked orphan hook handler, every skill portability lint, claude-only subtraction, the scoped-rule applicability preamble on a verbatim in-sync block, a semantic-mode managed block, and the undeclared-hooks-key and nested-agents-md observation channels. |
| [`dogfood/`](dogfood/) | Expectation only — no fixture tree. Its `expected-report.md` targets this repository itself (see below). |

Together the two fixture projects exercise every report state, including the
explicit non-verbatim `semantic-mode-block` path.

## Expectation files and run parameters

Every expectation file (`expected-report.md`) declares its own run
parameters in its header, then its normative content — nothing else:

- `- expectation:` — the report spec version the expectation was written
  against (`report/v2`). A sentinel run producing a different `- spec:`
  value fails the comparison loudly; documents are never compared across
  spec versions.
- `- scan root:` — resolved relative to the directory containing the
  expectation file (`.` means the fixture directory itself; `../..` means
  this repository's root).
- `- scope excludes:` — comma+space-separated glob filters passed to the
  sentinel as a run parameter (gitignore semantics, anchored at the scan
  root), or `(none)`.
- `- onboarding:` — the expected project-level flag
  (`onboarded` or `not-onboarded`).

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

`fixtures/dogfood/` contains only an expectation file. It declares scan
root `../..` — this repository itself, scanned in repo mode — and scope
excludes `fixtures/**`, so fixture-bed growth in later milestones never
touches it. The expectation reflects the repository after all M1 artifacts
have landed; it must be updated in the same commit as any change to
scan-relevant repository bytes outside `fixtures/`.

## Codex hooks shape

The `onboarded/.codex/hooks.json` fixture uses the current official Codex
shape: a top-level object whose `hooks` key holds the event-name map,
carrying the same group/handler family as Claude's `hooks` settings value.
The shape was verified against the official hooks reference and the
openai/codex source on 2026-07-23; research evidence lives in
`knowledge/hooks.md`.
