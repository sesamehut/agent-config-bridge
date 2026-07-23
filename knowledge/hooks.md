# Host facts: hooks

Host facts and the fidelity mapping for the hook-intent unit class: hook
intent entries and the two projection surfaces, `.claude/settings.json`
(top-level `hooks` key) and `.codex/hooks.json`. Facts only — the hook
intent document format, ownership derivation, field comparison rules, and
the reinforcement-marker rules live in
[`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md);
report states and annotations live in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md).

## Fidelity mapping (hook-intent unit class)

- Both hosts execute command-type hooks over a shared lifecycle event set
  (see the shared event set entry below), so a command hook targeting a
  shared event transfers natively on both sides.
- Capabilities absent on one host — blocking permission decisions on Codex,
  non-command handler types — cannot be projected; such targets are declared
  unsynced in the hook intent document rather than simulated in prose (see
  [`execution-semantics.md`](execution-semantics.md)).
- Per-target tiers are declared in the intent document; the M1-valid tier
  set and its schema live in the source-tree spec.

## Shared event set

- collected: 2026-07-07
- source: official Claude Code and Codex hooks docs
- status: settled

Exactly 10 same-named lifecycle events exist on both hosts; there are zero
Codex-only events.

| Shared event |
|---|
| `SessionStart` |
| `SubagentStart` |
| `PreToolUse` |
| `PermissionRequest` |
| `PostToolUse` |
| `PreCompact` |
| `PostCompact` |
| `UserPromptSubmit` |
| `SubagentStop` |
| `Stop` |

## Claude event superset

- collected: 2026-07-08
- source: official Claude Code hooks docs; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled (list), watch (growth)

- Claude documents 29 hook events — a strict superset of the shared 10.
- Five handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`.
- Command handlers may carry `args`, `async`, `asyncRewake`, `shell`, `if`,
  and `statusMessage`.
- `timeout` is in seconds.
- Unknown event names should be treated as newer than the research date,
  never as invalid.

## Codex hook limits

- collected: 2026-07-07
- source: official Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled (facts), watch (openai/codex#17532, handler implementation status)

- Command-type handlers only: `prompt` and `agent` handlers are parsed but
  skipped; `async` is skipped.
- PreToolUse intercepts only Bash, apply_patch, and MCP tool calls.
- `permissionDecision: "ask"` is unimplemented.
- `commandWindows` is Codex-only.
- The project-level hooks target is `.codex/hooks.json`; inline hooks in
  `config.toml` are broken (openai/codex#17532, open).

## Trust gating

- collected: 2026-07-07 (file-watcher fact 2026-07-08)
- source: official Claude Code and Codex docs; dated notes in [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled

- Codex loads a project's `.codex/` directory only after the project is
  trusted; modified hooks require re-trust (trust is content-hash bound).
- Claude project-settings hooks are gated by the workspace trust dialog.
- Edits to the hooks file are picked up by a file watcher (2026-07-08).
- This entry is the basis of the `awaiting-host-trust` annotation on
  Codex-side hooks rows (annotation rules in the report spec).

## `.codex/hooks.json` top-level shape

- collected: 2026-07-08, corrected 2026-07-23
- source: official Codex hooks reference; `HooksFile` in openai/codex
  `codex-rs/config/src/hook_config.rs`
- status: settled

- The file's schema is the same family as Claude's `hooks` settings value:
  event → matcher groups → handlers.
- The top level is an object whose `hooks` key holds the event-name map; an
  optional top-level `description` string may accompany it. The 2026-07-08
  pin (bare event-name keys, no wrapper object) was REFUTED by the official
  reference and source on 2026-07-23. The fixtures encode the official
  wrapped shape.

## `statusMessage` reinforcement marker

- collected: 2026-07-08, reverified 2026-07-23
- source: official Claude Code and Codex hooks references
- status: settled

- `statusMessage` is documented on command handlers by both hosts.
- The bridge uses a `[bridge:<id>]` prefix on this field as an OPTIONAL
  ownership reinforcement — never load-bearing; ownership always derives
  from the hook intent document (rules in the source-tree spec).

## `commandWindows` ↔ Claude `shell` field

- collected: 2026-07-07, updated 2026-07-08
- source: official Claude Code and Codex hooks docs
- status: settled (fields), watch (mapping)

- Codex's `commandWindows` (Windows command branch) and Claude's handler
  `shell` field are semantic neighbors.
- The mapping between them is deferred to M4; at M1, `commandWindows` is
  compared on the codex surface only.

## Per-hook-intent-class tier table (M4 stub)

This table is a stub, to be completed at M4 together with declared-tier
cross-validation against these knowledge tables and the reserved
`structural`/`semantic` hook tiers and `agents-md` hook surface. It is
seeded with the intent classes M1 already knows.

| Intent class | Claude mechanism | Codex mechanism | Tier (claude) | Tier (codex) | Notes |
|---|---|---|---|---|---|
| Print-only reminder (session start / wrap-up) | Command handler in `.claude/settings.json` | Command handler in `.codex/hooks.json` | `native` | `native` | Per-event stdout visibility differs by host; delivery is verified at M2 install time |
| Read-only observation (status / diff print) | Command handler | Command handler | `native` | `native` | For example `git status --short` at `Stop` |
| Pre-execution enforcement gate (block/ask before a tool runs) | Command handler with a permission decision | None: `permissionDecision: "ask"` is unimplemented | `native` | `declared-unsynced` | Prose simulation forbidden; see [`execution-semantics.md`](execution-semantics.md) |
| Standing-instruction carrier (`agents-md` hook surface) | — | — | reserved | reserved | The `structural`/`semantic` hook tiers and the `agents-md` surface are reserved schema values until M4 |
