<!-- bridge:managed:start id=rules/bridge-covenant source=.claude/rules/bridge-covenant.md -->
# Bridge covenant

Bridge contract versions: `covenant/v3`, `source-tree/v5`, `report/v5`,
`reconciliation/v3`, and `sync-plan/v3`.

This project keeps each managed project skill as one canonical Git tree at
`.claude/skills/<name>/` and one byte-identical Codex projection at
`.agents/skills/<name>/`. The complete regular-file tree is the unit,
including an explicitly authored `agents/openai.yaml`; the bridge never
derives a sidecar or writes `skills.config`.

Shared entry instructions live in one Claude-native project entry. Shared rule
shards live under `.claude/rules/`. Bridge projects each entry/rule unit into
one mechanically rendered block in root `AGENTS.md`; every byte outside
confirmed managed blocks remains a manual zone and is preserved exactly.

Every managed skill carries `bridge-intent.yaml`. Append a dated motivation
for onboarding, annexation, adoption, rename, or a semantic change. Do not
append a record for a byte-for-byte mechanical reprojection.

Entry and rule intent records use strict `bridge:intent` HTML comments, never
unknown YAML frontmatter keys. Shared prose is host-neutral. Wrap truly
Claude-only source paragraphs in `bridge:claude-only` comments; keep truly
Codex-only instructions in the `AGENTS.md` manual zone.

Use `bridge-sync` before creating, updating, adopting, deleting, renaming, or
annexing a managed unit. It must present a complete scoped plan and receive
confirmation before writing. Conflict, adoption, migration, destructive, and
semantic-review decisions require an explicit choice. `bridge-sentinel` is
strictly read-only and cannot choose a reconciliation direction.

Never overwrite an unmanaged path or content outside Bridge-owned regions.
Preserve the root `AGENTS.md` manual zone byte-for-byte. A `keep` decision
applies only to the current run and leaves the unit unresolved; it does not
create an ignore rule.

Bridge projects skills, entry instructions, rule shards, and hook intents.
Hook intents live in `.claude/rules/hooks.md`. Bridge projects each declared
hook only to the native carrier its entry declares, `.claude/settings.json`
for Claude and `.codex/hooks.json` for Codex, and every plan states each
hook's tier and reason for both hosts. Bridge never projects a `gate` or
`side-effect` hook without a dated `enabled-by` record in the source. Hooks
committed to this repository run for everyone who clones it; Bridge
classification is review metadata, not a sandbox. Surfaces outside the
contract tuple named above are not Bridge-managed.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=entry source=CLAUDE.md -->
# fixture-hooks-inline-codex

Shared entry instructions for the inline Codex hooks fixture project.

- Keep both hook carriers inert.
<!-- bridge:managed:end -->

Manual zone: the inline Codex hooks table lives in .codex/config.toml and is
reported as an observation only.
