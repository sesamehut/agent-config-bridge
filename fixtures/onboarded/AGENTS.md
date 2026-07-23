<!-- bridge:managed:start id=rules/bridge-covenant source=.claude/rules/bridge-covenant.md -->
# Bridge covenant

Bridge contract versions: `covenant/v1`, `source-tree/v3`, `report/v3`,
`reconciliation/v1`, and `sync-plan/v1`.

This project keeps each managed project skill as one canonical Git tree at
`.claude/skills/<name>/` and one byte-identical Codex projection at
`.agents/skills/<name>/`. The complete regular-file tree is the unit,
including an explicitly authored `agents/openai.yaml`; the bridge never
derives a sidecar or writes `skills.config`.

Use the `bridge-sync` skill before creating, updating, adopting, deleting,
renaming, or annexing a managed skill. It must present a complete scoped plan
and receive confirmation before writing. Conflict and adoption decisions
always require an explicit choice. The `bridge-sentinel` skill is strictly
read-only and cannot choose a reconciliation direction.

Every managed skill carries `bridge-intent.yaml`. Append a dated motivation
for onboarding, annexation, adoption, rename, or a semantic change. Do not
append a record for a byte-for-byte mechanical reprojection.

Never overwrite an unmanaged skill path or content outside bridge-owned
regions. Preserve the root `AGENTS.md` manual zone byte-for-byte. A `keep`
decision applies only to the current run and leaves the unit unresolved; it
does not create an ignore rule.

M2 projects skills only. General `CLAUDE.md` or rule projection and all hook
installation remain disabled until their roadmap milestones.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=entry source=CLAUDE.md -->
# fixture-onboarded

Shared entry instructions for the onboarded fixture project.

- Commit source and projections together.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=rules/legacy source=.claude/rules/legacy.md -->
Legacy rule text whose source shard was deleted after projection.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=rules/style source=.claude/rules/style.md mode=semantic -->
Applies only when working on files matching: `docs/**/*`. (bridge:pv1)

# Style

- Write documentation in complete sentences.
<!-- bridge:managed:end -->

<!-- bridge:managed:start id=rules/tone source=.claude/rules/tone.md -->
Applies only when working on files matching: `docs/**/*`. (bridge:pv1)

# Tone

- Prefer plain statements over exclamations.
<!-- bridge:managed:end -->

Manual zone: Codex-only notes live here; the sentinel never scans this text.
