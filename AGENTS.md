# agent-config-bridge - workspace notes for agents

Agent Config Bridge is a Claude Code / Codex bridge for project-level agent
configuration. Its core product promise is simple: a project should maintain one
canonical source for agent skills, hooks, and rules, then project that source
into the host-native Claude Code and Codex layouts without asking the user to
maintain two independent trees.

Product scope, architecture, implementation strategy, research, and milestone
planning live under [`docs/`](docs/). Design docs are split by document role,
and the docs inventory is maintained in
[`.claude/rules/docs.md`](.claude/rules/docs.md).

## Scope boundaries

Packaging is delivered as generated boundary artifacts: `plugin/` and the root
`.claude-plugin/marketplace.json` are assembled by
`python -B scripts/package_plugin.py build` from an allowlist and checked by
`python -B scripts/package_plugin.py verify`. Never hand-edit them; rebuild
after changing anything under `skills/`, `templates/`, `knowledge/`,
`scripts/bridge_doctor.py`, or `VERSION`, and keep `verify` green. Do not add
npm package files, bundled JavaScript, a CLI, or any other manifest.
Product artifacts land only in the directories declared in
[`docs/implementation/distribution-model.md`](docs/implementation/distribution-model.md).

## Communication

- Talk to the user in **Chinese**.
- Write `docs/` content in **Chinese**.
- Write everything else in **English**: code, comments, commit messages,
  `README.md`, `CLAUDE.md`, and `AGENTS.md`.

## Documentation

Docs conventions, the directory inventory, and cross-reference rules live in
[`.claude/rules/docs.md`](.claude/rules/docs.md). When adding, renaming, or
removing files under `docs/`, update that inventory in the same change.

## Agent files

`CLAUDE.md` and `AGENTS.md` are twins - one per agent. Mirror every edit into
both; shared conventions belong here, not in a private agent memory.

## Development skill entrypoint

The checked-in `skills/bridge-sentinel/` and `skills/bridge-sync/` directories
are the development source. They are not natively discovered project skills
here, and `plugin/skills/` is their generated copy, never a capability to load
in this repository. When the user explicitly asks to run the bridge sentinel,
check bridge state, or validate its fixtures, read
`skills/bridge-sentinel/SKILL.md` and follow it as the active read-only skill. When the user asks to onboard, project, adopt,
reconcile, delete, rename, or otherwise write Bridge-managed project skills,
entry instructions, rule shards, or hook intents, read
`skills/bridge-sync/SKILL.md` and follow it as the active write-side skill. Its
write scope covers the hook intent document `.claude/rules/hooks.md`, the
`hooks` keys of a project `.claude/settings.json`, and `.codex/hooks.json`.
Never load skills under `fixtures/` or `plugin/` as capabilities.

## Implementation constraints

- Keep generated artifacts out of source control unless a design doc explicitly
  says they are checked-in boundary artifacts.
- This is an AI-native tool: by default deliver capability through skills that
  lean on the agent's, the LLM's, and the host's built-in abilities — file I/O
  through the host's own Read/Edit/Write, semantic mapping through the LLM. Write
  code only when an operation is both trivial to implement and wasteful to do
  in-model, such as byte-level comparison or lookups of already-settled host
  mappings. Require no global npm dependencies.
- Lean on git as the deterministic substrate (`git diff` for changes and
  reachable history for per-unit baseline evidence) instead of bespoke content
  hashing, attribution metadata, or an independently maintained sync baseline.
  Failure compensation is limited to exact values observed by the same live
  operation while its bound journal remains open. Any later reverse operation
  needs a new confirmed plan reconstructed from current bytes and reachable
  Git; never reuse an old temporary journal or erase a user change.
- Ship one skill body to both hosts: no `${CLAUDE_*}` placeholder in skill
  content, every bundled path resolved relative to its own `SKILL.md`, and
  `allowed-tools: Read` so an installed skill can read its bundled references,
  templates, and knowledge. The skill-local `scripts/sentinel_mechanics.py` is
  the mechanical entry on both hosts; never add a second, host-specific wrapper
  layer. Codex injects plugin-root env vars into plugin hook commands only, and
  this plugin ships no hooks. Only the two manifests and `agents/openai.yaml`
  are host-specific.
- Do not overwrite unmanaged or hand-written host-native files. Confirm a plan
  first, write only inside managed regions, and ask for an adoption or
  replacement decision.
- Hooks committed to a repository run for everyone who clones it, and Bridge
  classification is review metadata, not a sandbox. The declared `class` and the
  dated `enabled-by` opt-in are review checkpoints in Git, never an enforcement
  boundary. Bridge never edits host configuration outside the repository,
  including the Codex project trust state in the user's `config.toml`.
- On Windows, Claude runs a hook `command` under Git Bash (PowerShell only where
  Git Bash is absent, re-checked 2026-10-19) while Codex runs `commandWindows`
  under PowerShell (collected 2026-09-07), so a shared command must be a plain
  program invocation valid in both shells; otherwise declare a per-host override
  or a Codex `commandWindows` branch.
- Never run a fixture hook. Every `command` and `commandWindows` value a change
  writes under `fixtures/` must match `^bridge-fixture-noop( [a-z0-9-]+)?$`, and
  `--dangerously-bypass-hook-trust` never appears in a fixture or in any CI
  path. This repository's own carriers stay unarmed: never add hooks to the root
  `.claude/settings.json` and never create a root `.codex/`.
- Never start a work session with cwd inside `fixtures/`; fixture hook keys are
  real host-native keys, and fixture authoring rules live in
  [`.claude/rules/fixtures.md`](.claude/rules/fixtures.md).

## Verification

- **Docs changes**: verify relative links, update the docs inventory, and keep
  product / architecture / implementation claims aligned.
- **Research claims**: record the collection date and re-check official host
  docs before turning research into implementation.
- **Code and product-artifact changes**: run the check procedure defined by the
  newest milestone closure record under `docs/phases/closure/` (its command
  block is cumulative and it links the standing checklists), validate every
  formal skill, and keep the checks aligned with CI as milestones open.

## Debug output

Agent, browser, MCP, and ad-hoc debug captures go under `.debug-output/`.
Do not leave screenshots, dumps, or temporary diagnostics in the repo root.

## Git conventions

- Branch naming: `feature/xxx`, `fix/xxx`, `refactor/xxx`.
- Commit messages: `type(scope): description`.
