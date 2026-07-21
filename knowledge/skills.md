# Host facts: skills

Host facts and the fidelity mapping for the skills unit class: skill
directories under `.claude/skills/` (Claude side; the bridge's master) and
`.agents/skills/` (Codex side; the bridge's projected copy). Facts only —
the skill portability requirements live in
[`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md);
the lint tokens, their conditions, and the comparison rules live in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md).

## Fidelity mapping (skills unit class)

- The projection mechanism is a whole-directory byte copy; both hosts
  consume `SKILL.md` directly, so the mechanism tier is `native`.
- Behavioral native-equivalence holds only for the portable subset (see the
  tiering entry below); everything outside it degrades on Codex while the
  bytes stay identical. Degradation is expressed by portability lints in the
  sentinel report, never by lowering the tier — bytes stay comparable.

## Codex project skills dir

- collected: 2026-07-07, reconfirmed 2026-07-08
- source: official Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled

- Project skills live under `.agents/skills/` — NOT `.codex/skills/`, which
  is the legacy layout (likely invisible to the current CLI).
- Discovery walks cwd→root, at every level.
- Same-name skills coexist; there is no merge or shadow behavior.

## Codex SKILL.md parsing

- collected: 2026-07-07, reconfirmed 2026-07-08
- source: openai/codex@58b66d3 and official Codex docs
- status: settled (facts), watch (BOM fix)

| Frontmatter key | Codex behavior |
|---|---|
| `name` | Optional; defaults to the directory name; at most 64 characters |
| `description` | REQUIRED non-empty; when missing the skill is silently undiscoverable |
| `metadata.short-description` | Parsed |
| any other key (including Claude-only keys) | Ignored for discovery; shown verbatim to the model on invocation |

- The body is injected verbatim: `$ARGUMENTS`, `$N` positional tokens,
  `${CLAUDE_*}` variables, backtick-exec lines, and `@file` references are
  inert literal text — never executed, never substituted.
- A UTF-8 BOM at the start of `SKILL.md` breaks Codex frontmatter parsing
  (openai/codex#13918, open as of 2026-07-08) and makes the skill silently
  undiscoverable. Watch item: the fix status of that bug.

## Skills tiering condition

- collected: 2026-07-08
- source: derived from the Codex SKILL.md parsing and Claude skill surface entries in this file
- status: settled

- The mechanism is `native`: a byte copy, with both hosts consuming
  `SKILL.md`.
- Behavioral native-equivalence holds only for the portable subset:
  {`name`, `description`} frontmatter plus a static body.
- Everything else degrades behaviorally while the bytes stay identical —
  hence the sentinel's lint axis (lint list in the report spec).

## Claude skill surface

- collected: 2026-07-08
- source: official Claude Code skills docs; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled

- Full frontmatter key list: `name`, `description`, `when_to_use`,
  `argument-hint`, `arguments`, `disable-model-invocation`,
  `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`,
  `context`, `agent`, `hooks`, `paths`, `shell`.
- Project skills' `allowed-tools` is gated by workspace trust.
- Nested `.claude/skills/` directories are lazy-discovered from
  subdirectories.

## Windows symlink caveat

- collected: 2026-07-07
- source: Windows platform behavior (symlink creation privilege), verified locally
- status: settled

- Creating symlinks on Windows requires administrator rights or Developer
  Mode.
- Consequence: projection is a copy, never a symlink.

## Codex skills-list metadata budget

- collected: 2026-07-08
- source: official Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled

- The injected skills LIST (name + description + path metadata) has a budget
  of about 2% of the context window / 8000 characters.
- The full SKILL.md body loads only on selection.
- Consequence: keep projected descriptions terse.

## Codex skills config flags

- collected: 2026-07-08
- source: official Codex docs and open issues openai/codex#20210, #24237, #14161, #16012
- status: watch

- `[[skills.config]]` entries (`path`, `enabled`) and
  `[skills] include_instructions = false` can make written skills inert —
  the "written, not active" category.
- Watch item: open bugs openai/codex#20210, #24237, #14161, and #16012
  affect whether project-local filtering is honored.

## Skill name-collision behavior

- collected: 2026-07-08
- source: official Claude Code and Codex docs
- status: settled

- Codex never merges or shadows same-name skills; both appear.
- Claude has a precedence chain — enterprise > personal > project, and any
  level over bundled — plus directory-qualified names for nested skills.

## `.agents/skills` trust gating

- collected: 2026-07-08
- source: official Codex docs (gap); dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: watch

- Trust gating was confirmed for the legacy `.codex/skills` layout; it is
  undocumented for the current `.agents/skills` path.
- Together with the trust-gating entry in [`hooks.md`](hooks.md), this is
  the basis of the `awaiting-host-trust` annotation on Codex-side skills
  rows (annotation rules in the report spec).
- Watch item: re-verify before M2 write work.
