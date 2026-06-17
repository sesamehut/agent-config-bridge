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

Do not add a CLI implementation, npm package files, generated plugin manifests,
bundled JavaScript, generated skills, or distribution payloads unless the user
explicitly requests implementation work.

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

## Implementation constraints

- Keep generated artifacts out of source control unless a design doc explicitly
  says they are checked-in boundary artifacts.
- This is an AI-native tool: by default deliver capability through skills that
  lean on the agent's, the LLM's, and the host's built-in abilities — file I/O
  through the host's own Read/Edit/Write, semantic mapping through the LLM. Write
  code only when an operation is both trivial to implement and wasteful to do
  in-model, such as byte-level comparison or lookups of already-settled host
  mappings. Require no global npm dependencies.
- Lean on git as the deterministic substrate (`git diff` for changes, history
  for the last-synced baseline, `git restore` for rollback) instead of bespoke
  content hashing or attribution metadata.
- Keep the Claude entrypoint and Codex entrypoint separate. Claude can rely on
  `CLAUDE_PLUGIN_ROOT`; Codex should use a skill-local wrapper rather than
  assuming an equivalent plugin-root environment variable.
- Do not overwrite unmanaged or hand-written host-native files. Confirm a plan
  first, write only inside managed regions, and ask for an adoption or
  replacement decision.

## Verification

- **Docs changes**: verify relative links, update the docs inventory, and keep
  product / architecture / implementation claims aligned.
- **Research claims**: record the collection date and re-check official host
  docs before turning research into implementation.
- **Code changes**: once implementation starts, define the check command in the
  roadmap and keep it aligned with CI.

## Debug output

Agent, browser, MCP, and ad-hoc debug captures go under `.debug-output/`.
Do not leave screenshots, dumps, or temporary diagnostics in the repo root.

## Git conventions

- Branch naming: `feature/xxx`, `fix/xxx`, `refactor/xxx`.
- Commit messages: `type(scope): description`.
