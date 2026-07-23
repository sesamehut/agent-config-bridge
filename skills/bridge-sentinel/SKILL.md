---
name: bridge-sentinel
description: Checks a Git repository for drift between canonical project agent configuration and its Claude Code/Codex projections, then emits a read-only report. Use after agent-configuration changes, for an explicit bridge-state check, or to validate bridge fixtures.
---

# Bridge sentinel

Scan bridge-managed agent configuration without modifying it. Derive every
state from the normative decision tables and return the prescribed report.

## Runtime

- Requires a Git worktree, Git on `PATH`, and Python 3.9+.
- Resolve support files relative to this `SKILL.md`.
- Put renders, normalized copies, and produced expectation reports in a
  unique OS-temporary directory outside the scan root.

Use the helper for all deterministic comparisons:

```text
<python3> <skill-dir>/scripts/sentinel_mechanics.py self-test
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-trees <master> <copy>
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-files <source> <projection> [--normalize-n]
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-expectation <produced-report> <expected-report>
```

It reads supplied paths and writes JSON to stdout. `self-test` manages only its
own OS-temporary directory. Exit codes: `0` = equal/PASS, `1` =
different/FAIL, `2` = invalid input or execution error.

## Reference map

Read each reference's Contents section, then load a complete section just
before applying it:

| Scan phase | Source-tree sections | Report sections |
|---|---|---|
| Scope and onboarding | Unit model; Onboarding predicate; Marker grammar | Input set; The states |
| Skills | Skill intent supporting file; Skill portability requirements | Per-surface decision tables > Skills; Diff shape; Skill portability lint list |
| AGENTS.md | Marker grammar; Applicability preamble and rendering pipeline; Normalization set N | Per-surface decision tables > Agents-md; Closed observation vocabulary; Fidelity tiers |
| Hooks | Hook intent document; Declared keys and ownership derivation; Projected handler shape | Per-surface decision tables > Hooks; Closed observation vocabulary; Fidelity tiers |
| Output | — | Report document format; Expectation files and the deterministic comparison rule; Codex activation hedge |

Versions: `references/source-tree-spec.md` = `source-tree/v2`;
`references/report-spec.md` = `report/v2`. Read the defining rule before
emitting any normative token.

## Procedure

1. **Preflight.** Run `git --version`. Probe `python3 --version`,
   `python --version`, then `py -3 --version`; use the first actual Python
   version ≥ 3.9 (a Windows Store alias does not qualify). Report a missing
   prerequisite with install guidance. Run `self-test` and stop on failure.
2. **Resolve inputs.** Repo mode uses `git rev-parse --show-toplevel`.
   Fixture mode reads scan root and excludes from the expectation header and
   ignores outer-repository history. Build repo bytes with scoped
   `git ls-files`, applying excludes before every rule. Reserve untracked
   scan-surface files for Local environment notes.
3. **Establish scope.** Evaluate the onboarding predicate, then enumerate the
   entry unit, rule shards except `.claude/rules/hooks.md`, schema-valid hook
   entries, and skill masters. Apply the source-path grammar before emitting
   `unrepresentable-source-path`.
4. **Check skills.** For each name in masters union copies, apply S1–S4.
   Use `compare-trees`; do not eyeball file sets or bytes. Compute every
   portability lint on the master only. A directory without `SKILL.md` is not
   a unit; mention it only in Evidence and notes.
5. **Check AGENTS.md.** Parse blocks with the marker grammar. Render each
   source unit through the exact pipeline. Compare rendered source and block
   body with `compare-files --normalize-n`, using scratch files outside the
   project only. Apply cases A1–A7.
6. **Check hooks.** Parse hook intent entries and both JSON surfaces. Emit one
   `intent-doc-anomaly` per schema violation. Derive ownership from valid
   intent entries, locate marked handlers, apply all H-cases, and emit
   `undeclared-hooks-key` only for groups that are neither owned nor marked.
   Do not execute hook commands. Evaluate the complete observation registry;
   derive `agents-md-size` solely from its effective-budget rule.
7. **Assemble output.** Emit the exact report skeleton, sorted findings and
    observations, tiers, annotations, no-source-unit rows, and the Codex
    activation hedge. Cite intent records and, in repo mode only, relevant
    `git log` or `git blame` pointers in Evidence and notes.
8. **Compare expectations.** In fixture or dogfood mode, keep the produced
    report outside the project and run `compare-expectation`. Report PASS or
    FAIL and reproduce the helper's exact differing fields on failure.

## Hard boundary

Keep the scanned project unchanged. Temporary helper and comparison files stay
outside it. Return the report as session output and leave no persistent product
artifact.
