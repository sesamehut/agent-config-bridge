# Host facts: execution semantics (declared-unsynced surfaces)

Host facts for the execution-semantics surfaces whose enforcement point is
the host runtime itself. These are tier-4 surfaces: they get no projection,
because a natural-language restatement would fake an enforcement boundary
without enforcing anything. How a target is declared unsynced is a bridge
convention defined in
[`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md);
the corresponding report state lives in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md).

## Tier-4 list

- collected: 2026-07-07
- source: official Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled

| Surface | Host | Nature |
|---|---|---|
| `approval_policy` | Codex | Approval behavior enforced by the Codex runtime |
| Sandbox configuration | Codex | Execution sandboxing enforced by the Codex runtime |
| `.codex/rules/` execpolicy | Codex | Execution-policy rules enforced by the Codex runtime |

- The enforcement point of every surface above is the host runtime; prose
  simulation is forbidden.
- These surfaces are declared not-synced — the only legitimate source of the
  `unsupported` classification (state and sync-verb mapping in the report
  spec).
- `notify` is user-level-only and is never a projection target.
- Claude permissions ↔ Codex execpolicy is a future mapping candidate
  (post-MVP); no mapping is pinned.
