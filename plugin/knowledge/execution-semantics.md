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
- source: official Codex docs; dated notes in [`docs/research/codex-capability-surface.md`](https://github.com/sesamehut/agent-config-bridge/blob/main/docs/research/codex-capability-surface.md)
- status: settled

| Surface | Host | Nature |
|---|---|---|
| `approval_policy` | Codex | Approval behavior enforced by the Codex runtime |
| Sandbox configuration | Codex | Execution sandboxing enforced by the Codex runtime |
| `.codex/rules/` execpolicy | Codex | Execution-policy rules enforced by the Codex runtime |

- The enforcement point of every surface above is the host runtime; prose
  simulation is forbidden.
- These surfaces are declared not-synced, which is the only legitimate source
  of the `declared-unsynced` state (closed state set in the report spec).
- `notify` is user-level-only and is never a projection target.
- Claude permissions ↔ Codex execpolicy is a future mapping candidate
  (post-MVP); no mapping is pinned.

## Degradation eligibility

- collected: 2026-09-07
- source: [`hooks.md`](hooks.md) and the host facts it cites
- status: settled

A degradation is legitimate only when the source mechanism's own effect is
delivering text to the model. A mechanism whose effect is a runtime veto, a
permission decision, or a filesystem or network side effect is never
degradable. This is why a hook entry may take a prose surface only with
`class: reminder` or `class: observation`: restating a reminder reproduces its
entire mechanism, while restating a gate would advertise an enforcement
boundary that no prose enforces.

## Tier-4 hook surfaces

- collected: 2026-09-07
- source: [`hooks.md`](hooks.md), which cites the host documentation and the
  pinned host source for each fact
- status: settled

These hook-side surfaces get no Bridge projection for the reason given. One of
them is found-and-preserved rather than absent: a Claude `if` key on an owned
handler is kept byte-for-byte in place, never written and never compared, and
the row is reported as behavior-degraded. The Codex `additionalContextLimit`
key is preserved the same way.

| Surface | Host | Reason (collected 2026-09-07) |
|---|---|---|
| `async: true` and `asyncRewake` command handlers | both | Both hosts fire and forget: Codex runs them in the background (max 8 concurrent) and Claude honors neither their stdout nor their JSON decisions and does not enforce the timeout |
| Handler types `http`, `mcp_tool`, `prompt`, `agent` | both | Codex rejects `prompt` and `agent` at discovery and the executable remainder has no shared field shape, so no handler type but `command` is projectable |
| Claude `once` | Claude | Claude honors `once` only in skill frontmatter and explicitly ignores it in settings files, so projecting it would write an inert key |
| Claude `if` | Claude | Host-side conditional execution that Bridge does not model; Codex's own importer drops any group carrying it |
| Claude `args` | Claude | It switches the handler to exec form, changes placeholder quoting, cannot spawn `.cmd` or `.bat` shims on Windows, and has no Codex analogue |
| Inline `[hooks]` in `.codex/config.toml` | Codex | Codex merges it with `.codex/hooks.json` inside one layer while the positional trust keys register two entries, so the hook would run twice; presence is detected, never written |
| `.claude/settings.local.json` | Claude | A personal untracked layer whose load location is documented as unreliable on Windows; it stays a read-only observation |
| Claude skill-frontmatter and subagent-frontmatter hooks | Claude | A third carrier with its own trust story, neither scanned, compared, nor written |
| Managed hook policies (`allowManagedHooksOnly`, `allowedHttpHookUrls`, and the Codex managed equivalent) | both | Enforced by managed settings that live outside the repository, so they are neither readable nor writable from a project checkout |

- The enforcement or delivery point of every row above is the host runtime or
  a layer outside the repository; prose simulation is forbidden here for the
  same reason as for the surfaces in the tier-4 list.
- A declared-unsynced hook target is a legitimate authored choice, not a
  failure: the intent document records the target as `none` with tier
  `declared-unsynced`, and the plan states the reason token.
