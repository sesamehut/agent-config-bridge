---
name: bridge-sync
description: Plans, selects, confirms, and reconciles versioned Bridge-managed project skills, Claude entry instructions, rule shards, root AGENTS.md blocks, hook intents, and both native hook carriers using Git-proven unit baselines, deterministic rendering, per-closure authorization, and explicit strict or guarded write protocols. Use to onboard an empty, Claude-native, or Codex-native project; migrate, project, adopt, repair, delete, rename, or inspect proposed Bridge writes.
allowed-tools: Read
---

# Bridge sync

Reconcile project skills, entry/rule units, and hook units without overwriting
unknown content. Serialize the complete closure selection and authorization
first, then execute and verify only selected, confirmed dependency closures.
Hooks committed to a repository run for everyone who clones it: Bridge
classification is review metadata, not a sandbox.

## Runtime

- Run only in a Git worktree with Git on `PATH` and Python 3.9+.
- Resolve this skill, its references, the sibling `bridge-sentinel` skill, and
  `../../templates/covenant/` from this `SKILL.md`.
- The dated host fact base is `../../knowledge/` relative to this `SKILL.md`;
  consult it when a host behavior is not settled by the references.
- Use the sibling read-only helper for deterministic tree inspection and byte
  comparison:

```text
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py self-test
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py inspect-tree <unit>
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py compare-trees <source> <projection>
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py git-manifest <repo-root> <repo-relative-unit> [--revision <commit>] [--include-untracked] [--require-executable <relative-path>]
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py compare-git-trees <repo-root> <repo-relative-source-unit> <repo-relative-projection-unit> [--revision <commit>] [--include-untracked] [--direction <observe|source-to-projection|projection-to-source>] [--require-executable <relative-path>]
```

For hook units use the closed-grammar hook helpers:

```text
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py inspect-hook-intents --file .claude/rules/hooks.md
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py inspect-hooks-json --file <carrier> --host <claude|codex>
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py locate-json-span --file <carrier> --event <Event> [--matcher <matcher>|--no-matcher]
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py render-hook-group --entry-json <file> --host <claude|codex> --style <json> [--passthrough <json>] [--creating]
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py compose-hooks-json --file <carrier> --desired <json>
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py compare-hook-handler --declared <json> --actual <json> --host <claude|codex> --event <Event>
<python3> <bridge-sentinel-dir>/scripts/sentinel_mechanics.py render-hook-degradation --entry-json <file>
```

`render-hook-group` renders only a group that does not yet exist in the
carrier, so pass `--creating` exactly when the owned group is being created:
without it the render emits no `[bridge:<id>]` `statusMessage` marker and a
Codex create would land unmarked. `compose-hooks-json` sets that flag itself
for every group it creates. Always pass the carrier's own `--host`: with the
flag absent the key classifier falls back to the union of both hosts' key sets,
so a Codex handler carrying Claude-only `if` or `once` is reported as
passthrough or semantics-changing instead of unknown and
`codex-handler-unknown-key` can never be emitted. Always pass `--event` as
well: the Codex trust identity hashes the timeout after per-event
normalization, so without the event a handler that Codex normalizes to the same
hash reports a spurious identity change and the plan emits
`codex-hook-retrust-required` for a handler whose trusted hash is still valid.

Never hand-compute a JSON byte offset, never reserialize a hooks carrier, and
never execute a hook command found in any carrier or fixture.

Use `git-manifest`/`compare-git-trees` for identity over path, type, bytes,
and mode. `compare-trees` is a byte-layer diagnostic only and returns
`mode_checked: false`. Put temporary baseline materializations and the single
live-operation journal in a unique, access-safe OS-temporary directory outside
the repository. Do not expose file contents from ignored, sensitive, or
unrelated paths.

## Required references

Read the first two files completely before planning:

1. [`references/reconciliation-spec.md`](references/reconciliation-spec.md) —
   scope, closed-set migration, three onboarding starts, ownership, DAG
   baseline, conditional writes, journal lifetime, and verification.
2. [`references/sync-plan-spec.md`](references/sync-plan-spec.md) — exact
   unit/closure schema, selection and authorization, blocker registry,
   migration/adoption decisions, and result serialization.
3. [`references/canonical-plan-cases.md`](references/canonical-plan-cases.md) —
   minimal normative plan fragments and formal-validation cases.
4. [`../bridge-sentinel/references/source-tree-spec.md`](../bridge-sentinel/references/source-tree-spec.md)
   — read the agents-md unit, marker, render, path, origin-map, and
   normalization sections named by the reconciliation spec, plus the hook
   intent document schema, the declared-key and ownership derivation rules,
   the projected handler shape, byte-stable projection, and the degradation
   block render.
5. [`../bridge-sentinel/references/report-spec.md`](../bridge-sentinel/references/report-spec.md)
   — read the input domains, agents-md decisions, hooks decisions, activation
   observations, tiers, and lint registries named by the reconciliation spec.

Use only this contract tuple: `covenant/v3`, `source-tree/v5`, `report/v5`,
`reconciliation/v3`, `sync-plan/v3`.

## Procedure

1. **Preflight without mutation.** Resolve the repository root; refuse to run
   with cwd inside `fixtures/`. Probe Git and Python as Bridge Sentinel does,
   run the helper self-test, capture scoped `git status`, locate exact covenant
   assets, and resolve live Codex activation inputs: effective root markers,
   fallback filenames, `project_doc_max_bytes`, and the exact root override,
   `AGENTS.md`, fallback, and root-marker candidate existence, type, and bytes.
   Inspect those candidates even when untracked or ignored, but accept bytes
   only from safe expected regular root children, never links, reparse points,
   special files, or escapes. Keep live activation evidence disjoint from repo
   ownership bytes; ignored or untracked activation bytes never prove
   ownership or a baseline. Use a documented default only after proving its
   configuration key absent. Otherwise emit `codex-activation-unresolved` or
   `codex-root-unresolved`. Never stage, commit, stash, reset, restore, change
   ignore rules, or edit host configuration.
2. **Validate or migrate the covenant.** Apply gates in order:
   safety/trackability, pair coherence, tuple version, then reachable history.
   Interpret bytes exact for either archived pair in the closed set
   {`covenant/v1`, `covenant/v2`} only as migration evidence; each archived
   version is a single hop to the current tuple, with no chaining. For
   migration,
   derive the complete reachable archived-tuple owned set from
   ancestry-maximal managed
   candidates, serialize every full candidate oid in the independent
   Migration candidates table plus one Migration decisions row per unit, and
   require
   every member to be `carry-forward`, confirmed `repair-and-carry`, or
   confirmed `release`. Keep the covenant and closed legacy set in
   `closure/migration`. After preparing current-tuple bytes,
   require one reachable user commit that records the complete transition;
   until then emit `migration-transition-uncommitted`, claim no current
   ownership, block ordinary Bridge writes, and keep
   `migration-transition-required` on the covenant and carried unit rows.
   A released post-write row has Units baseline `-` and no transition
   annotation. If any legacy candidate set is ambiguous, select and block the
   complete migration closure with Units baseline `-`; give only the
   ambiguous row `decision-required` and keep unique candidate oids in the
   migration evidence tables. The legacy-owned set holds only `entry`,
   `rules/<id>`, and `skills/<name>`: a `covenant/v2`-to-`covenant/v3`
   migration never carries a hooks unit, because `reconciliation/v2` forbade
   every hook write, so a `hooks/*` unit claiming an archived-era baseline is
   `blocked` / `resolve-blocker` and hook units arrive afterwards through
   ordinary `no-baseline` / `create` reconciliation.
   Never dual-read an archived tuple or treat covenant byte replacement alone
   as an ownership transition.
3. **Select the onboarding start.** For an empty start, propose minimal source
   units plus the current covenant. For a Claude start, use the one safe entry
   and safe rule shards as source candidates while leaving existing
   `AGENTS.md` bytes manual. For a Codex start, segment every non-whitespace
   unmanaged `AGENTS.md` byte into exact contiguous spans; list each span in
   the required Adoption decisions table and obtain a `shared-entry`,
   `shared-rule`, `manual`, or explicit destructive `discard` decision. Never
   infer whole-file annexation or use Claude `/init` as an import mechanism.
   Before a shared destination is confirmed, serialize
   `onboarding/agents-md` with only `decision-required`; no source intent
   target exists yet. Do not add that unit to an empty/create capability
   blocker without explicit segmentation decisions.
4. **Snapshot every unit and protected byte.** Enumerate skills, the single
   supported entry, safe rule shards, managed blocks, tracked deletions,
   relevant untracked files, ignored paths, unknown occupancy, and unrelated
   dirty changes. Emit `untracked-files-included` for every relevant
   non-ignored untracked path, including an entry or rule source. For skills,
   generate current and historical
   `git-tree-manifest/v1` evidence. For entry/rules, retain raw source bytes,
   validated control comments and ordered `paths`, deterministic render plus
   origin/protected-span map, exact marker spans, and all manual-zone bytes.
   For hooks, snapshot `.claude/rules/hooks.md` with `inspect-hook-intents`
   and both carriers with `inspect-hooks-json`: capture each valid entry's
   byte span, normalized machine-field model and five prose bullets, the
   file-level `bridge:hooks-shared-execution` acknowledgement or its absence,
   every scanner anomaly, including the `yaml-block-count` record with no
   entry id that a stray fenced `yaml` block in the preamble produces and that
   the plan serializes as an `intent-doc-anomaly` warning on
   `.claude/rules/hooks.md` with detail `(line <n>)`,
   per host the owned `(event, effective-matcher)` group span with its
   normalized handler model or proven absence, the passthrough,
   semantics-changing and unknown keys, both complete carrier preimages with
   their parse, duplicate-key and closed-shape results and inferred style,
   and the shallow `.codex/config.toml` inline-hooks scan. Record every
   unowned group, marked orphan and foreign handler as unmanaged occupancy
   without claiming ownership. Read `.claude/settings.local.json` only for
   the informational `local-hooks-present` observation. Resolve Codex project
   trust and the effective hooks feature flag as live activation inputs that
   never enter a baseline.
5. **Apply the closed blocker registry.** Map every write blocker to
   `sync-plan/v3`; never invent a prose-only gate. Block on
   `authorization-incomplete`, `closure-dependency-unsatisfied`,
   `covenant-anchor-anomaly`, `codex-activation-unresolved`,
   `codex-root-unresolved`, `surface-shadowed`, `fallback-shadow`,
   `agents-md-budget-disabled`, `agents-md-budget-exceeded`,
   `dual-project-entry`, `active-shared-import`, `invalid-rule-paths`,
   `legacy-managed-mode`, `entry-rule-source-anomaly`, `marker-anomaly`,
   `ambiguous-baseline`, `migration-closure-incomplete`,
   `migration-transition-uncommitted`, `unsafe-tree-entry`,
   `ignored-required-input`, `skill-loadability-blocked`,
   `sensitive-or-generated-blocked`, `mode-limited`, `intent-doc-anomaly`,
   `hooks-carrier-unusable`, `codex-inline-hooks-conflict`,
   `hook-opt-in-required`, `hook-acknowledgement-missing`, or
   `conditional-write-unavailable` / `guarded-patch-unavailable` exactly as
   their registry rows specify. The `write capability`, `hook carrier`, and
   `hook opt-in` gates are the only gates scoped to the matching closure and
   its dependents; `hook source` and every other gate stay project-wide. Keep
   a scoped-blocked closure `selected` with authorization `not-applicable`
   and outcome `blocked`, never `not-selected`, and emit
   `hook-projection-asymmetric` on the blocked carrier when its sibling
   proceeds. For an entry whose `class` is `gate` the entry is
   all-or-nothing: keep the blocked carrier closure `selected` /
   `not-applicable` / `blocked` and force the sibling carrier closure to
   `not-selected` with zero writes.
   Represent pending onboarding/authority targeting as `decision-required`
   with a not-selected decision closure and outcome `not-selected`. Represent
   `both-changed` as a selected, `required`, `deferred` conflict row with
   `decision-required`. Represent an exact semantic-review source candidate
   in its selected physical closure as `required` / `planned` with
   `intent-required; semantic-review-required`.
   A `resolve-blocker` row always uses `user-decision` direction.
   Require acknowledgement for `agents-md-near-budget`,
   `claude-hooks-shared-execution`, `codex-hook-retrust-required`,
   `codex-trust-reindex`, `guarded-patch-non-cas`,
   `hook-projection-asymmetric`, `manual-zone-guarded`,
   `manual-zone-preserved`, `matcher-grammar-divergent`,
   `platform-branch-divergence`, and `strict-compensation-unavailable`; they
   are not forward-apply blockers. Emit `matcher-grammar-divergent` only under
   its closed predicate: a shared `matcher` inside the Claude list class that
   contains `|` or `,`, both targets on a host-executed JSON surface, and no
   per-host `matcher` override; a bare literal such as `Bash` never qualifies.
   Do not expand imports or degrade an invalid scoped rule to unscoped
   content.
6. **Prove ownership and a DAG baseline per unit.** Evaluate only commits
   reachable from `HEAD`, require current-contract ownership evidence, and
   select the unique ancestry-maximal candidate. Compare skills against one
   complete-tree baseline. Compare entry/rules against `(raw B_s, rendered
   B_p)` and separately test current `P == render(S)`. Block incomparable
   maximal candidates. Never select by date, current line-diff shape, or an
   intent record alone.
7. **Classify unit decisions and compose closures.** Apply the exact
   reconciliation tables. When payload carriers have converged but required
   semantic source intent is absent, use `intent-missing` / `update` with
   `intent-required`; never label a planned source write `unchanged`.
   Reverse-adopt only through the render origin map: strip an exact `pv2`
   preamble, preserve frontmatter, control comments, and Claude-only spans,
   and validate any recovered `paths`. For an ambiguous or boundary-crossing
   hunk, free-form preamble, or host-specific wording, emit
   `semantic-review-required` and show proposed source bytes plus their exact
   rerender before confirmation. Never enable a free semantic managed mode.
   Pair renames only from explicit intent or reliable Git path history.
   A rename destination uses baseline `-` / state `no-baseline`; its old
   source uses a proven baseline / state `source-only`.
   Apply the hooks reconciliation table per host unit. Take
   `declared-unsynced` / `unchanged` whenever the target declares
   `surface: none` and that carrier is unoccupied for the entry, but let an
   occupied one fall through to `no-baseline` / `annex-or-keep`;
   keep the computed state but take `opt-in-or-skip`
   whenever a `gate` or `side-effect` entry with `enabled: true` has no
   covering `enabled-by` record. Let semantic handler equality decide the
   state and byte equality decide only whether a write row exists; a
   converged group that differs only in formatting stays `unchanged` and
   emits `hook-format-preserved`. Reverse-adopt only `command`,
   `commandWindows` on Codex, `timeout`, and the group `matcher`; never adopt
   `statusMessage`, whose text after the `[bridge:<id>]` prefix has no source
   field and is carried forward verbatim instead. Map to the shared
   scalar only when the other host is unchanged and equal, and show that
   host's rerendered bytes first, otherwise require
   `targets.<host>.<field>` with a stated `override-reason` and an explicit
   confirmation. Never adopt `event`. Treat a passthrough-key change as no
   change. Route a `type` change, a foreign handler, a semantics-changing
   key, an `H-MULTI` group, or a mode-ambiguous matcher change to
   `semantic-review-required`, and every unresolved handler to the Hook
   adoption decisions table.
8. **Serialize closures and authorization.** Emit exact `sync-plan/v3` Units,
   Closures, Capability profiles, Write capabilities, Hook tiers, Migration
   decisions, Migration candidates, Adoption decisions, and Hook adoption
   decisions tables. Bind every unit row
   to one stable closure id and repeat its `selection` and `authorization`.
   List every selected physical operation in execution order with its forward
   protocol/binding and inverse protocol/binding. For migration, list every
   ancestry-maximal legacy candidate oid;
   a multiple-candidate unit uses no scalar legacy baseline and remains
   ambiguous. Use `closure/migration` with precedence,
   `closure/agents-md`, `closure/skill/<name>`,
   `closure/skill-rename/<old>--to--<new>`, `closure/hooks/source`,
   `closure/hooks/claude`, `closure/hooks/codex`,
   `closure/decision/hooks/<entry-id>`, or `closure/decision/<unit>`. Put a
   degraded Codex hook block in the existing `closure/agents-md` and keep an
   entry's two zero-write host rows in one
   `closure/decision/hooks/<entry-id>`. Make `closure/hooks/claude`,
   `closure/hooks/codex`, and `closure/agents-md` depend on
   `closure/hooks/source` when it is selected, and never let two carrier
   closures depend on each other. Serialize a `hooks/<id>/source` row only
   when `.claude/rules/hooks.md` is written by this plan or the source unit
   is itself blocked. Give every hook unit exactly one Hook tiers row whose
   `tier` equals its Units `tier`, and keep header authorization derived from
   selected mutating closures, so a zero-write hook decision closure yields
   `not-applicable` with no `authorization-incomplete` line.
   Represent a partial batch only by serialized
   `not-selected` closures and unit rows. Sort closure members/dependencies,
   select dependencies together, and serialize selection, authorization, and
   outcome on every closure. Give a not-selected closure authorization
   `not-applicable` and outcome `not-selected`; give a selected zero-write
   closure authorization `not-applicable`. Keep a selected mutating closure
   `required` until that exact serialized closure is confirmed, then mark it
   `confirmed`; a scoped-blocked closure instead carries `not-applicable` with
   outcome `blocked`. Derive header authorization from the selected mutating
   closures only: `required` when one of them carries `required`, otherwise
   `confirmed` when at least one exists, otherwise `not-applicable`. A
   scoped-blocked closure still counts as a selected mutating closure, so a
   plan that writes nothing because its only mutating closure is
   scoped-blocked still derives `confirmed`. Re-scan when any relevant
   precondition changes.
   Serialize only affected or explicitly request-scoped units; repository-wide
   covenant preflight does not add an unchanged covenant row. Allocate
   capability bindings contiguously by numeric suffix in first-use order,
   scanning each numeric write step's forward binding before its inverse.
   Before confirmation or mutation, pass the exact document through the
   formal validator defined by `sync-plan/v3`; expectation comparison is not
   a substitute. In a fixture replay, if that public validator rejects a
   draft, run the public `explain-plan` companion with the same replay input,
   worktree, lease, plan bytes, and operation lifecycle. Correct only from its
   closed `sync-plan-diagnostic/v1` failures and diagnostics. Never inspect an
   expectation, matrix result, post-state alias, or golden/oracle plan to
   repair the draft.
9. **Resolve a versioned write protocol.** Build
   `capability-profile/v1`, binding the active host/version, tool surface,
   platform, and filesystem assumptions; default every capability to
   unavailable. Use `strict-replace/v1`, `strict-create/v1`, or
   `strict-delete/v1` only when one operation binds the complete expected
   value to mutation. An existing safe, byte-round-trippable UTF-8 text file
   may instead use `guarded-patch/v1`: derive one non-empty unique exact region
   covering every changed Unicode code point, extending only at strict UTF-8
   code-point boundaries; require complete pre/post images and old/new regions
   to decode exactly, then require complete-file preflight, one
   exact-literal non-fuzzy replacement, and complete-file postverification.
   Guarded patch is not CAS and never applies to create, delete, rename, mode,
   or inverse operations. For a hooks carrier, derive the postimage with
   `json-owned-span/v1`: require a strict JSON object parse with no duplicate
   key anywhere and no node outside the closed hooks shape, locate the owned
   `(event, effective-matcher)` spans and insertion points with
   `locate-json-span`, render new groups with `render-hook-group`, compose
   with `compose-hooks-json`, and reject any postimage produced by
   reserializing the parsed document. An absent carrier is a `create` that
   accepts only `strict-create/v1`: keep the row `unavailable` / `blocked`,
   emit `conditional-write-unavailable` and `hook-carrier-absent`, add
   `hook-projection-asymmetric` only when the sibling carrier still proceeds
   (never for a `class: gate` entry), and print the exact bytes the user can
   paste instead of writing the file unconditionally. Serialize `unavailable`
   and block with the matching capability token rather than silently
   degrading.
   Admit only the
   attestation sources defined by reconciliation/v3; generic host file I/O
   and fixture-only profiles do not imply a strict live capability. A
   fixture-only root-child fault mutation has a separate platform gate:
   retained POSIX root/leaf handles may prove the exact read but do not bind
   the current pathname to that leaf in the same mutation. Without a
   mutation-bound current name-to-leaf attestation, keep that mutation
   declarative-only and make `apply-fault` reject before the mutation path.
   Resolve the Windows adapter independently from its own handle/name evidence;
   do not inherit either a downgrade or an upgrade from the POSIX result.
10. **Bind and execute one live operation.** Before any selected closure
    executes, allocate one opaque `operation-id` and one fresh, access-safe
    no-follow OS-temporary lease directory outside the repository; create its
    journal exclusively and retain the exact path in active memory. Bind the
    resolved repo, starting `HEAD` or `unborn`, SHA-256 of the independent
    exact confirmed `phase: pre-write` plan bytes, selected
    closure ids/dependencies/selection/authorization, lifecycle `prepared`,
    `executing`, `compensating`, `verified`, `partial`, or `closed`, and every
    path operation's step, closure id, kind, protocol, inverse protocol,
    capability binding, exact pre-value, intended post-value, and observed
    applied value; guarded steps also bind region offset and exact old/new
    region. For a fixture journal, obtain the prepared validation context and
    formal result together from one attestation over the authenticated public
    replay envelope and one alternate `HEAD` index. Never supply
    `temporal_context` or `live_untracked` as caller claims. Never discover a
    journal by
    scanning temporary directories or accept one from another repo, `HEAD`,
    plan, operation, process, or session. Compose one exact desired
    `AGENTS.md` image, preserve every manual/unselected/conflict span in its
    complete pre/post images, write canonical source paths first, and apply
    the carrier last with its serialized strict or guarded protocol. When a
    plan writes hook units, use the step order `.claude/rules/hooks.md`, then
    `AGENTS.md`, then `.claude/settings.json`, then `.codex/hooks.json`.
    Compose each hooks-carrier desired image from the exact preimage with only
    the owned spans edited and the located insertion points filled; append
    new groups and never move, sort, or reorder an existing element, owned or
    unowned. Remove a deleted element with exactly one adjacent separator,
    remove an emptied event member whole, and leave `"hooks": {}` when the
    object empties. Never write the Codex top-level `description`, and add
    the bare `[bridge:<id>]` `statusMessage` marker only to a handler that
    carries none: on Claude whenever it composes the handler, and on Codex
    only at creation. Re-read
    the complete path at the final preflight immediately before every host
    call and again after it. If that final full-file preflight differs from
    the confirmed preimage before any selected mutation, make zero Bridge
    writes and report the affected closure exactly `failed`. For a guarded call,
    classify exact postimage as verified, exact preimage as failed only when
    no prior mutation exists, and every third value as `partial`; stop on the
    first rejection or mismatch.
11. **Verify and report.** Re-read every affected path; compare skill
    manifests; rerender every selected entry/rule; verify the covenant,
    complete `AGENTS.md` image, and each protected span; re-parse both hooks
    carriers with `inspect-hooks-json` and verify that every unowned byte is
    byte-identical to the preimage, that every owned group parses equal to
    its desired model, and that each file still parses with no duplicate key;
    then run scoped `git status`, scoped `git diff`, and `git diff --check`.
    Emit the `sync-plan/v3` result with the phase selected by its
    operation-lifecycle rule. Treat live activation as unknown only at the
    timing defined by the plan spec, and require a fresh Codex run/session to
    test a carrier that was or may have been written. Attach
    `awaiting-host-trust` only to a `hooks/<id>/codex` row whose carrier was
    or may have been written, and state that Codex silently skips a new or
    modified hook until the user reviews it. Never pass ignored files to a
    raw tree comparison.
12. **Compensate only with pre-attested strict inverses.** Resolve every
    inverse protocol before the first mutation. If any is unavailable, emit
    `strict-compensation-unavailable` and do not attempt guarded
    compensation. Only while the bound journal remains open may fully strict
    inverse steps run in reverse order. Verify every call. Report
    `compensated` only after the full pre-write closure verifies; otherwise
    report `partial` and mark later/dependent selected closures
    `not-attempted`. After `applied`, mark the journal `verified` then
    `closed`; it grants no future authority. Treat any later reverse request
    as a new plan reconstructed from current bytes plus reachable Git. User
    confirmation cannot substitute arbitrary evidence for missing ownership,
    baseline, or prior bytes. Never search for an old journal; if Git cannot
    reconstruct exact prior bytes, reverse is unavailable and annexation or a
    destructive decision must be planned separately under its normal gates.
    Cleanup validates and removes only the retained closed journal and its
    exact empty lease directory; never enumerate sibling leases.

## Hard boundaries

- Do not infer direction from current two-tree diff shape.
- Do not auto-merge conflicts.
- Do not describe `guarded-patch/v1`, preflight, postverification, atomic
  rename, or advisory locking as CAS.
- Do not use guarded patch for create, delete, rename, mode change, or
  compensation.
- Do not promise locking, crash durability, or a cross-file transaction.
- Do not invent a semantic projection escape mode or silently rewrite
  host-specific prose.
- Do not expand or project active Claude imports.
- Do not copy ignored, secret, generated, linked, or path-escaping content.
- Do not overwrite unmanaged blocks, manual-zone bytes, or another target
  without Git-proven ownership or an explicit annex/replacement decision.
- Do not edit root-discovery configuration, fallback files,
  `AGENTS.override.md`, inline `[hooks]` in `.codex/config.toml`, or
  `.claude/settings.local.json`.
- Do not write any byte of a hooks carrier outside an owned group span, and
  do not reserialize a carrier, reorder its arrays, or repair its formatting.
- Do not project a `gate` or `side-effect` hook without a dated `enabled-by`
  record already in the source, and do not describe that record, the
  file-level acknowledgement, or the `class` field as an enforcement
  boundary: Bridge classification is review metadata, not a sandbox.
- Do not delete, rewrite, or normalize an unowned handler, a foreign handler
  type, a passthrough key, or the Codex top-level `description`.
- Do not execute a hook command from any carrier, fixture, or plan.
- Do not use a legacy contract as a supported runtime path.
- Do not reuse a closed journal or search temporary storage for recovery.
- Do not describe a retained POSIX leaf handle or link count as proof that a
  swapped current pathname still names that leaf at mutation time.
- Do not claim success for `keep`, blocked, conflict, failed, partial, or
  not-attempted units, or for not-selected closures.
