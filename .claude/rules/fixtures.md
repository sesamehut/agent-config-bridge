---
paths:
  - "fixtures/**"
bridge:
  intent:
    - date: 2026-07-08
      note: fixture-authoring conventions introduced with the first M1 fixtures
---

# fixtures/ - Fixture authoring rules

Everything under `fixtures/` is an inert verification bed for the
bridge-sentinel skill. The rules below are hard rules, binding on every
change inside `fixtures/`.

- **Scan in place, real names.** Fixtures keep their real host-native file
  names (`CLAUDE.md`, `AGENTS.md`, `.claude/…`, `.agents/…`, `.codex/…`) and
  are scanned where they sit. Never neutralize file names and never scan
  scratch copies instead of the fixture itself.
- **Contained fixture skills.** Every fixture skill's `SKILL.md` carries
  `disable-model-invocation: true` in its frontmatter, has a harmless body,
  and lives in a directory whose name starts with the `fixture-` prefix.
- **No packaging or repo payloads.** Never add `.claude-plugin/plugin.json`,
  `allowed-tools` frontmatter, packaging payloads, or a nested `.git` inside
  fixtures.
- **Byte discipline.** All fixture text files use LF line endings, carry no
  trailing whitespace, end with exactly one final newline, and are UTF-8
  without BOM. Single deliberate exception: the declared BOM fixture — the
  `fixture-bom-with-a-very-long-directory-name-exceeding-codexs-limit`
  skill's `SKILL.md` (master and copy) begins with a UTF-8 BOM by design.
- **Expectations move with their fixtures.** Each `expected-report.md`
  follows the expectation-file format defined in
  [`skills/bridge-sentinel/references/report-spec.md`](../../skills/bridge-sentinel/references/report-spec.md):
  a run-parameter header (expectation version, scan root, scope excludes,
  onboarding flag) plus the normative Findings and Observations content.
  An expectation changes only together with the fixture bytes it describes,
  in the same change.
- **Fixture hooks never execute.** Sentinel runs are file comparison only at
  M1; no fixture hook command is ever run. Live-loading a fixture under
  Codex requires copying it outside this repo first.
- **Parent-history-blind.** Fixture evidence is intent records plus file
  structure only. Never consult this repo's git history as fixture evidence;
  no git bundles ship at M1.
- **Never start a work session with cwd inside `fixtures/`.** That is the
  one path where fixture configuration goes live on both hosts, because
  project settings — including the `claudeMdExcludes` fence below — load
  only from the session's starting directory.
- **The leak fence.** This repo's root `.claude/settings.json` carries
  `"claudeMdExcludes": ["**/fixtures/**"]`, which neutralizes fixture
  `CLAUDE.md` and rules files for Claude sessions launched at the repo root.
  It must not be removed while fixtures exist. Codex needs no fence at the
  root: it has no downward discovery from the root (verified 2026-07-08).
- **Nested fixture skills have no path-exclusion mechanism.** Their
  containment relies entirely on the authoring conventions above
  (`disable-model-invocation: true`, harmless bodies, `fixture-` prefix).
