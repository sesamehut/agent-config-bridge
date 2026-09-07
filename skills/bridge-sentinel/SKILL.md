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
<python3> <skill-dir>/scripts/sentinel_mechanics.py inspect-agents-md <AGENTS.md> [--entry-source <path>] [--owned-id <id> ...]
<python3> <skill-dir>/scripts/sentinel_mechanics.py render-agents-unit <source> --kind <entry|rule|covenant> [--paths-json <ordered-json-string-list>]
<python3> <skill-dir>/scripts/sentinel_mechanics.py inspect-active-imports <source>
<python3> <skill-dir>/scripts/sentinel_mechanics.py parse-preamble <rendered-body>
<python3> <skill-dir>/scripts/sentinel_mechanics.py validate-render-paths <ordered-json-string-list>
<python3> <skill-dir>/scripts/sentinel_mechanics.py check-agents-budget <AGENTS.md> --budget <bytes>
<python3> <skill-dir>/scripts/sentinel_mechanics.py inspect-tree <root>
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-trees <master> <copy>
<python3> <skill-dir>/scripts/sentinel_mechanics.py git-manifest <repo-root> <repo-relative-unit> [--revision <commit>] [--include-untracked] [--require-executable <relative-path>]
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-git-trees <repo-root> <repo-relative-source-unit> <repo-relative-projection-unit> [--revision <commit>] [--include-untracked] [--direction <observe|source-to-projection|projection-to-source>] [--require-executable <relative-path>]
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-files <source> <projection> [--normalize-n]
<python3> <skill-dir>/scripts/sentinel_mechanics.py validate-activation-profile <profile.json>
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-expectation <produced-report> <expected-report>
<python3> <skill-dir>/scripts/sentinel_mechanics.py inspect-hook-intents --file <.claude/rules/hooks.md>
<python3> <skill-dir>/scripts/sentinel_mechanics.py inspect-hooks-json --file <hooks-carrier> --host <claude|codex>
<python3> <skill-dir>/scripts/sentinel_mechanics.py compare-hook-handler --declared <json> --actual <json> --host <claude|codex> --event <Event>
<python3> <skill-dir>/scripts/sentinel_mechanics.py render-hook-degradation --entry-json <file>
```

It reads supplied paths and writes JSON to stdout. `self-test` manages only its
own OS-temporary directory. Exit codes: `0` = equal/PASS, `1` =
different/FAIL, `2` = invalid input or execution error.
`git-manifest` and `compare-git-trees` implement Git-tree identity over path,
entry type, bytes, and mode. `compare-trees` is deliberately limited to
filesystem paths and bytes and returns `mode_checked: false`; never use it
alone to claim Git-tree equality. Sentinel always uses direction `observe`;
write directions and explicit executable requirements belong to bridge-sync.
`render-agents-unit` returns normalized rendered bytes as base64, an origin
map, protected spans, and blockers. Parse rule YAML with the agent and pass
only a fully validated ordered JSON string list to `--paths-json`.
`validate-render-paths` is a defensive lexical/schema check; it deliberately
does not parse general YAML or prove brace-expansion count/byte limits.
Validate those closed v5 rules before calling the renderer.
`validate-activation-profile` validates only the closed fixture-profile JSON
shape, now `activation-fixture/v2`. It does not resolve live Codex
configuration or inspect carriers.
`inspect-hook-intents` returns `hook-intent-scan/v1`: entry spans and ids,
bullet-label spans, the single `yaml` fence span per entry, the file-level
`bridge:hooks-shared-execution` span, byte-decidable violations including a
stray `yaml` block in the preamble before the first entry, and the
authenticated per-target triple. It is a closed-grammar byte scanner, never a
YAML parser; the agent parses the YAML and validates the complete v5 schema.
`inspect-hooks-json` returns `hooks-json-inspection/v1`: byte spans for `hooks`,
each event array, each group, each handler and each key/value member, the parsed
scalars, duplicate-key detection, the classified passthrough, semantics-changing
and unknown handler keys, and the inferred file style. It makes no ownership
judgement; ownership comes from the intent document alone. Always pass the
carrier's own `--host`: with the flag absent the key classifier falls back to the
union of both hosts' key sets, so a Codex handler carrying Claude-only `if` or
`once` is reported as passthrough or semantics-changing instead of unknown and
`codex-handler-unknown-key` can never be emitted.
`compare-hook-handler` applies the whitespace-strip, code-point,
integer-`timeout`, `type == command`, and matcher-absence rules and feeds the
H-case discriminator. Always pass `--event` as well: the Codex trust identity
hashes the timeout after per-event normalization, so without the event a handler
that Codex normalizes to the same hash reports a spurious identity change.
`render-hook-degradation` is a pure `hd1` template renderer that reads only the
supplied entry JSON and never touches the scanned project.
`locate-json-span`, `render-hook-group`, and `compose-hooks-json` are write-side
helpers; `bridge-sync` uses them to locate insertion points, render a new group,
and compose a byte-stable postimage. The sentinel never calls them.

## Reference map

Read each reference's Contents section, then load a complete section just
before applying it:

| Scan phase | Source-tree sections | Report sections |
|---|---|---|
| Scope and onboarding | Unit model; Onboarding anchor; Marker grammar | Input set; The states |
| Skills | Skill intent supporting file; Managed skill tree; Skill compatibility layers | Per-surface decision tables > Skills; Diff shape; Skill portability lint list |
| AGENTS.md | Marker grammar; Applicability preamble and rendering pipeline; Codex target eligibility; Manual-zone ownership; Normalization set N; Entry/rule control comments and paths; Active shared imports; Reverse-adoption origin map; Hook degradation block | Per-surface decision tables > Agents-md; Closed observation vocabulary; Fidelity tiers |
| Hooks | Hook intent document; Shared event registry; Declared keys and ownership derivation; Hook degradation block; Projected handler shape | Per-surface decision tables > Hooks; Closed observation vocabulary; Fidelity tiers |
| Output | — | Report document format; Expectation files and the deterministic comparison rule; Runtime hedges |

Versions: `references/source-tree-spec.md` = `source-tree/v5`;
`references/report-spec.md` = `report/v5`. Read the defining rule before
emitting any normative token.

## Procedure

1. **Preflight.** Run `git --version`. Probe `python3 --version`,
   `python --version`, then `py -3 --version`; use the first actual Python
   version ≥ 3.9 (a Windows Store alias does not qualify). Report a missing
   prerequisite with install guidance. Run `self-test` and stop on failure.
2. **Resolve inputs.** Keep repo ownership bytes and live activation inputs
   disjoint. Repo mode uses `git rev-parse --show-toplevel`. Fixture mode
   reads scan root, excludes, and activation profile from the expectation
   header and ignores outer-repository history. Build ownership bytes with
   scoped `git-manifest` snapshots, preserving path, type, bytes, HEAD/index
   mode evidence, and any reliable POSIX worktree mode change. Apply excludes
   before every ownership rule. Do not pass `--include-untracked` for managed
   equality; inspect only the exact untracked covenant paths for the specified
   onboarding safety exception.

   Resolve effective Codex root markers, fallback filenames, and document
   budget independently. Inspect the exact root override, root `AGENTS.md`,
   configured same-directory fallbacks, and marker candidates even when
   untracked or ignored. Read only safe regular exact-child carriers without
   symlink, reparse, special-file, or path-escape traversal. In fixture mode,
   use a validated pinned profile when named; `environment-dependent` keeps
   live and capability observations out of deterministic comparison. Never
   use activation bytes or values as ownership or baseline evidence.
3. **Establish scope.** Validate both versioned covenant halves against the
   exact templates under `../../templates/covenant/`, then evaluate onboarding.
   A partial, modified, malformed, untracked, or version-mismatched pair is
   blocked. Treat an exact pair from the closed archived set {`covenant/v1`,
   `covenant/v2`} as migration-only evidence, never as a readable runtime
   contract. Enumerate the entry unit, rule shards
   except `.claude/rules/hooks.md`, schema-valid hook entries, and skill
   masters. Apply the source-path grammar before emitting
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
5. **Check AGENTS.md.** Parse root `AGENTS.md` with `inspect-agents-md`; treat
   every byte outside proven managed blocks as protected manual data. A
   legacy `mode=` marker, duplicate id, malformed region, or source mismatch
   blocks the region map. Parse entry/rule control comments, strict `paths`
   YAML, Claude-only spans, and active imports. Validate the complete v5 path
   schema plus brace-expansion limits with the agent, then call
   `render-agents-unit`. Compare the rendered source and block body under N,
   using scratch files outside the project only. Evaluate A0, A-SURFACE,
   A-SOURCE, A-MARKER, then A1–A8; a block whose id begins `hooks/` derives the
   constant source `.claude/rules/hooks.md` and falls to A8, never A4. Emit
   exact live activation observations; use `check-agents-budget` with the
   resolved non-negative budget.
6. **Check hooks.** Run `inspect-hook-intents` for entry spans and ids, bullet
   labels, the one `yaml` fence per entry, and the file-level
   `bridge:hooks-shared-execution` comment; parse that YAML with the agent and
   validate the complete v5 schema, emitting one `intent-doc-anomaly` per
   violation and naming its closed reason token in Evidence and notes only.
   The scan itself reports a fenced `yaml` block that opens before the first
   `## hook:` heading as reason `yaml-block-count` with no entry id; serialize
   it as `intent-doc-anomaly` with `(line <n>)` for the opening fence and never
   re-derive it. Emit `matcher-grammar-divergent` only under its closed
   predicate: a shared `matcher` inside the Claude list class that contains
   `|` or `,`, both targets on a host-executed JSON surface, and no per-host
   `matcher` override. The scan's per-entry advisories already apply that
   predicate, and a bare literal such as `Bash` never qualifies.
   Run `inspect-hooks-json` on each present carrier for spans, parsed scalars,
   duplicate keys, and the classified passthrough, semantics-changing, and
   unknown handler keys; always pass `--host` and always pass the carrier's own
   host, because the key classification is host-specific and a missing flag
   silently widens it to both hosts. Derive ownership from valid entries alone
   using `(event, effective-matcher(host))`, locate marked handlers, then
   discriminate the H-cases with `compare-hook-handler`, passing the entry's
   `--event` so Codex timeout normalization runs, and running the prose-surface
   cases before H-NOFILE and H-FOREIGN-HANDLER before H-MISSING. For a
   `targets.codex.surface: agents-md` entry, compare
   `render-hook-degradation` against `N(body)` of the root `AGENTS.md` block
   `hooks/<id>`. Emit `undeclared-hooks-key` only for groups that are neither
   owned nor marked, in both regimes: a `surface: none` or prose-surface target
   owns no group, so the group its H-T4-PRESENT or H-DEGRADED-NATIVE-PRESENT
   candidate occupies is still reported unless a `[bridge:<id>]` marker claims
   it. Shallow-scan a tracked `.codex/config.toml` for an inline
   `[hooks` table header or a top-level `hooks =` pointer key without parsing
   TOML, and read `disableAllHooks` and a tracked
   `.claude/settings.local.json` for their observations only. `locate-json-span`,
   `render-hook-group`, and `compose-hooks-json` belong to `bridge-sync`; never
   call them here. Never execute a hook command and never start a host against
   the scanned tree. Evaluate the complete observation registry. Derive
   `agents-md-size`, budget-disabled, and budget-exceeded solely from the
   effective-budget rules.
7. **Assemble output.** Emit the exact report skeleton, sorted findings and
    observations with their registered provenance, tiers, annotations,
    no-source-unit rows, and every applicable runtime hedge, including the
    Claude hook hedge whenever a Claude hook row is present. Current diff
    shape may appear only as evidence. Never emit a write direction, adoption
    decision, or conflict conclusion; every drift action is `reconcile`. Cite
    intent records and, in repo mode only, relevant `git log` or `git blame`
    pointers in Evidence and notes.
8. **Compare expectations.** In fixture or dogfood mode, keep the produced
    report outside the project and run `compare-expectation`. Require the
    expectation's activation-profile header. Report PASS or FAIL and reproduce
    the helper's exact differing fields on failure.

## Hard boundary

Keep the scanned project unchanged. Temporary helper and comparison files stay
outside it. Return the report as session output and leave no persistent product
artifact. Never execute a hook command, never write a hooks carrier, and never
start Claude Code or Codex against the scanned tree: this skill is read-only,
and hook classification in an intent document is review metadata, not a
sandbox.
