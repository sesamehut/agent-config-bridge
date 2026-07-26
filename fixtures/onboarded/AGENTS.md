<!-- bridge:managed:start id=rules/bridge-covenant source=.claude/rules/bridge-covenant.md -->
# Bridge covenant

Bridge contract versions: `covenant/v2`, `source-tree/v4`, `report/v4`,
`reconciliation/v2`, and `sync-plan/v2`.

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

M3 projects skills, entry instructions, and rule shards. Hook intent
installation and both native hook carriers remain disabled until M4.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=entry source=CLAUDE.md -->
# fixture-onboarded

Shared entry instructions for the onboarded fixture project.

- Commit source and projections together.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=rules/legacy source=.claude/rules/legacy.md -->
Legacy rule text whose source shard was deleted after projection.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=rules/style source=.claude/rules/style.md -->
Applies only while reading or editing files that match at least one of these source globs: `docs/**/*`. (bridge:pv2)

# Style

- Write documentation in complete sentences.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=rules/tone source=.claude/rules/tone.md -->
Applies only while reading or editing files that match at least one of these source globs: `docs/**/*`. (bridge:pv2)

# Tone

- Prefer plain statements over exclamations.
<!-- bridge:managed:end -->

Manual zone: Codex-only notes live here; the sentinel never scans this text.
