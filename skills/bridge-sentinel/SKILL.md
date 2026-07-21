---
name: bridge-sentinel
description: Read-only drift sentinel for bridge-managed agent configuration. Scans skill copies, AGENTS.md managed blocks, and declared hooks keys against the canonical source tree; reports states, never repairs. Use on demand, at session wrap-up, or against fixtures/ for verification.
---

# Bridge sentinel

You are executing the bridge drift sentinel: a read-only, agent-executed
checklist that compares a project's canonical agent-configuration source
tree against its host-native projections and produces a report. Before
scanning, read both normative reference files, located relative to this
skill's directory:

- `references/source-tree-spec.md` (spec version `source-tree/v1`) — the
  source-tree conventions: unit model, onboarding predicate, marker grammar,
  applicability preamble and rendering pipeline, normalization set N,
  frontmatter schemas, hook-intent entry format, and skill portability
  requirements.
- `references/report-spec.md` (spec version `report/v1`) — the report
  contract: states and detection rules, per-surface decision tables, diff
  shape, observations, fidelity tiers, portability lints, report document
  format, and the deterministic expectation-comparison rule.

Use only the host's built-in tools and `git` commands — no wrapper scripts,
no environment-variable interpolation, no code beyond what the checklist
names. Every state in the report comes from the decision tables; you never
judge in-sync versus drift yourself.

**Hard read-only rule**: the sentinel MUST NOT create, modify, or delete any
file under the scanned project; scratch files for rendering and diff
mechanics go OUTSIDE the project (the session scratchpad). The report is
session output. The product writes nothing to disk.

## Checklist (execute in order)

1. **Mode, scan root, run parameters.** Repo mode: scan root = `git rev-parse
   --show-toplevel`. Fixture/expectation mode (an expectation file is given
   or named): scan root and scope excludes come from the expectation header
   (expectation format in `references/report-spec.md`). Fixture scans are
   parent-history-blind: use frontmatter intent records plus file structure
   only; never consult the outer repo's git history as fixture evidence.

2. **Read the specs.** Load both reference files; confirm `report/v1` and
   `source-tree/v1`.

3. **Pin the input set.** `git ls-files` under the scan root (fixture mode:
   `git ls-files -- <fixture path>` of the outer repo), then apply the scope
   excludes as a filter. Note (do not compare) untracked files at scan
   surfaces for "Local environment notes".

4. **Evaluate the onboarding predicate** (`references/source-tree-spec.md`)
   and record which trigger fired. Mechanics: find well-formed managed block
   PAIRS in the root `AGENTS.md` per the marker grammar's line, placement,
   and malformation rules (a matched start marker plus end marker outside
   code fences; a bare unpaired start line never fires trigger (a)); parse
   the hook intent document and check owned-group existence; grep both hooks
   files for `"statusMessage"` values beginning `[bridge:`; compare
   same-name skill directories byte-wise; stat
   `.claude/rules/bridge-covenant.md`.

5. **Enumerate source units** per the unit model in
   `references/source-tree-spec.md` (the entry unit, rule shards excluding
   `.claude/rules/hooks.md`, hook intent entries, skill masters), flagging
   paths outside the source-path charset with the
   `unrepresentable-source-path` observation.

6. **Skills check.** For each name in masters ∪ copies apply the skills
   decision table (cases S1–S4 in `references/report-spec.md`) with its
   regime branches. Byte comparison via git as the narrow gate:
   `git diff --no-index <master> <copy>` (or `git hash-object` per file);
   never eyeball bytes. Compute the five portability lints (the lint list in
   `references/report-spec.md`, including the lint BOM-skip rule and the
   whole-directory BOM scan) on each master. Note SKILL.md-less
   subdirectories of either skills root as a free-form line in "Evidence and
   notes" (they are not units).

7. **AGENTS.md check.** Parse the root `AGENTS.md` blocks per the marker
   grammar; render each source unit per the rendering pipeline in
   `references/source-tree-spec.md`, writing scratch renders ONLY to the
   session scratchpad outside the project; compare per the agents-md
   decision table (cases A1–A7) with normalization N applied, via
   `git diff --no-index` on normalized scratch copies.

8. **Hooks check.** Parse `.claude/rules/hooks.md` entries per the hook
   intent document format in `references/source-tree-spec.md`, emitting one
   `intent-doc-anomaly` observation per schema violation; parse both JSON
   surfaces; derive the bridge-owned groups and locate marked handlers;
   apply the hooks decision table (the H-cases) per entry per declared host,
   plus the marked-orphan case; collect `undeclared-hooks-key` observations
   for groups neither owned nor marked.

9. **Cheap guards (same pass).** Root `AGENTS.override.md` →
   `surface-shadowed` (report it prominently: the whole rules projection
   surface is inactive); root `AGENTS.md` byte size vs 32768 →
   `agents-md-size` at ≥ 28672; import scan of the entry file for an import
   token whose path component ends with `AGENTS.md` →
   `self-referential-import` (whole file, including code fences);
   `CLAUDE.md` and `.claude/CLAUDE.md` both present → `dual-project-entry`;
   tracked nested `CLAUDE.md` / `AGENTS.md` / `.claude/skills/` /
   `.agents/skills/` → nested-* observations with the positional-precedence
   hedge; `.claude/commands/*.md` → `legacy-commands-dir`;
   `.codex/skills/` → `legacy-codex-skills`; tracked `settings.local.json`
   hooks → `local-hooks-present` (untracked → local notes only);
   `.codex/config.toml` present and readable → `config-toml-budget` when it
   sets `project_doc_max_bytes` (0 = surface disabled). `.codex/config.toml`
   is NOT otherwise a check surface at M1.

10. **Assemble the report** per the report document format in
    `references/report-spec.md`: compute the no-source-unit rows, sort rows
    and observations, attach the tier and annotations columns, include the
    Codex activation hedge sentence whenever a host=codex row exists, and
    cite intent records and (repo mode only) `git log` / `git blame`
    pointers in "Evidence and notes".

11. **Expectation comparison (fixture mode and dogfood).** Apply steps 2–7
    of the deterministic comparison rule in `references/report-spec.md`
    against the expectation file. Emit PASS or FAIL plus, on FAIL, the exact
    differing rows/lines.

12. **Boundary restatement.** Close by repeating the hard read-only rule
    verbatim: the sentinel MUST NOT create, modify, or delete any file under
    the scanned project; scratch files for rendering and diff mechanics go
    OUTSIDE the project (the session scratchpad). The report is session
    output. The product writes nothing to disk.

Your role is confined to executing this checklist and wording the report's
free-form sections; you never classify in-sync versus drift — every state in
the Findings table comes from the decision tables.
