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
  (see the shared event set entry below), so a command hook targeting a shared
  event has a native carrier on both sides. Same-named events do not establish
  identical matcher domains, timing, timeout, or decision controls; M4 must
  compare those per event.
- Capabilities absent or not executable on one host — such as Codex
  non-command handler types and asynchronous command handling — cannot be
  silently projected. Such targets are declared unsynced in the hook intent
  document rather than simulated in prose (see
  [`execution-semantics.md`](execution-semantics.md)).
- Per-target tiers are declared in the intent document; the M1-valid tier
  set and its schema live in the source-tree spec.

## Shared event set

- collected: 2026-07-07; shared-set refreshed: 2026-07-25
- source:
  [Claude Code hooks reference](https://code.claude.com/docs/en/hooks) and
  [Codex Hooks](https://learn.chatgpt.com/docs/hooks)
- status: settled (shared set), watch (host growth)

Exactly 11 same-named lifecycle events exist on both hosts; there are zero
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
| `SessionEnd` |

## Claude event superset

- collected: 2026-07-08; shared-set relation refreshed: 2026-07-25
- source: official Claude Code hooks docs; dated notes in [`../docs/research/host-context-loading.md`](../docs/research/host-context-loading.md)
- status: settled (shared relation), watch (Claude total and growth)

- The 2026-07-08 Claude snapshot documented 29 hook events. The 2026-07-25
  shared-set refresh confirms that Claude remains a strict superset of the
  current shared 11; it does not claim a refreshed total for Claude's
  independently growing event set.
- Five handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`.
- Command handlers may carry `args`, `async`, `asyncRewake`, `shell`, `if`,
  and `statusMessage`.
- `timeout` is in seconds.
- Unknown event names should be treated as newer than the research date,
  never as invalid.

## Codex hook limits

- collected: 2026-07-07; refreshed: 2026-07-25
- source: [Codex Hooks](https://learn.chatgpt.com/docs/hooks); dated notes in
  [`../docs/research/codex-capability-surface.md`](../docs/research/codex-capability-surface.md)
- status: settled (current official facts), watch (handler implementation and
  the dated openai/codex#17532 implementation report)

- Command-type handlers only: `prompt` and `agent` handlers are parsed but
  skipped; `async` is skipped.
- PreToolUse covers Bash and unified exec, `apply_patch`, MCP tools, and other
  local function tools that use the standard hook path. Hosted tools such as
  WebSearch do not use that path, and specialized local paths may opt out.
- PreToolUse can deny a supported call or allow it with rewritten input;
  `permissionDecision: "ask"` remains unimplemented. PermissionRequest can
  allow, deny, or decline to decide and leave the normal approval prompt in
  place.
- `commandWindows` is Codex-only.
- The official contract supports both project `.codex/hooks.json` and inline
  `[hooks]` tables in `.codex/config.toml`; when both exist in one layer Codex
  merges them and warns. openai/codex#17532 is dated implementation evidence
  to re-test before M4 chooses an inline projection target, not grounds for
  declaring the official inline form universally broken.

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
| Print-only reminder (session start / wrap-up) | Command handler in `.claude/settings.json` | Command handler in `.codex/hooks.json` | `native` | `native` | Per-event stdout visibility differs by host; M4 projection must verify delivery against the then-current hosts before claiming this tier |
| Read-only observation (status / diff print) | Command handler | Command handler | `native` | `native` | For example `git status --short` at `Stop` |
| Pre-execution denial gate for a supported tool path | Command handler with a permission decision | PreToolUse command handler with `allow` / `deny` | `native` | `native` | Exact tool coverage, matcher domains, and `ask` behavior differ; M4 mapping remains pending |
| Standing-instruction carrier (`agents-md` hook surface) | — | — | reserved | reserved | The `structural`/`semantic` hook tiers and the `agents-md` surface are reserved schema values until M4 |
