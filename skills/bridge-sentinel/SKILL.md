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
<python3> <skill-dir>/scripts/sentinel_mechanics.py inspect-tree <root>
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-trees <master> <copy>
<python3> <skill-dir>/scripts/sentinel_mechanics.py git-manifest <repo-root> <repo-relative-unit> [--revision <commit>] [--include-untracked] [--require-executable <relative-path>]
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-git-trees <repo-root> <repo-relative-source-unit> <repo-relative-projection-unit> [--revision <commit>] [--include-untracked] [--direction <observe|source-to-projection|projection-to-source>] [--require-executable <relative-path>]
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-files <source> <projection> [--normalize-n]
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-expectation <produced-report> <expected-report>
```

It reads supplied paths and writes JSON to stdout. `self-test` manages only its
own OS-temporary directory. Exit codes: `0` = equal/PASS, `1` =
different/FAIL, `2` = invalid input or execution error.
`git-manifest` and `compare-git-trees` implement Git-tree identity over path,
entry type, bytes, and mode. `compare-trees` is deliberately limited to
filesystem paths and bytes and returns `mode_checked: false`; never use it
alone to claim Git-tree equality. Sentinel always uses direction `observe`;
write directions and explicit executable requirements belong to bridge-sync.

## Reference map

Read each reference's Contents section, then load a complete section just
before applying it:

| Scan phase | Source-tree sections | Report sections |
|---|---|---|
| Scope and onboarding | Unit model; Onboarding anchor; Marker grammar | Input set; The states |
| Skills | Skill intent supporting file; Managed skill tree; Skill compatibility layers | Per-surface decision tables > Skills; Diff shape; Skill portability lint list |
| AGENTS.md | Marker grammar; Applicability preamble and rendering pipeline; Normalization set N | Per-surface decision tables > Agents-md; Closed observation vocabulary; Fidelity tiers |
| Hooks | Hook intent document; Declared keys and ownership derivation; Projected handler shape | Per-surface decision tables > Hooks; Closed observation vocabulary; Fidelity tiers |
| Output | — | Report document format; Expectation files and the deterministic comparison rule; Codex runtime hedges |

Versions: `references/source-tree-spec.md` = `source-tree/v3`;
`references/report-spec.md` = `report/v3`. Read the defining rule before
emitting any normative token.

## Procedure

1. **Preflight.** Run `git --version`. Probe `python3 --version`,
   `python --version`, then `py -3 --version`; use the first actual Python
   version ≥ 3.9 (a Windows Store alias does not qualify). Report a missing
   prerequisite with install guidance. Run `self-test` and stop on failure.
2. **Resolve inputs.** Repo mode uses `git rev-parse --show-toplevel`.
   Fixture mode reads scan root and excludes from the expectation header and
   ignores outer-repository history. Build repo bytes with scoped
   `git-manifest` snapshots, preserving path, type, bytes, HEAD/index mode
   evidence, and any reliable POSIX worktree mode change. Apply excludes
   before every rule. Reserve untracked scan-surface files for Local
   environment notes; never pass `--include-untracked` for Sentinel managed
   equality.
3. **Establish scope.** Validate both versioned covenant halves against the
   exact templates under `../../templates/covenant/`, then evaluate onboarding.
   A partial, modified, malformed, untracked, or version-mismatched pair is
   blocked. Enumerate the
   entry unit, rule shards except `.claude/rules/hooks.md`, schema-valid hook
   entries, and skill masters. Apply the source-path grammar before emitting
   `unrepresentable-source-path`.
4. **Check skills.** For each name in masters union copies, apply S0, then
   S1–S4. Reject symlinks, reparse points, gitlinks, special files, path
   escapes, case-fold collisions, and `mode-limited` evidence. Use
   `compare-git-trees` for complete current identity. Use `compare-trees`
   only as a named byte-layer diagnostic, never as mode evidence. Never let
   an ignored or untracked file enter a Sentinel equality result. Include
   tracked deletions in the unit-wide case-fold collision domain. Compute
   every compatibility lint on the master only. A directory without
   `SKILL.md` is not a unit; mention non-empty occupancy only in Evidence and
   notes. S4 is always `adoption-candidate`/`annex-or-keep`, even in an
   onboarded project; only bridge-sync may use history to arbitrate a managed
   source-side deletion.
5. **Check AGENTS.md.** Parse blocks with the marker grammar. Render each
   source unit through the exact pipeline. Compare rendered source and block
   body with `compare-files --normalize-n`, using scratch files outside the
   project only. Apply cases A0–A7.
6. **Check hooks.** Parse hook intent entries and both JSON surfaces. Emit one
   `intent-doc-anomaly` per schema violation. Derive ownership from valid
   intent entries, locate marked handlers, apply all H-cases, and emit
   `undeclared-hooks-key` only for groups that are neither owned nor marked.
   Do not execute hook commands. Evaluate the complete observation registry;
   derive `agents-md-size` solely from its effective-budget rule.
7. **Assemble output.** Emit the exact report skeleton, sorted findings and
    observations, tiers, annotations, no-source-unit rows, and both applicable
    Codex runtime hedges. Current diff shape may appear only as evidence. Never
    emit a write direction, adoption decision, or conflict conclusion; every
    drift action is `reconcile`. Cite intent records and, in repo mode only,
    relevant `git log` or `git blame` pointers in Evidence and notes.
8. **Compare expectations.** In fixture or dogfood mode, keep the produced
    report outside the project and run `compare-expectation`. Report PASS or
    FAIL and reproduce the helper's exact differing fields on failure.

## Hard boundary

Keep the scanned project unchanged. Temporary helper and comparison files stay
outside it. Return the report as session output and leave no persistent product
artifact.
