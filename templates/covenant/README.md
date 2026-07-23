# Covenant templates

The two installation files are the immutable `covenant/v1` M2 bootstrap
assets.
`claude-rules-bridge.md` is installed exactly at
`.claude/rules/bridge-covenant.md`. `agents-md-covenant-block.md` is inserted
as one managed block in root `AGENTS.md` while preserving every manual-zone
byte. The body of the managed block is the standard rendering of the source
template.

The pair binds `source-tree/v3`, `report/v3`, `reconciliation/v1`, and
`sync-plan/v1`. Both halves must be tracked and template-valid before they
establish onboarding. A partial, modified, malformed, untracked, or
version-mismatched pair is a blocker and requires an explicit migration or
repair plan.

Bootstrap is the only M2 write to the rules/entry surface. General rules and
entry projection remain M3 work. `hook-intents.md` is an inert M4 planning
asset: M2 must not install, merge, or enable it. Hook projection and
installation remain M4 work. Rendered byte count must be checked against the
target project's effective `project_doc_max_bytes` at install time.
