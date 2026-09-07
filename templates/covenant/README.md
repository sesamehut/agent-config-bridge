# Covenant templates

The two files at this directory root are the only runtime installation assets.
They form the immutable `covenant/v3` pair:

- `claude-rules-bridge.md` installs exactly at
  `.claude/rules/bridge-covenant.md`;
- `agents-md-covenant-block.md` installs as one exact managed block in root
  `AGENTS.md`, preserving every manual-zone byte.

The current pair binds `source-tree/v5`, `report/v5`, `reconciliation/v3`,
and `sync-plan/v3`. Both halves must be tracked, mutually coherent, and exact
before they establish onboarding. Partial, modified, malformed, untracked, or
version-mismatched pairs block normal writes.

`v1/` and `v2/` preserve the exact former `covenant/v1` (M2) and `covenant/v2`
(M3) bytes solely as migration evidence. Together they form the closed
archived-pair set; runtime scanning never treats those files as an alternate
supported contract. A project carrying either exact old pair needs one
explicit whole-pair migration in a single hop to the current tuple; there is
no chaining and no dual-read compatibility mode. That migration also
enumerates every reachable proven managed unit of the old tuple and carries it
through one closed current-tuple transition commit, or records an explicit
repair/release decision. Replacing only the two covenant bytes does not
preserve ownership. A v2-to-v3 migration never carries a hooks unit, because
`reconciliation/v2` forbade every hook write.

The covenant text names no milestone. Bridge projects skills, entry
instructions, rule shards, and hook intents; hook intents are ordinary units
declared in `.claude/rules/hooks.md`, never a covenant bootstrap asset. The
example intent document lives at `templates/hook-intents.example.md`.
Before any `AGENTS.md` apply, check root discovery, shadowing, and the exact
post-write byte count against the effective `project_doc_max_bytes`.
