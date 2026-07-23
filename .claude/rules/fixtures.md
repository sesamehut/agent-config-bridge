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
- **Contained fixture skills.** Every fixture skill has a harmless body and
  lives in a directory whose name starts with the `fixture-` prefix. Claude
  fencing is two-layered, because project settings load only from the
  session's starting directory while nested `.claude/skills/` directories
  are lazily discovered by root sessions: the fixture project's
  `.claude/settings.json` AND this repo's root `.claude/settings.json` both
  set every fixture name to `"off"` through `skillOverrides`. Every fixture
  skill directory also carries `agents/openai.yaml` with
  `policy.allow_implicit_invocation: false` for Codex.
  `disable-model-invocation` appears only in the deliberate Claude-extension
  fixture whose purpose is to exercise that portability lint.
- **No packaging or repo payloads.** Never add `.claude-plugin/plugin.json`,
  plugin manifests, `allowed-tools` frontmatter, packaging payloads, or a
  nested `.git` inside fixtures. `agents/openai.yaml` is permitted only for
  the implicit-invocation safety policy above.
- **Byte discipline.** All fixture text files use LF line endings, carry no
  trailing whitespace, end with exactly one final newline, and are UTF-8
  without BOM. Single deliberate exception: the declared BOM fixture — the
  `fixture-bom-with-a-very-long-directory-name-exceeding-codexs-limit`
  skill's `SKILL.md` (master and copy) begins with a UTF-8 BOM by design. The
  repository root `.gitattributes` enforces LF checkout behavior for the text
  formats used here.
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
- **Never start a work session with cwd inside `fixtures/`.** Fixture project
  settings and hooks can become active there. Skill invocation is separately
  fenced as described above, but that does not make the rest of the fixture
  configuration safe to load.
- **The leak fence.** This repo's root `.claude/settings.json` carries
  `"claudeMdExcludes": ["**/fixtures/**"]`, which neutralizes fixture
  `CLAUDE.md` and rules files for Claude sessions launched at the repo root.
  It must not be removed while fixtures exist. Codex needs no fence at the
  root: it has no downward discovery from the root (verified 2026-07-08).
- **Nested fixture skills remain inert.** Their containment relies on the
  two `skillOverrides` fences above, harmless bodies, and the `fixture-`
  prefix. Whether `skillOverrides` suppresses a lazily discovered nested
  skill is not officially documented (live-verified 2026-07-23: WITHOUT the
  root-level override, nested fixture skills DO surface in a root session,
  and only the fixture carrying `disable-model-invocation` stays hidden) —
  harmless bodies are the final backstop. When a fixture skill is added or
  renamed, update BOTH `skillOverrides` maps and its `agents/openai.yaml`
  in the same change.
