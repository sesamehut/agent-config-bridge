---
name: bridge-sentinel
description: Checks a Git repository for drift between canonical project agent configuration and its Claude Code/Codex projections, then emits a read-only report. Use after agent-configuration changes, when explicitly asked to verify bridge state, or when validating bridge fixtures; do not use for ordinary session wrap-up.
---

# Bridge sentinel

Execute a read-only scan of bridge-managed agent configuration. Classify every
row from the normative decision tables; never infer a consistency state from
prose or repair the project.

## Requirements and paths

- Require a Git worktree and Git on `PATH`.
- Require Python 3.9 or newer for `scripts/sentinel_mechanics.py`. Both
  prerequisites are verified by the environment preflight (checklist step 1)
  before any scan work starts; when one is missing, the preflight reports it
  to the user with concrete install guidance. Never substitute an approximate
  in-model comparison for the helper.
- Resolve every supporting path from the directory containing this `SKILL.md`,
  never from the process working directory.
- `bridge-intent.yaml` is maintenance provenance for this skill source. Do not
  load it during an ordinary scan; consult intent records only when this skill
  directory is itself in the scan scope or arbitration evidence is requested.
- Treat the session scratchpad as a unique directory under the host operating
  system's temporary directory, resolved outside the scan root. Use it only
  when rendering an intermediate body is unavoidable.

The comparison subcommands are read-only: they read the paths supplied and
write JSON to stdout. `self-test` creates and removes only its own unique
directory under the operating system's temporary directory. Exit codes are
`0` for equal/PASS, `1` for different/FAIL, and `2` for invalid input or an
execution error.

```text
<python3> <skill-dir>/scripts/sentinel_mechanics.py self-test
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-trees <master> <copy>
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-files <source> <projection> [--normalize-n]
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-expectation <produced-report> <expected-report>
```

An exit code of `1` from a comparison is an expected data result, not a tool
failure.

## Load normative references progressively

Both references are relative to this skill:

- `references/source-tree-spec.md`, version `source-tree/v2`
- `references/report-spec.md`, version `report/v2`

Read each file's Contents section first. Then load the complete sections needed
immediately before applying them:

| Scan phase | Source-tree sections | Report sections |
|---|---|---|
| Scope and onboarding | Unit model; Onboarding predicate; Marker grammar | Input set; States and decision tables |
| Skills | Skill portability requirements; Skill intent supporting file | Skills decision table; Diff shape; Skill portability lints |
| AGENTS.md | Marker grammar; Rendering pipeline; Normalization set N | Agents-md decision table; Observations; Fidelity tiers |
| Hooks | Hook intent document; ownership derivation; projected handler shape | Hooks decision table; Observations; Fidelity tiers |
| Output | — | Report format; Expectation comparison; Codex activation hedge |

Do not load either long reference wholesale at startup. Before emitting a
normative token, read the full table or rule that defines it.

## Checklist

1. **Preflight the environment.** Before any scan work, confirm
   `git --version` succeeds. Locate the Python interpreter by probing, in
   order, `python3 --version`, `python --version`, and `py -3 --version`
   (Windows launcher); select the first that reports version 3.9 or newer. A
   probe counts only when it prints an actual Python version — on Windows a
   stub `python` alias may print a Microsoft Store hint instead. If Git or a
   suitable Python is missing, stop before scanning and tell the user exactly
   what is missing and how to install it (for example Python 3.9+ from
   python.org, or via `winget install Python.Python.3.12`,
   `apt install python3`, or `brew install python`). Then run `self-test`
   with the selected interpreter and stop on any failure.
2. **Resolve mode and inputs.** In repo mode, set scan root to
   `git rev-parse --show-toplevel`. In fixture mode, resolve scan root and
   scope excludes from the expectation header. Fixture scans are
   parent-history-blind: never use the outer repository's history as fixture
   evidence.
3. **Pin repository bytes.** Enumerate tracked inputs with `git ls-files`
   scoped to the scan root, then apply expectation excludes before every
   rule. Mention untracked scan-surface files only under Local environment
   notes.
4. **Evaluate onboarding.** Parse well-formed managed-block pairs, the hook
   intent document and owned hook groups, bridge-marked hook handlers,
   byte-identical same-name skill trees, and the covenant shard exactly as
   the onboarding predicate defines them.
5. **Enumerate units.** Enumerate the entry unit, rule shards excluding
   `.claude/rules/hooks.md`, schema-valid hook intent entries, and skill
   masters. Emit `unrepresentable-source-path` only from the specified path
   grammar.
6. **Check skills.** For each name in masters union copies, apply cases S1–S4.
   Use `compare-trees`; do not eyeball file sets or bytes. Compute every
   portability lint on the master only. A directory without `SKILL.md` is not
   a unit; mention it only in Evidence and notes.
7. **Check AGENTS.md.** Parse blocks with the marker grammar. Render each
   source unit through the exact pipeline. Compare rendered source and block
   body with `compare-files --normalize-n`, using scratch files outside the
   project only. Apply cases A1–A7.
8. **Check hooks.** Parse hook intent entries and both JSON surfaces. Emit one
   `intent-doc-anomaly` per schema violation. Derive ownership from valid
   intent entries, locate marked handlers, apply all H-cases, and emit
   `undeclared-hooks-key` only for groups that are neither owned nor marked.
   Never execute a hook command.
9. **Apply cheap guards.** Evaluate every observation in the closed registry.
   For `agents-md-size`, derive the effective budget B from a valid tracked
   `.codex/config.toml` value or the documented default, and use the registry's
   `floor(7 × B / 8)` threshold. Do not hard-code a second threshold here.
10. **Assemble output.** Emit the exact report skeleton, sorted findings and
    observations, tiers, annotations, no-source-unit rows, and the Codex
    activation hedge. Cite intent records and, in repo mode only, relevant
    `git log` or `git blame` pointers in Evidence and notes.
11. **Compare expectations.** In fixture or dogfood mode, keep the produced
    report outside the project and run `compare-expectation`. Report PASS or
    FAIL and reproduce the helper's exact differing fields on failure.

## Hard boundary

The sentinel MUST NOT create, modify, or delete any file under the scanned
project; scratch files for rendering and diff mechanics go OUTSIDE the project
(the session scratchpad). The report is session output. The product writes
nothing to disk.
