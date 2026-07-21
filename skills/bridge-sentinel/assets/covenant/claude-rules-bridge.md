---
bridge:
  intent:
    - date: 2026-07-08
      note: initial covenant draft (M1 asset; installation is milestone-gated)
---

# Bridge covenant

This project keeps one canonical source for project-level agent
configuration: `CLAUDE.md`, `.claude/rules/*.md` (including the hook intent
document `.claude/rules/hooks.md`), and `.claude/skills/<name>/`. Host-native
counterparts are projections: managed blocks in `AGENTS.md`,
`.agents/skills/<name>/` copies, and declared hooks keys in
`.claude/settings.json` and `.codex/hooks.json`.

For ANY change to project-level agent configuration, from either tool's
session:

1. Land the change in the source tree, and append the motivation and date to
   the entry's `bridge` intent log.
2. Update every affected projection surface in the same unit of work.
3. Commit source and projections together, in one commit.

Never overwrite content outside bridge-managed regions (managed blocks,
managed skill copies, declared hooks keys). Before ending a session, and
before any commit that touches agent configuration, self-check that source
and projections still match; when in doubt, run the bridge-sentinel skill and
follow its report.
