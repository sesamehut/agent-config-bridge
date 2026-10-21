# Host facts: skills

Host facts and the fidelity mapping for the skills unit class: skill
directories under `.claude/skills/` (Claude side; the bridge's master) and
`.agents/skills/` (Codex side; the bridge's projected copy). Facts only —
the skill portability requirements live in
[`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md);
the lint tokens, their conditions, and the comparison rules live in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md).

## Evidence layers

- collected: 2026-07-23
- source: [Agent Skills specification](https://agentskills.io/specification),
  [official Codex skills docs](https://developers.openai.com/codex/skills),
  and [official Claude Code skills docs](https://code.claude.com/docs/en/slash-commands)
- status: settled

Skill evidence is evaluated in four separate layers:

| Layer | Question answered |
|---|---|
| Agent Skills format | Is the skill valid according to the open authoring format? |
| Host runtime acceptance | What bytes does this dated host implementation currently discover and parse? |
| Codex bundled validator | What does the current Codex authoring helper accept? |
| Behavior portability | Do identical bytes produce equivalent behavior in both hosts? |

Acceptance in one layer does not imply acceptance or equivalence in another.
In particular, a permissive runtime parser is not a public authoring contract,
and a validator accepting a key does not prove that the runtime implements its
semantics.

## Agent Skills format

- collected: 2026-07-23
- source: [Agent Skills specification](https://agentskills.io/specification)
- status: settled

- A skill directory contains `SKILL.md` and may contain `scripts/`,
  `references/`, `assets/`, and other supporting files.
- `SKILL.md` is YAML frontmatter followed by a Markdown body. `name` and
  `description` are required.
- `name` is 1–64 characters, uses lowercase letters, digits, and hyphens,
  cannot start or end with a hyphen or contain consecutive hyphens, and must
  match the parent directory name.
- `description` is 1–1024 characters. The standard optional keys are
  `license`, `compatibility`, `metadata`, and `allowed-tools`.
- `allowed-tools` is explicitly experimental, and the specification says
  support may vary between agent implementations. Its presence is format
  compatibility, not evidence of permission-semantic equivalence.
- The format does not define repository discovery paths, trust prompts,
  host-local enablement, invocation policy, or Claude-specific preprocessing.

## Codex repository discovery and activation

- collected: 2026-07-23
- source: [official Codex skills docs](https://developers.openai.com/codex/skills)
  and [Codex config basics](https://learn.chatgpt.com/docs/config-file/config-basic)
- status: settled

- The public repository location is `.agents/skills/`. Codex scans that
  directory at every level from cwd to repository root.
- User skills live under `$HOME/.agents/skills/`; admin skills live under
  `/etc/codex/skills`. M2 targets only the documented repository location.
  A legacy path accepted by a current runtime is not a projection contract.
- Codex exposes skills in its app, CLI, and IDE surfaces. Invocation can be
  explicit (`/skills` or a `$` mention) or implicit through description
  matching.
- Optional `agents/openai.yaml` controls presentation, dependencies, and
  invocation policy. `policy.allow_implicit_invocation: false` disables
  implicit selection without preventing explicit invocation.
- Repository bytes, discoverability, and live activation are orthogonal:
  a directory copy proves only that bytes exist; appearance in a host skill
  list proves discovery and metadata parsing; successful invocation in the
  current session proves live activation.
- Codex documents project trust for project `.codex/` config, hooks, and
  rules. It does not document a corresponding trust gate for
  `.agents/skills/`. The bridge therefore must not synthesize an
  `awaiting-host-trust` state for Codex repository skills.

## Codex user-level skill config

- collected: 2026-07-23
- source: [official Codex skills docs](https://developers.openai.com/codex/skills)
  and
  [`config_rules.rs` at `44d76c6`](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/core-skills/src/config_rules.rs)
- status: settled

- `[[skills.config]]` is documented in `~/.codex/config.toml`. The dated core
  implementation reads per-skill rules only from user and session-flag
  layers, not from project config.
- This setting is user-owned live-activation state, not a repository
  projection surface. M2 neither creates nor edits it.
- An existing user override can make a written and discoverable skill
  inactive. Report that as runtime environment context, not file drift.

## Codex runtime acceptance

- collected: 2026-07-23
- source:
  [`loader.rs` at `44d76c6`](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/core-skills/src/loader.rs)
  and
  [`injection.rs` at `44d76c6`](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/core-skills/src/injection.rs)
- status: watch

- The dated loader materializes `name`, `description`, and
  `metadata.short-description`. It ignores unrecognized frontmatter keys and
  falls back to the directory name when `name` is absent.
- Those permissive behaviors are implementation observations only. Portable
  skills still follow the public Agent Skills format and Codex docs.
- The explicit-invocation path reads `SKILL.md` and forwards its `contents`
  unchanged. Codex does not perform the Claude-specific substitutions or
  shell preprocessing listed below.
- A UTF-8 BOM prevents the first line from being recognized as the opening
  `---`; portable `SKILL.md` files therefore have no BOM.

## Codex bundled validator

- collected: 2026-07-23
- source:
  [`quick_validate.py` at `44d76c6`](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/skills/src/assets/samples/skill-creator/scripts/quick_validate.py)
- status: watch

The bundled `skill-creator/scripts/quick_validate.py` is an authoring gate,
not the runtime parser:

| Check | Current validator behavior |
|---|---|
| Required keys | Requires the `name` and `description` keys and string values |
| Allowed top-level keys | `name`, `description`, `license`, `allowed-tools`, `metadata` |
| `name` | When non-empty, checks grammar, 64-character limit, and hyphen placement |
| `description` | When non-empty, checks the 1024-character limit and rejects angle brackets |
| Directory-name match | Not checked |
| `compatibility` | Rejected even though the Agent Skills format defines it |
| Unknown and Claude-only keys | Rejected |

The current script's acceptance of empty strings is a validator gap; it does
not relax the open standard's non-empty requirement. Likewise, accepting
`allowed-tools` proves only that the key passes this script, not that Codex
implements Claude's permission behavior.

Re-checked 2026-10-19: `quick_validate.py` still ships with codex-cli 0.163.0.
The sibling `plugin-creator/scripts/validate_plugin.py` was removed in 0.159.0
(openai/codex #48604, 2026-09-29) and no `codex plugin validate` subcommand
replaces it.

## Fidelity mapping (skills unit class)

- collected: 2026-07-23
- source: derived from the format and host entries above
- status: settled

- Whole-directory byte copy is a `native` projection mechanism because both
  hosts consume `SKILL.md` directly.
- Behavioral native-equivalence is narrower: the common stable core is a
  format-valid `name`, `description`, static Markdown instructions, and
  ordinary relative references to supporting files.
- `license` and `metadata` can remain byte-identical but do not establish
  runtime behavior. `compatibility` is standard-valid but currently blocked by
  the Codex bundled validator.
- `allowed-tools` is not behaviorally equivalent. Agent Skills marks it
  experimental; Claude implements a one-turn permission grant; Codex does not
  publish the same contract.
- Claude-only frontmatter and Claude-rendered dynamic content degrade on
  Codex even when its permissive loader ignores the keys and the bytes remain
  identical. Degradation belongs on the lint axis, not in the byte-comparison
  result or projection-mechanism tier.

## Claude Code skill runtime

- collected: 2026-07-23
- source: [official Claude Code skills docs](https://code.claude.com/docs/en/slash-commands)
- status: settled

- Claude Code follows Agent Skills but extends it. Its documented frontmatter
  includes `name`, `description`, `when_to_use`, `argument-hint`, `arguments`,
  `disable-model-invocation`, `user-invocable`, `allowed-tools`,
  `disallowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`,
  and `shell`.
- Claude's runtime permits omitted `name` and `description` by falling back to
  the directory name and first body paragraph. That host convenience does not
  relax the bridge's Agent Skills format gate.
- Before the skill content enters context, Claude renders `$ARGUMENTS`,
  `$ARGUMENTS[N]` / `$N`, named `$name` arguments, `${CLAUDE_SESSION_ID}`,
  `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`, and
  `${CLAUDE_PROJECT_DIR}`.
- Claude also executes inline `` !`command` `` placeholders and fenced shell
  blocks marked with `!` before injection, replacing each
  placeholder with command output. Codex leaves the same source text
  unchanged at its injection boundary.
- `allowed-tools` grants no-prompt permission for the invocation turn; it does
  not restrict other tools. Re-checked 2026-10-19: neither the skills nor the
  permissions documentation gates `allowed-tools` on workspace trust, and the
  2026-09-08 live probe saw no such effect, so the earlier "gated by Claude
  workspace trust" sentence is withdrawn.
- Nested `.claude/skills/` directories are discovered on demand.
  `skillOverrides` can change non-plugin skill visibility without modifying
  `SKILL.md`.

## Codex skills-list metadata budget

- collected: 2026-07-23
- source: [official Codex skills docs](https://developers.openai.com/codex/skills)
- status: settled

- The initial skills list (name, description, and path metadata) uses at most
  2% of the context window, or 8,000 characters when the context window is
  unknown.
- Codex shortens descriptions first and may omit skills with a warning when
  the list is too large. It still loads the full `SKILL.md` after selection.
- Consequence: keep projected descriptions concise.

## Skill name collisions

- collected: 2026-07-23
- source: [official Codex skills docs](https://developers.openai.com/codex/skills)
  and [official Claude Code skills docs](https://code.claude.com/docs/en/slash-commands)
- status: settled

- Codex does not merge same-name repository skills; both can appear.
- Claude has enterprise > personal > project > bundled precedence and uses
  directory-qualified names for nested collisions.

## Windows symlink caveat

- collected: 2026-07-23
- source:
  [Microsoft CreateSymbolicLink documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createsymboliclinka)
- status: settled

- Windows symlink creation is privilege- and policy-sensitive; Microsoft
  exposes a separate unprivileged-create flag, with Developer Mode
  requirements on applicable hosts.
- Consequence: projection is a copy, never a symlink.
