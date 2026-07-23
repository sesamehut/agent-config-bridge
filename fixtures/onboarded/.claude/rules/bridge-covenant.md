---
bridge:
  covenant:
    version: covenant/v1
    source_tree: source-tree/v3
    report: report/v3
    reconciliation: reconciliation/v1
    sync_plan: sync-plan/v1
  intent:
    - date: 2026-07-23
      note: M2 bootstrap establishes the versioned bridge ownership covenant
---

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
