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
- **Expectations move with their fixtures.** Each `expected-report.md`
  follows the expectation-file format defined in
  [`skills/bridge-sentinel/references/report-spec.md`](../../skills/bridge-sentinel/references/report-spec.md)
  and changes only together with the fixture bytes it describes, in the same
  change.
- **Fixture hooks never execute.** Sentinel runs are file comparison only at
  M1. M2 mutation fixtures do not install hooks. Any later live-loading check
  must use a materialized temporary project, never fixture source data.
- **Never start a work session with cwd inside `fixtures/`.** Fixture project
  settings and hooks can become active there. The skill fences above do not
  make the rest of the fixture configuration safe to load.
- **The leak fence.** This repo's root `.claude/settings.json` carries
  `"claudeMdExcludes": ["**/fixtures/**"]`, which neutralizes fixture
  `CLAUDE.md` and rules files for Claude sessions launched at the repo root.
  It must not be removed while fixtures exist. Codex needs no fence at the
  root: it has no downward discovery from the root (verified 2026-07-08).
