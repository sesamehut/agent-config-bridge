---
paths:
  - "fixtures/**"
---
<!-- bridge:intent 2026-07-08 Fixture-authoring conventions introduced with the first M1 fixtures -->
<!-- bridge:intent 2026-09-07 M4 hook fence: inert fixture hook commands, activation-fixture/v2 profiles -->

# fixtures/ - Fixture authoring rules

Everything under `fixtures/` is an inert verification bed for the
Bridge skills. These are hard rules, binding on every change inside
`fixtures/`.

- **Real host-native names.** Fixtures keep real host-native file names
  (`CLAUDE.md`, `AGENTS.md`, `.claude/…`, `.agents/…`, `.codex/…`). Read-only
  sentinel projects are scanned where they sit and are never neutralized or
  replaced by scratch copies.
- **Mutation isolation.** A mutation scenario is declarative source data, not
  a writable miniature repository. Materialize its versioned baseline into a
  newly created OS temporary directory, initialize and commit a disposable
  git repository there, then apply the versioned input state. Run every
  mutating workflow and post-state comparison only in that temporary copy.
  Never initialize a nested `.git` under `fixtures/`, never point a mutating
  workflow at fixture source data, and never start either host with a current
  working directory under `fixtures/`.
- **Synthetic history only.** Mutation baselines come from the scenario's
  versioned tree manifests. The harness creates their git history in the OS
  temporary directory. Never use this repository's parent history as
  scenario evidence and never check in a git bundle.
- **Contained fixture skills.** Every fixture skill has a harmless body and a
  directory name starting with `fixture-`.
  - Claude fence, two-layered: the fixture project's `.claude/settings.json`
    AND this repo's root `.claude/settings.json` both set every fixture name
    to `"off"` through `skillOverrides`, because project settings load only
    from the session's starting directory while root sessions lazily discover
    nested `.claude/skills/` directories. That suppression is not officially
    documented (live-verified 2026-07-23: without the root override, nested
    fixture skills DO surface in a root session, and only the fixture
    carrying `disable-model-invocation` stays hidden), so harmless bodies are
    the final backstop.
  - Codex fence: every fixture skill directory carries `agents/openai.yaml`
    with `policy.allow_implicit_invocation: false`.
  - Exception: `disable-model-invocation` appears only in the deliberate
    Claude-extension fixture that exercises the portability lint.
  - On add/rename: update BOTH `skillOverrides` maps and the skill's
    `agents/openai.yaml` in the same change.
- **No packaging or repo payloads.** Never add `.claude-plugin/plugin.json`,
  plugin manifests, `allowed-tools` frontmatter, packaging payloads, or a
  nested `.git` inside fixtures. `agents/openai.yaml` is permitted only for
  the implicit-invocation policy above.
- **Byte discipline.** All fixture text files are UTF-8 without BOM with LF
  line endings, no trailing whitespace, and exactly one final newline; the
  root `.gitattributes` enforces LF checkout for the text formats used here.
  Single deliberate exception: `SKILL.md` (master and copy) of the
  `fixture-bom-with-a-very-long-directory-name-exceeding-codexs-limit` skill
  begins with a UTF-8 BOM by design.
- **Expectations move with their fixtures.** Each `expected-report.md` declares
  `- expectation: report/v5`, follows the expectation-file format defined in
  [`skills/bridge-sentinel/references/report-spec.md`](../../skills/bridge-sentinel/references/report-spec.md),
  and changes only together with the fixture bytes it describes, in the same
  change. Pin deterministic live activation inputs in a contained
  `activation-fixture/v2` profile: it adds `codex_project_trust` (`trusted`,
  `untrusted`, or `unknown`) and `codex_hooks_feature` (`enabled`, `disabled`,
  or `unknown`) to the v1 keys, and a profile pinning neither Codex input uses
  `unknown` for both. Use `environment-dependent` only when the expectation
  deliberately excludes all live and capability observations.
- **Fixture hooks are inert by construction.** Every `command` and
  `commandWindows` value a change writes into any fixture
  `.claude/settings.json`, `.codex/hooks.json`, `.codex/config.toml`, or
  `.claude/rules/hooks.md` must match `^bridge-fixture-noop( [a-z0-9-]+)?$`, a
  program that exists on no machine, so an accidental run is a harmless ENOENT.
  `scan_hook_fence()` in
  [`skills/bridge-sentinel/scripts/sentinel_mechanics.py`](../../skills/bridge-sentinel/scripts/sentinel_mechanics.py)
  implements the check today, and `sentinel_mechanics self-test` asserts it over
  synthetic trees; `fixtures/m4-hooks/hooks_harness.py check-hook-fence` runs it
  over the complete fixture tree once the M4 harness lands. Converting the
  pre-M4 commands still carried by `fixtures/onboarded` belongs to the M4
  fixture suite, and the change that converts a command converts its
  `expected-report.md` in the same change.
- **Fixture hooks never execute.** The fixture hook carriers
  `.claude/settings.json` and `.codex/hooks.json` are inert file comparison
  inputs, never loaded by starting a host inside `fixtures/`. No fixture or
  harness step starts either host against fixture source data or against a
  materialized fixture tree with hooks enabled.
  `--dangerously-bypass-hook-trust` is forbidden in every fixture and every CI
  path; it may appear only in a dated, manually run live-verification procedure
  recorded under `.debug-output/`. `disableAllHooks` is never relied upon.
- **Never start a work session with cwd inside `fixtures/`** or inside a
  materialized fixture tree. Fixture project settings and hook keys are real
  host-native keys and can become active there, and the skill fences above do
  not make the rest of the fixture configuration safe to load. A materialized
  temporary project is the only place a host may be pointed at fixture-derived
  bytes, and even there the no-op fence holds.
- **Hook changes move together.** On adding or renaming a fixture hook, update
  the intent document, both carriers, and the expectation in the same change.
- **The leak fence.** This repo's root `.claude/settings.json` carries
  `"claudeMdExcludes": ["**/fixtures/**"]`, which neutralizes fixture
  `CLAUDE.md` and rules files for Claude sessions launched at the repo root.
  It must not be removed while fixtures exist. Codex needs no fence at the
  root: it has no downward discovery from the root (verified 2026-07-08).
