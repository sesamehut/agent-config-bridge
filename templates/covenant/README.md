# Covenant templates

The two files at this directory root are the only runtime installation assets.
They form the immutable `covenant/v2` pair:

- `claude-rules-bridge.md` installs exactly at
  `.claude/rules/bridge-covenant.md`;
- `agents-md-covenant-block.md` installs as one exact managed block in root
  `AGENTS.md`, preserving every manual-zone byte.

The current pair binds `source-tree/v4`, `report/v4`, `reconciliation/v2`,
and `sync-plan/v2`. Both halves must be tracked, mutually coherent, and exact
before they establish onboarding. Partial, modified, malformed, untracked, or
version-mismatched pairs block normal writes.

`v1/` preserves the exact former `covenant/v1` M2 bytes solely as migration
evidence. Runtime scanning never treats those files as an alternate supported
contract. A project carrying the exact old pair needs one explicit whole-pair
migration; there is no dual-read compatibility mode. That migration also
enumerates every reachable-v1 proven managed unit and carries it through one
closed current-tuple transition commit, or records an explicit repair/release
decision. Replacing only the two covenant bytes does not preserve ownership.

M3 permits skill, entry, and rule projection. `hook-intents.md` remains an
inert M4 planning asset and must not be installed, merged, or enabled in M3.
Before any `AGENTS.md` apply, check root discovery, shadowing, and the exact
post-write byte count against the effective `project_doc_max_bytes`.
