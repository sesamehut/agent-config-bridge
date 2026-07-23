# Covenant templates

The files in this directory are M1 drafts of the bridge covenant — nothing
here is installed at M1, because installation is milestone-gated: it happens
through the M2+ write path (or as an explicit manual maintainer edit outside
Bridge's write path), never as an M1 acceptance step. Each asset is the exact
install content for one host surface of a user project:
`claude-rules-bridge.md` is the Claude-side standing-rule shard destined for
`.claude/rules/bridge-covenant.md` (the filename that anchors onboarding
trigger (d)); `agents-md-covenant-block.md` is the Codex-side managed block
to insert into the project's root `AGENTS.md`, and is byte-for-byte the
standard rendering of the Claude shard, so once installed the pair verifies
under the ordinary agents-md check and the sentinel can self-check the
covenant like any unit; `hook-intents.md` holds the covenant reminder
entries, in the hook-intent entry format, destined for the project's
`.claude/rules/hooks.md` and projected from there to both hooks surfaces
(`.claude/settings.json` and `.codex/hooks.json`). Rendered byte count of the
AGENTS.md covenant block must be measured against the target project's
effective `project_doc_max_bytes` value at install time; the template does not
freeze a host default into its contract.
