---
name: bridge-sync
description: Plans, confirms, and reconciles versioned Bridge onboarding plus project skill trees between .claude/skills and .agents/skills using Git-proven managed baselines. Use to onboard, project, adopt, repair, delete, rename, or inspect a proposed write to managed project skills.
---

# Bridge sync

Reconcile M2 project skill units without overwriting unknown content. Produce
the complete plan first, obtain confirmation, then write only confirmed
dependency closures and verify them.

## Runtime

- Requires a Git worktree, Git on `PATH`, and Python 3.9+.
- Resolve this skill, its references, the sibling `bridge-sentinel` skill, and
  `../../templates/covenant/` from this `SKILL.md`.
- Use the sibling read-only helper for deterministic tree inspection and byte
  comparison:

```text
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py self-test
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py inspect-tree <unit>
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py compare-trees <source> <projection>
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py git-manifest <repo-root> <repo-relative-unit> [--revision <commit>] [--include-untracked] [--require-executable <relative-path>]
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py compare-git-trees <repo-root> <repo-relative-source-unit> <repo-relative-projection-unit> [--revision <commit>] [--include-untracked] [--direction <observe|source-to-projection|projection-to-source>] [--require-executable <relative-path>]
```

Use `git-manifest`/`compare-git-trees` for identity over path, type, bytes,
and mode. `compare-trees` is a byte-layer diagnostic only and returns
`mode_checked: false`. Put temporary baseline materializations and
operation-local transaction journals in a unique, access-safe OS-temporary
directory outside the repository. Do not expose file contents from ignored,
sensitive, or unrelated paths.

## Required references

Read both files completely before planning:

1. [`references/reconciliation-spec.md`](references/reconciliation-spec.md) —
   scope, covenant, snapshots, ownership, DAG baseline, decision tables,
   destructive actions, batching, and verification.
2. [`references/sync-plan-spec.md`](references/sync-plan-spec.md) — exact
   plan/result registry and serialization.

Also read the sibling Sentinel sections named by the reconciliation spec.
Contract tuple: `covenant/v1`, `source-tree/v3`, `report/v3`,
`reconciliation/v1`, `sync-plan/v1`.

## Procedure

1. **Preflight without mutation.** Resolve the repository root; refuse to run
   with cwd inside `fixtures/`. Probe Git and Python as Bridge Sentinel does,
   run the helper self-test, capture scoped `git status`, and locate the exact
   covenant assets. Never stage, commit, stash, reset, restore, or change
   ignore rules.
2. **Validate onboarding.** Inspect both tracked covenant halves and their
   versions, then apply the covenant state/action table in gate order:
   safety/trackability, pair coherence, tuple version, history. An untracked
   old tuple is blocked for repair/decision before migration. Distinguish
   current repair, historical restore, tuple migration, and offboarding;
   every action uses the whole pair plus the preserved `AGENTS.md` manual
   zone. Bootstrap is M2's sole rules/AGENTS write; never install hook intents
   or claim a newly created untracked half is already onboarded.
3. **Snapshot every relevant unit.** Enumerate immediate source and target
   names, tracked deletions, non-ignored untracked files, ignored paths, and
   non-empty directories without `SKILL.md`. Generate current
   `git-tree-manifest/v1` evidence with `--include-untracked`; generate each
   historical candidate from its revision. Treat ordinary untracked files as
   prospective `100644` when no reliable POSIX mode probe exists. Preserve
   unrelated dirty changes.
4. **Apply safety gates.** Check lexical and resolved containment, Git modes,
   regular-file-only trees, case collisions, identity/YAML/loadability, and
   sensitive/generated risk. Include tracked deletions with current paths in
   the unit-wide case-fold domain, deduplicating only exact same-path
   occurrences. Copy format-valid host extensions unchanged; report
   validator and behavior axes separately. Treat explicit or
   direction-aware `mode-limited` as a blocker, never as byte equality;
   ordinary prospective `100644` is not itself a blocker.
5. **Prove ownership and baseline.** For each unit, evaluate only commits
   reachable from `HEAD`, require current-contract ownership evidence and
   identical complete Git trees, then select the unique ancestry-maximal
   candidate. Multiple incomparable maximal candidates are blocked. Never
   select by date, line-diff shape, or intent records alone.
6. **Classify and plan.** Apply the reconciliation table. Pair rename only
   from explicit intent or reliable Git path history and keep old/new atomic.
   Append intent only for onboarding, annexation, adoption, rename, or a
   semantic change. Aggregate per-unit decisions into physical dependency
   closures. Keep observation/pending/keep comparisons direction `observe`.
   For a proposed write, rerun the mechanical comparison with its exact
   direction and any explicit executable paths; block only a required target
   mode the host cannot realize.
7. **Present the full pre-write plan.** Emit exact `sync-plan/v1`, including
   every path, baseline, untracked/ignored file, unrelated dirty warning,
   blocker, annotation, and decision. Ask for confirmation before all writes;
   conflicts, annexation/replacement, migration, offboarding, and destructive
   choices require an explicit resolution. Re-scan if relevant bytes change.
8. **Execute confirmed closures only.** Before each closure, journal exact
   path existence, type, bytes, and mode outside the repository. Compare and
   swap immediately before every write, record the exact value written, and
   preserve `AGENTS.md` manual-zone bytes. Unknown occupancy and every
   conflict unit receive zero writes. Independent closures may proceed only
   when the confirmation explicitly authorizes that partial batch.
9. **Verify and report.** Re-read, mechanically compare bytes and modes,
   validate the covenant/manual-zone snapshot, run scoped `git status`, scoped
   `git diff`, and `git diff --check`, then emit the post-write result. Warn
   that Codex live activation is unknown and a fresh session or restart may be
   required. Never pass a raw directory containing excluded ignored files to
   `compare-trees`; compare the allowed Git manifests instead.
10. **Compensate failures safely.** The confirmed plan authorizes automatic
    reverse compensation within a closure. Before each restoration, require
    current path/type/bytes/mode to equal the exact value written by this run.
    Report `compensated` only after the full pre-write closure verifies;
    report `partial` and stop if compensation cannot safely complete. Mark
    skipped later/dependent closures `not-attempted`. A rollback requested
    after an applied result is separate, requires a new plan and confirmation,
    and may restore only this run's journaled preconditions.

## Hard boundaries

- Do not infer direction from current two-tree diff shape.
- Do not auto-merge conflicts.
- Do not copy ignored, secret, generated, linked, or path-escaping content.
- Do not overwrite or delete a target without Git-proven ownership or an
  explicit annex/replacement decision.
- Do not install M3 rule projection or M4 hooks.
- Do not claim success for `keep`, blocked, conflict, failed, partial, or
  not-attempted units.
