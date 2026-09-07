# Host facts: hooks

Host facts and the fidelity mapping for the hook-intent unit class: hook
intent entries in `.claude/rules/hooks.md` and the projection surfaces
`.claude/settings.json` (top-level `hooks` key), `.codex/hooks.json`, and the
root `AGENTS.md` degradation block. Facts only. The intent document schema,
ownership derivation, comparison rules, byte-stable projection, and marker
rules live in
[`../skills/bridge-sentinel/references/source-tree-spec.md`](../skills/bridge-sentinel/references/source-tree-spec.md);
report states, hook cases, observations, and annotations live in
[`../skills/bridge-sentinel/references/report-spec.md`](../skills/bridge-sentinel/references/report-spec.md);
write-side ownership, plan tiers, warnings, and blockers live in
[`../skills/bridge-sync/references/reconciliation-spec.md`](../skills/bridge-sync/references/reconciliation-spec.md)
and
[`../skills/bridge-sync/references/sync-plan-spec.md`](../skills/bridge-sync/references/sync-plan-spec.md).

Evidence labels are used as in
[`entry-and-rules.md`](entry-and-rules.md): **host contract** is behavior
stated in current official host documentation; **implementation observation**
is behavior read from a pinned official source commit or shipped binary;
**empirical observation** is behavior seen in a dated live host run; **Bridge
policy** is a project-owned consequence and never a host fact.

## Fidelity mapping (hook-intent unit class)

- Both hosts execute command-type hooks over a shared lifecycle event set
  (the dated registry `shared-events/2026-09-07`, 11 events), so a command
  hook on a shared event has a native carrier on both sides. Same-named
  events do not imply identical matcher domains, matcher grammars, timeout
  ranges, output delivery, or decision shapes; every divergence is a row of
  the tier table below.
- A prose surface exists only where one host has no native carrier for the
  declared event. The Codex-only `Interrupt` degrades on Claude to the intent
  document itself, which Claude already loads, so that half costs zero writes;
  a Claude-only event degrades on Codex to one managed block in root
  `AGENTS.md`. Both are limited to intent class `reminder` or `observation`,
  because only those classes have an effect that prose can reproduce.
- Capabilities that no faithful projection can carry, such as asynchronous
  handlers, non-command handler types, and decision shapes only one host
  implements, are declared unsynced rather than restated in prose (see
  [`execution-semantics.md`](execution-semantics.md)).
- Hooks committed to a repository run for everyone who clones it. Bridge
  classification is review metadata, not a sandbox, so the intent class, the
  dated opt-in record, and the file-level acknowledgement are review
  checkpoints in Git and never an enforcement boundary (Bridge policy).
- Per-target tiers are declared in the intent document and validated against
  the dated event registry, never computed. The tier set and the schema live
  in the source-tree spec.

## Per-intent-class tier table

- collected: 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks),
  [Codex Hooks](https://learn.chatgpt.com/docs/hooks), and the live record at
  the end of this file
- status: settled

Reason tokens are the closed registry the plan's `## Hook tiers` section
serializes; this table is the fact base behind that registry.

| Intent class or situation | Claude mechanism | Codex mechanism | claude tier | codex tier | reason token |
|---|---|---|---|---|---|
| reminder/observation, shared-11 event, command handler | `.claude/settings.json` handler | `.codex/hooks.json` handler | `native` | `native` | `shared-event-command` |
| reminder whose stdout is not delivered on the declared event (outside `{SessionStart, UserPromptSubmit}`) | handler runs, output to the debug log only | handler runs, output not injected | `native` | `native` | `output-not-delivered` |
| reminder/observation on a Claude-only event | handler | root `AGENTS.md` `hd1` block | `native` | `semantic` | `claude-only-event` + `degraded-standing-instruction` |
| gate/side-effect on a Claude-only event | handler | none | `native` | `declared-unsynced` | `claude-only-event` + `decision-not-portable` |
| reminder/observation on the Codex-only `Interrupt` | `.claude/rules/hooks.md` itself, zero writes | handler | `semantic` | `native` | `intent-doc-standing-instruction` + `codex-only-event` |
| gate/side-effect on `Interrupt` | none | handler | `declared-unsynced` | `native` | `declared-none` + `codex-only-event` |
| gate on a shared event with a compatible decision shape (`PreToolUse` deny) | handler plus `permissionDecision` | handler plus `allow` / `deny` | `native` | `native` | `shared-event-command` (exit-2 semantics differ per event; see `## Exit codes`) |
| gate needing `permissionDecision: "ask"` on Codex | handler | unimplemented | `native` | `declared-unsynced` | `decision-not-portable` |
| gate on `PermissionRequest` | `decision` is a string | `decision` is an object `{behavior, ...}` | `native` | `declared-unsynced` | `decision-not-portable` |
| side-effect on a shared event | handler | handler | `native` | `native` | `opt-in-pending` until a covering `enabled-by` record exists |
| async or non-`command` handler intent | not declarable in the intent schema | not declarable in the intent schema | `declared-unsynced` | `declared-unsynced` | `async-not-portable` / `handler-type-not-portable` |
| Windows-specific command line | `targets.claude.shell`, or a bash-and-pwsh-portable command | `targets.codex.commandWindows` | `native` | `native` | `platform-command-branch` |
| `SessionEnd` or `Interrupt` timeout | shared 1.5s budget, raisable to 60s | default 1s, hard-clamped to 1..3s with a warning | `native` | `native` | `timeout-cap-differs` |
| matcher domain divergence (`SessionStart` source, `SessionEnd` reason) | 5-value reason domain, `fork` source | no `fork`; `SessionEnd` reason is the single value `other` | `native` | `native` | `matcher-domain` |
| matcher declared for an event Codex ignores (`UserPromptSubmit`, `Stop`, `Interrupt`) | matcher honored where supported | matcher ignored | `native` | `native` | `codex-matcher-ignored` |
| standing-instruction carrier (`agents-md` hook surface) | none | one managed block | `declared-unsynced` | `semantic` | `degraded-standing-instruction` |

## Shared event set

- collected: 2026-07-07; refreshed 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
  and [Codex Hooks](https://learn.chatgpt.com/docs/hooks)
- status: settled (dated registry `shared-events/2026-09-07`), watch (host
  growth)

Codex documents 12 events. Eleven are shared with Claude and one, `Interrupt`,
is the first Codex-only event (openai/codex PR #40511, rust-v0.150.0,
2026-08-26). The 2026-07-25 claim that there are zero Codex-only events is
refuted; see `## Refuted facts`.

| Event | Shared | Notes |
|---|---|---|
| `SessionStart` | yes | both hosts add plain stdout as context |
| `SubagentStart` | yes | |
| `PreToolUse` | yes | matcher honored on both hosts |
| `PermissionRequest` | yes | decision shapes differ |
| `PostToolUse` | yes | Claude exit 2 does not block |
| `PreCompact` | yes | |
| `PostCompact` | yes | |
| `UserPromptSubmit` | yes | Codex ignores the matcher |
| `SubagentStop` | yes | |
| `Stop` | yes | Codex ignores the matcher; plain stdout invalid on Codex |
| `SessionEnd` | yes | Codex timeout clamped to 1..3s; no output schema |
| `Interrupt` | Codex only | Codex ignores the matcher; timeout clamped to 1..3s |

Unknown event names are treated as newer than the registry date, never as
invalid; the intent document keeps them valid and annotates them
`event-unverified`.

## Claude event superset

- collected: 2026-07-08; refreshed 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- status: settled (superset relation), watch (Claude total and growth)

- Claude documents 33 hook events on 2026-09-07 and remains a strict superset
  of the shared 11.
- Five handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`.
- MCP tool handler fields (documented under `#### MCP tool hook fields`) are
  `server` (required; a plugin-bundled server uses the scoped
  `plugin:<plugin-name>:<server-name>` form, must already be connected, and
  never triggers OAuth), `tool` (required), and `input` (optional; string
  values support `${path}` substitution from the hook's JSON input, for
  example `"${tool_input.file_path}"`). Tool text content is read like
  command-hook stdout. A disconnected server or `isError: true` is a
  non-blocking error and execution continues; `SessionStart` and `Setup`
  typically fire before servers connect.
- Command handlers may carry `args`, `async`, `asyncRewake`, `shell`, `if`,
  `once`, and `statusMessage`.
- `timeout` is in seconds.

## Codex handler and event support

- collected: 2026-07-07; rewritten 2026-09-07
- source: [Codex Hooks](https://learn.chatgpt.com/docs/hooks);
  `codex-rs/config/src/hook_config.rs` and
  `codex-rs/hooks/src/engine/discovery.rs` in openai/codex `main`
- status: settled (current release facts), watch (main-branch fields that the
  0.153.x release does not carry)

- Handler variants parse as `command`, `mcp_tool`, `prompt`, `agent`. `prompt`
  and `agent` are rejected at discovery ("prompt hooks are not supported yet",
  "agent hooks are not supported yet"). `mcp_tool` is recognized and executes.
  Bridge projects `command` handlers only; `http`, `mcp_tool`, `prompt`, and
  `agent` are never written to either carrier.
- `async: true` command hooks now run in the background, capped at 8
  concurrent, and `SessionEnd` is always synchronous. The earlier "async is
  skipped" reading is refuted.
- Timeout normalization runs before dispatch and before the trust hash:
  `SessionEnd` and `Interrupt` default to 1 second and clamp to 1..3 with a
  warning; every other event is `unwrap_or(600).max(1)`, so the general
  default is 600 seconds with a 1 second minimum.
- Nine of the 12 events honor a matcher; `UserPromptSubmit`, `Stop`, and
  `Interrupt` ignore it.
- `PreToolUse` covers the shell and unified exec tool, `apply_patch`, MCP
  tools, and other local function tools on the standard hook path. Hosted
  tools such as `WebSearch` do not use that path and never reach hooks.
- `PreToolUse` can deny a supported call or allow it with rewritten input;
  `permissionDecision: "ask"` remains unimplemented. `PermissionRequest` can
  allow, deny, or decline to decide and leave the normal approval prompt in
  place, but its decision is an object, not Claude's string (see
  `## Refuted facts`).
- Common output fields `continue`, `stopReason`, `systemMessage`, and
  `suppressOutput` are supported on `SessionStart`, `PreCompact`,
  `PostCompact`, `UserPromptSubmit`, `SubagentStop`, and `Stop`; `PreToolUse`
  and `PermissionRequest` support `systemMessage` only. Returning an
  unsupported field marks the hook run failed, reports the error, and
  continues the tool call. `suppressOutput` parses but is not yet implemented.
- Model-visible hook output is capped around 2,500 tokens; overflow is saved
  under `<temp_dir>/hook_outputs/<session_id>/<uuid>.txt`.
- Both project `.codex/hooks.json` and inline `[hooks]` tables in
  `.codex/config.toml` are official carriers. Within one layer Codex merges
  them and warns, and because the persisted trust key embeds the source path
  plus positional indices, the two forms register as two distinct keys that
  share one normalized hash, so the hook runs twice. openai/codex#17532
  remains open (last activity 2026-05-21) and used the legacy
  `hooks = "<path>"` pointer key with the deprecated `features.codex_hooks`
  alias. Bridge writes `.codex/hooks.json` only.

## `.codex/hooks.json` top-level shape

- collected: 2026-07-08; corrected 2026-07-23; strictness scoped 2026-09-07
- source: [Codex Hooks](https://learn.chatgpt.com/docs/hooks);
  `HooksFile` in openai/codex `codex-rs/config/src/hook_config.rs`
- status: settled (implementation observation for the strictness scope)

- The file's schema is the same family as Claude's `hooks` settings value:
  event, then matcher groups, then handlers.
- The top level is an object whose `hooks` key holds the event-name map; an
  optional top-level `description` string may accompany it. The 2026-07-08 pin
  (bare event-name keys, no wrapper object) was refuted by the official
  reference and the source on 2026-07-23. The fixtures encode the official
  wrapped shape.
- `#[serde(deny_unknown_fields)]` appears exactly once, on `HooksFile`.
  `MatcherGroup` and `HookHandlerConfig` do not deny unknown fields, so an
  unknown top-level key rejects the whole file while an unknown key inside a
  matcher group or a handler object is silently ignored. Knowledge and specs
  must not claim handler-level strictness.
- Bridge writes only documented fields, so its own output can never break the
  file; an unknown key found on an owned handler is reported, not removed.

## Distribution

- collected: 2026-09-07
- source: official Claude Code settings documentation;
  [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- status: settled

- Official guidance is to commit `.claude/settings.json` so that everyone who
  clones the repository gets the same permissions, hooks, telemetry, and
  plugins. Committing the carrier is the documented normal case, not an abuse.
- The per-teammate opt-outs are the per-run flags `--bare`, `--safe-mode`,
  `--setting-sources user`, and `--settings '{"disableAllHooks": true}'`. None
  of them is observable from repository bytes.
- Take-effect timing is not promised. Claude documents settings changes as
  normally picked up, with a documented miss-and-restart failure mode, so this
  repository claims no take-effect-without-restart behavior on either host.
- Consequence (Bridge policy): every Claude hooks write carries an
  acknowledged warning, and the source document carries a one-time dated
  file-level acknowledgement before the first Claude hook is written. Hooks
  committed to a repository run for everyone who clones it, and Bridge
  classification is review metadata, not a sandbox.

## Trust gating

- collected: 2026-09-07 (replaces the 2026-07-07 entry)
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
  `## Security considerations` / `### Workspace trust`; official Claude Code
  permissions documentation; [Codex Hooks](https://learn.chatgpt.com/docs/hooks);
  the live record at the end of this file
- status: settled

- Claude, host contract: in an interactive session, hooks from every settings
  file, including the user's own, are held back until the workspace trust
  dialog is accepted. A `-p` or SDK session "never shows the dialog and treats
  the folder as trusted, so hooks committed in a repository's
  `.claude/settings.json` run in a folder you've never trusted". The
  permissions documentation's "What runs before you trust a folder" table
  lists hooks in settings files as used in the untrusted situations it covers;
  only `permissions.allow` and `additionalDirectories` are held back.
- Claude, empirical observation (2026-09-07): project-settings `SessionStart`
  and `Stop` hooks fired in a fresh `claude -p --setting-sources project` run
  in a never-trusted, non-git temp directory.
- What Claude does gate: project subagent-frontmatter hooks require the
  interactive trust dialog (fixed in v2.1.218). Project skill-frontmatter
  hooks are explicitly not gated and follow the settings-file rule.
- Mitigations the Claude doc names: review `.claude/` settings first, start
  with `--bare`, or pass `--settings '{"disableAllHooks": true}'`.
- Consequence: the workspace trust dialog is not a boundary Bridge may rely on
  for committed hooks. The old blanket claim that project-settings hooks are
  gated by that dialog is refuted.
- Codex: a project's `.codex/` layer loads only after the project is trusted,
  and project trust is read from the user config file's `projects` table
  (`[projects."<path>"] trust_level`). A `-c projects.*` CLI override does not
  make the layer load (live test G). Untrusted project hooks are silently
  skipped, with no prompt and no notice in the `codex exec --json` stream.
- Codex per-hook trust is a second, independent gate bound to a normalized
  content hash; see the three entries below. This pair of facts is the basis
  of the `awaiting-host-trust` annotation and of the live-activation
  observation `codex-project-untrusted`.

## Per-hook trust identity

- collected: 2026-09-07
- source: `codex-rs/hooks/src/engine/discovery.rs` in openai/codex `main`
  (there is no `hooks/src/trust.rs`)
- status: settled (implementation observation)

- Codex hashes a `NormalizedHookIdentity { event_name, matcher group with one
  normalized handler }` serialized to TOML, described in source as "a
  normalized, config-derived identity instead of source text so equivalent
  hooks from config TOML and hooks.json converge on the same trust identity".
- Normalization runs before the hash. The timeout default and clamp are
  applied first, and `additionalContextLimit` is normalized (an explicit
  default value equals omission, and it is forced to none outside
  `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, and
  `SubagentStart`).
- In the identity: `event_name`, `matcher`, `command`, the normalized
  `timeout`, `async`, `statusMessage`, and the normalized
  `additionalContextLimit`. `${VAR}` substitution is applied to `command`
  after the hashed config is cloned, so the identity hashes the
  pre-substitution command text.
- Not in the identity: `commandWindows`. The rebuilt config hardcodes
  `command_windows: None`, so replacing only the Windows branch keeps an
  existing trusted hash valid and the new Windows command runs under old
  trust. This asymmetry is security-relevant, so a Windows-branch-only
  replacement is disclosed as the informational `codex-trust-blind-change`
  while a change to an identity field is disclosed as
  `codex-hook-retrust-required`.
- Consequences: reformatting or reordering unrelated groups does not
  invalidate trust, but editing `command`, `matcher`, `timeout`,
  `statusMessage`, `async`, or `additionalContextLimit` does. Omitting
  `timeout` hashes identically to writing 600, and a `SessionEnd`
  `timeout: 5` hashes identically to `timeout: 3`.

## Trust state location and positional keys

- collected: 2026-09-07
- source: `codex-rs/tui/src/hooks_rpc.rs`,
  `codex-rs/app-server-protocol/src/protocol/v2/config.rs`, and
  `codex-rs/hooks/src/lib.rs` in openai/codex `main`; codex-cli 0.153.4 binary
  strings
- status: settled (implementation observation); the interactive write is not
  yet exercised on this machine (see `## Still open`)

- The TUI `/hooks` flow sends
  `ConfigBatchWrite { edits: [ConfigEdit { key_path: "hooks.state", value: {"<key>": {"trusted_hash": "<hash>"}}, merge_strategy: Upsert }], file_path: None, reload_user_config: true }`.
  `file_path: None` defaults to the user's `config.toml`, so persisted
  per-hook trust lives in the user config file and there is no separate hook
  state file. The 2026-09-07 probe that found no `hooks` lines in that file
  simply means no hook has ever been trusted on this machine.
- The persisted shape is `[hooks.state."<key>"] { enabled, trusted_hash }`
  (`HookStateToml`, confirmed in the 0.153.4 binary).
- The key is `{key_source}:{Event}:{group_index}:{handler_index}` with an
  absolute source path, so it is positional. Reordering matcher groups or
  handlers re-keys existing entries and silently orphans them, which can also
  discard a user's deliberate `enabled = false`.
- Consequence (Bridge policy): render groups and handlers in a stable sorted
  order, append only, never reorder, and report any index shift.

## Trust dispatch

- collected: 2026-09-07
- source: openai/codex `codex-rs/hooks` engine (`hook_trust_status()`);
  codex-cli 0.153.4 binary strings; live tests H and I
- status: settled (implementation observation)

- `hook_trust_status()` yields `Trusted | Modified | Untrusted | Managed`. A
  handler is registered only when `enabled && (bypass || Managed | Trusted)`.
- Untrusted and Modified hooks are listed but silently skipped at dispatch.
  They never block a turn and never prompt mid-session.
- Live: an untrusted project hook did not run under `codex exec` and the
  `--json` stream carried no "needs review" notice; the same hook ran with
  `--dangerously-bypass-hook-trust`, which also emits two `error` items
  warning that enabled hooks may run without review. That flag never appears
  in fixtures or CI and is reserved for a dated manual evidence procedure.
- TUI vocabulary in 0.153.4: "New hook - review required", "Modified since
  last trusted - review required", "1 hook needs review before it can run.".
- Consequence: a written and byte-verified Codex hook is not a running hook.
  `awaiting-host-trust` is a post-write annotation only, and the report tells
  the user to run `/hooks` in Codex because `codex exec` does not prompt.

## Environment

- collected: 2026-09-07
- source: `codex-rs/hooks/src/engine/command_runner.rs` in openai/codex
  `main`; [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- status: settled

- Project-scoped Codex hooks receive no injected environment variables at all
  (`env: HashMap::new()`). `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, `PLUGIN_DATA`,
  and `CLAUDE_PLUGIN_DATA` are injected only for plugin-sourced hooks.
- `build_command` calls `env_clear()` and replays a captured session
  environment snapshot rather than the live process environment (openai/codex
  "Run hooks with the captured session environment (#39314)", 2026-08-18).
- Claude exports `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, and
  `${CLAUDE_PLUGIN_DATA}` to hook commands in both exec and shell form.
- Consequence: a single shared command may not reference any path
  placeholder, because the placeholder that Claude expands is literally absent
  on Codex. Such an intent needs a per-host `command` override with
  `override-reason: env-placeholder`.

## Delivery per event

- collected: 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
  `#### Exit code 0`; [Codex Hooks](https://learn.chatgpt.com/docs/hooks);
  live test K
- status: settled

- Claude adds plain-text stdout as context only on `UserPromptSubmit`,
  `UserPromptExpansion`, `SessionStart`, and `PostModelSwitch`. For every
  other event stdout goes to the debug log and is not shown in the transcript.
  Stderr on exit 0 goes to the debug log only.
- Claude's stdout parsing rule: output that starts with `{` and ends with `}`
  is parsed as JSON; output that starts with `{` but does not end with `}` is
  plain text; anything else is plain text. A parse failure is a non-blocking
  error on every exit code other than 2, and on a context-adding event the
  text is then not added.
- Claude `Stop` reacts only to JSON (`decision: "block"` with `reason`, or
  `hookSpecificOutput.additionalContext`) or to exit 2 with stderr as the
  reason; eight consecutive blocks end the turn. `additionalContext` is placed
  at conversation start for `SessionStart` and `SubagentStart` and at end of
  turn for `Stop` and `SubagentStop`; values over 10,000 characters spill to a
  file in the session directory with a short preview.
- Codex `SessionStart` accepts both forms: plain text on stdout "is added as
  extra developer context", and `hookSpecificOutput.additionalContext` is
  added as developer context. After compaction, `SessionStart` hooks matching
  `source: "compact"` run before the next model request.
- Codex `Stop` rejects plain text; it expects JSON on stdout at exit 0, or
  exit 2 with stderr. `continue: false` takes precedence.
- Codex documents `additionalContext` for `SessionStart` and
  `UserPromptSubmit`, so the shared delivering set is exactly
  `{SessionStart, UserPromptSubmit}`.
- `systemMessage` alone is not model-visible on either host; live test K
  confirmed the model never received it on Codex. On Claude at `Stop` it
  becomes visible only together with `stopReason`, which overrides the
  displayed stop reason.
- Consequence: `hook-output-not-delivered` is informational and applies only
  to a `class: reminder` entry whose declared event is outside the shared
  delivering set. It never applies to `observation`, whose effect does not
  depend on delivery.

## Windows shells

- collected: 2026-09-07 (live), source-confirmed the same day
- source: `codex-rs/hooks/src/engine/command_runner.rs`,
  `codex-rs/shell-command/src/shell_detect.rs`, and `codex-rs/core/src/shell.rs`
  in openai/codex `main`;
  [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
  `## Windows PowerShell tool`; live tests J, L2, and L3
- status: settled

- Codex runs a Windows hook command as `<shell> -NoProfile -Command <command>`
  where the shell is the session's detected shell. On Windows that detection
  is unconditionally PowerShell: `pwsh` first (falling back to
  `C:\Program Files\PowerShell\7\pwsh.exe`), then `powershell.exe`.
  `COMSPEC` / `cmd.exe /C` is reached only when the session shell program is
  empty. Live confirmation: a `commandWindows` of `echo %COMSPEC% > file`
  wrote the literal `%COMSPEC%`, and
  `Write-Output pwsh-$($PSVersionTable.PSVersion)` wrote `pwsh-7.6.5`.
- The earlier cmd.exe reading, including the Codex source comment that names
  `$COMSPEC`, is superseded as of 2026-09-07 by both the live run and the
  shell-detection source.
- Claude runs a Windows hook `command` under bash (Git Bash): a probe printed
  `$BASH_VERSION` as `5.2.37(1)-release`, and PowerShell syntax produced no
  file at all. A Claude command handler may opt into PowerShell with
  `"shell": "powershell"`, which auto-detects `pwsh.exe` and falls back to
  `powershell.exe`.
- Binding consequence: on one Windows machine Claude executes `command` under
  bash while Codex executes `commandWindows` under pwsh, so a single shared
  command string must be a plain program invocation with simple arguments that
  is valid in both, or the entry must carry per-host branches. Codex's
  documented `$(git rev-parse --show-toplevel)/...` idiom is not portable to
  the Windows branch.
- A hook that emits a JSON envelope must be a committed script file. An inline
  `cmd /c echo {json}` mangles the quoting and the envelope is not delivered,
  while the identical JSON printed by a script file is delivered (live test K).
- On Windows only the `commandWindows` branch runs on Codex, for all four
  tested events; the `command` branch does not run. Test J declared both keys
  on every handler, so what is proven is that a present `commandWindows`
  replaces `command` on Windows; the `commandWindows`-absent case was not
  tested and Bridge keeps treating a shared `command` as the Windows text,
  which is why it must also be valid in pwsh.

## Matcher grammar

- collected: 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks);
  [Codex Hooks](https://learn.chatgpt.com/docs/hooks)
- status: settled

- Claude mode-switches on a character class: a matcher composed only of
  `[A-Za-z0-9_ ,|-]` is an exact string or a `|` / `,` separated list, and
  anything else is an unanchored `RegExp.prototype.test`. `FileChanged` and
  `StopFailure` use the narrower set `[A-Za-z0-9_|]`.
- Codex matchers are always unanchored Rust `regex` patterns, with no
  lookahead and no backreferences. A valid JavaScript regex can therefore fail
  to compile on Codex, where the failure is logged rather than blocking.
- Nine of Codex's 12 events honor a matcher; `UserPromptSubmit`, `Stop`, and
  `Interrupt` ignore it.
- Matcher domains are not only tool names. `SessionStart` matches a source
  domain that includes the Claude-only value `fork`, and `SessionEnd` matches
  a reason domain of five values on Claude versus the single value `other` on
  Codex (live test J observed `reason: "other"`).
- Consequence: `matcher: Write|Edit` is an exact two-item list on Claude and a
  substring alternation on Codex, and `matcher: Write,Edit` is an exact
  two-item list on Claude but a regex that matches the literal text
  `Write,Edit` on Codex, so it never fires there. One shared string that
  selects different interpretation modes on the two hosts is an acknowledged
  divergence, not a schema violation, and per-host matcher overrides exist for
  exactly this. Bridge draws one closed advisory from these facts:
  `matcher-grammar-divergent` fires exactly when a shared `matcher` inside the
  Claude list class contains `|` or `,`, both targets declare a host-executed
  JSON surface, and neither target overrides `matcher`; a bare literal such as
  `Bash` is read the same way on both hosts and never fires it.

## Exit codes

- collected: 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks);
  [Codex Hooks](https://learn.chatgpt.com/docs/hooks)
- status: settled

- Codex exit 2 is a uniform blocking or denial decision across events.
- On Claude, exit 2 does not block on `PermissionRequest`, `StopFailure`,
  `PostToolUse`, `PostToolUseFailure`, or `PermissionDenied`, and
  `WorktreeCreate` aborts on any non-zero exit.
- Consequence: a hook written to Codex's uniform exit-2 contract silently
  fails to block on Claude for those events, so a `gate` intent on them is not
  portable.

## `once`

- collected: 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- status: settled

- Claude honors `once` only in skill frontmatter and explicitly ignores it in
  settings files.
- Bridge never projects `once`. Because the host ignores it in the carrier
  Bridge writes, its presence on an owned handler is an actionable mistake and
  is treated as semantics-changing drift rather than a preserved passthrough
  key.

## Vendor corroboration

- collected: 2026-09-07
- source: openai/codex `external-agent-migration/src/hooks_cla.rs`
- status: settled (implementation observation)

- Codex's own Claude-to-Codex hook importer honors `disableAllHooks: true`,
  carries over only groups whose keys are exactly `{matcher, hooks}` (dropping
  any group carrying `if`), and carries only `command` handlers whose keys are
  a subset of `{type, command, timeout|timeoutSec, statusMessage, async}`,
  dropping `async: true`, `asyncRewake`, `shell`, and `once`.
- The host vendor independently arrived at essentially the same cross-host
  safe core that Bridge projects. This is corroboration for the projected key
  set, not a contract Bridge may cite as a promise.

## Layering

- collected: 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks);
  [Codex Hooks](https://learn.chatgpt.com/docs/hooks)
- status: settled

- Hook entries merge additively across settings levels on both hosts, so an
  identical user-level hook plus a Bridge-projected project-level hook runs
  twice.
- Detecting that requires reading user-level configuration, which is outside
  the repository-bytes input domain, so this milestone discloses the hazard
  and implements no deduplication.
- `disableAllHooks` resolves by settings precedence, so a project `false`
  overrides a user `true`. Only the tracked projection file is visible in
  repository bytes, which is what the `hooks-globally-disabled` observation
  reads; a user-level value that a project value overrides, or the reverse, is
  not resolvable from the repository.

## Non-claim

- collected: 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- status: settled

- Claude skill-frontmatter and subagent-frontmatter hooks are a third hook
  carrier. Bridge does not scan, compare, or write it, and this repository
  already ships two project skills, so the gap is real and stated rather than
  partially covered.
- Managed hook policies (`allowManagedHooksOnly`, `allowedHttpHookUrls`, and
  the Codex managed equivalent) live in managed settings outside the
  repository and outside anything Bridge can read portably (see
  [`execution-semantics.md`](execution-semantics.md)).

## Codex tool vocabulary

- collected: 2026-09-07
- source: `codex-rs/core/src/tools/hook_names.rs` and the tool handlers in
  openai/codex `main`; [Codex Hooks](https://learn.chatgpt.com/docs/hooks)
  tool coverage; live test L3
- status: settled (canonical names), watch (the set is open-ended)

- `HookToolName { name, matcher_aliases }`; aliases are matcher-only and "must
  not change the payload seen by hook processes".
- `Bash` is the shell and unified exec tool. Live-confirmed envelope keys:
  `session_id`, `turn_id`, `transcript_path`, `cwd`, `hook_event_name`,
  `model`, `permission_mode`, `tool_name`, `tool_input`
  (`{"command": "..."}`), `tool_use_id`, and on `PostToolUse` a string
  `tool_response`.
- `apply_patch` carries the matcher aliases `Write` and `Edit`; the stdin
  payload always shows `apply_patch`.
- `spawn_agent` carries the matcher alias `Agent`.
- Every other local function tool reports its own flat function name, for
  example `update_plan`, `write_stdin`, and `request_permissions`. MCP tools
  are `mcp__<server>__<tool>`.
- Hosted tools such as `WebSearch` do not use the local function-tool hook
  path and never reach hooks.
- The vocabulary is open-ended, so a Codex matcher can be syntactically valid,
  byte-verified, and tier `native` and still never fire because the tool-name
  spelling is wrong. Grammar checks do not verify vocabulary.

## Codex SessionEnd

- collected: 2026-09-07
- source: Codex hook JSON schemas (12 `*.command.input`, 11 `*.command.output`)
- status: settled (implementation observation)

- There are 12 `*.command.input` schemas but only 11 `*.command.output`
  schemas: `session-end.command.output.schema.json` does not exist.
- Codex `SessionEnd` hooks are therefore fire-and-forget with no documented
  way to influence the host, and their timeout is the clamped 1..3 second
  range. Live test J observed the envelope as `session_id`,
  `transcript_path`, `cwd`, `hook_event_name`, and `reason` ("other"), with no
  `model` and no `permission_mode`.

## `statusMessage` reinforcement marker

- collected: 2026-07-08; reverified 2026-07-23; trust consequence added
  2026-09-07
- source: official Claude Code and Codex hooks references;
  `codex-rs/hooks/src/engine/discovery.rs`
- status: settled

- `statusMessage` is documented on command handlers by both hosts.
- Bridge uses a `[bridge:<id>]` prefix on this field as an OPTIONAL ownership
  reinforcement. It is never load-bearing; ownership always derives from the
  hook intent document (rules in the source-tree spec).
- `statusMessage` is inside Codex's normalized trust identity, so adding,
  changing, or removing it invalidates trust. Bridge therefore writes the
  marker on the Claude surface always and on the Codex surface only when
  creating the handler, and never touches a Codex `statusMessage` on an
  otherwise converged handler.

## `commandWindows` ↔ Claude `shell` field

- collected: 2026-07-07; rewritten 2026-09-07
- source: [Claude Code hooks reference](https://code.claude.com/docs/en/hooks);
  [Codex Hooks](https://learn.chatgpt.com/docs/hooks); openai/codex
  `external-agent-migration/src/hooks_cla.rs`; live tests J, L2, and L3
- status: settled (two independent per-host fields, 2026-09-07)

- The two fields are not semantic neighbors and there is no mapping between
  them. Claude's `shell` selects the interpreter, is ignored when `args` is
  set, and never changes the command text. Codex's `commandWindows` selects
  the command text on Windows, and Codex has no per-handler interpreter
  selector.
- Codex's own Claude-to-Codex importer drops handlers carrying `shell`, which
  confirms it as a Claude-only divergence.
- Bridge never derives one field from the other. A projected Claude
  `commandWindows` key and a projected Codex `shell` key both remain
  undeclared, and `commandWindows` is compared on the Codex surface only.
- A `commandWindows` that differs from the effective `command` means Windows
  and POSIX run different code, which the plan discloses per handler.
- `commandWindows` is outside the Codex trust identity, so a Windows-only
  replacement is invisible to per-hook trust (see
  `## Per-hook trust identity`).

## Refuted facts

- collected: 2026-09-07
- source: named per item below
- status: settled

Every correction below was collected on 2026-09-07 and supersedes the dated
claim it names.

1. Old claim (this file, 2026-07-07): "Claude project-settings hooks are gated
   by the workspace trust dialog." Now: the gate does not cover the `-p` or
   SDK path, which treats the folder as trusted and runs committed hooks, and
   the permissions table lists settings-file hooks as used in the untrusted
   situations it covers. Subagent-frontmatter hooks are gated;
   skill-frontmatter hooks are not. Source:
   [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
   `### Workspace trust`, the permissions documentation's "What runs before
   you trust a folder" table, and live test 1 below.
2. Old claim (this file, 2026-07-25): "Exactly 11 same-named lifecycle events
   exist on both hosts; there are zero Codex-only events", echoed by
   `docs/research/codex-capability-surface.md`. Now: Codex documents 12
   events, and `Interrupt` is the first Codex-only event (PR #40511,
   rust-v0.150.0, 2026-08-26); Claude documents 33 and stays a strict superset
   of the shared 11. Source:
   [Codex Hooks](https://learn.chatgpt.com/docs/hooks) and
   [Claude Code hooks reference](https://code.claude.com/docs/en/hooks).
3. Old claim (this file, 2026-07-25): "Command-type handlers only ... `async`
   is skipped." Now: `mcp_tool` is a recognized and executing Codex handler,
   and `async` command hooks run in the background (max 8 concurrent,
   `SessionEnd` always synchronous). Claude async hooks also run, but their
   stdout and JSON decisions are not honored and the timeout is not enforced.
   The degradation rationale changes from "Codex skips it" to "both hosts
   fire and forget". Source: `codex-rs/config/src/hook_config.rs`,
   `codex-rs/hooks/src/engine/discovery.rs`, and the two hooks references.
4. Old claim (`docs/research/codex-capability-surface.md`, 2026-07-07): the
   Codex command handler default timeout is 1 second with a 3 second maximum.
   Now: the general default is 600 seconds with a 1 second minimum clamp; the
   1 second default and 3 second cap apply only to `SessionEnd` and
   `Interrupt`, with silent clamping plus a warning. Source:
   `normalize_command_hook` in `codex-rs/hooks/src/engine/discovery.rs`.
5. Old claim (this file, 2026-07-08): "`commandWindows` and Claude's `shell`
   field are semantic neighbors", with the mapping deferred. Now: no mapping
   exists; see `## commandWindows ↔ Claude shell field`. Source: both hooks
   references and `external-agent-migration/src/hooks_cla.rs`.
6. Old claim (host research, 2026-07): Codex `PermissionRequest` returns a
   decision in the same shape as Claude. Now: Claude's `decision` is a string
   (`allow` / `deny` / `ask`), while Codex's is an object
   `{behavior, message, interrupt, updatedInput, updatedPermissions}` whose
   last three members fail closed when present. Source: both hooks references.
7. Old claim: `developers.openai.com/codex/hooks` is the citable Codex hooks
   reference. Now: stale; that URL redirects to
   https://learn.chatgpt.com/docs/hooks, which is the canonical hooks URL,
   and `learn.chatgpt.com/docs/codex/hooks` is not a current path. This entry
   is scoped to the hooks page only. The Codex skills citations in
   [`skills.md`](skills.md) were not re-checked on 2026-09-07 and keep their
   own collection dates. Source: the redirect observed on 2026-09-07.
8. Old claim (this file, 2026-07-08): "Edits to the hooks file are picked up
   by a file watcher." Now softened: Claude documents settings changes as
   normally picked up, with a documented miss-and-restart failure mode, so
   this repository promises no take-effect-without-restart behavior on either
   host. Source:
   [Claude Code hooks reference](https://code.claude.com/docs/en/hooks).

## Live verification record

- collected: 2026-09-07
- source: dated live runs on this machine; the full procedure record is kept
  under the untracked `.debug-output/` directory
- status: settled (empirical observation)

Environment: Windows 11 Pro 10.0.26200, Claude Code 2.1.263, codex-cli
0.153.4. Every run used a disposable temp project, or a temporary untracked
`.codex/hooks.json` at the repository root that was removed immediately after
the run and never committed. No user configuration was edited and no fixture
hook was executed.

1. Claude project-settings `SessionStart` and `Stop` hooks fired in a fresh
   `claude -p --setting-sources project` run in a never-trusted, non-git temp
   directory. This refutes the recorded Claude trust gate.
2. `claude --help` (2.1.263): `-p` skips the workspace trust dialog; `--bare`
   skips hooks; `--safe-mode` disables hooks; `--setting-sources` selects the
   layers; `--settings <file-or-json>` loads additional settings.
3. Codex project trust is read from the user config file's `projects` table; a
   `-c projects.'<path>'.trust_level="trusted"` CLI override does not make the
   project `.codex/` layer load (test G, verified against
   `RUST_LOG=codex_core::session=debug`).
4. Untrusted project hooks are silently skipped under `codex exec`, with no
   notice in the `--json` stream (test H); they run with
   `--dangerously-bypass-hook-trust` (test I).
5. All four tested Codex events fired under `codex exec` with the recorded
   stdin envelopes (`SessionStart`, `UserPromptSubmit`, `Stop`, `SessionEnd`);
   `PreToolUse` and `PostToolUse` also fire, with and without a matcher
   (L3, L4).
6. On Windows only the `commandWindows` branch runs on Codex, for all four
   tested events; the `command` branch does not (test J, which declared both
   keys on every handler).
7. The Codex Windows hook shell is pwsh 7.6.5, not cmd.exe (L2, L3); Claude's
   Windows hook shell is bash from Git Bash (`$BASH_VERSION` =
   `5.2.37(1)-release`, and PowerShell syntax produced no file).
8. Plain stdout is injected as context at Codex `SessionStart`;
   `additionalContext` printed by a script file is injected; `systemMessage`
   alone is not model-visible; an inline `cmd /c echo {json}` envelope is
   mangled and not delivered (test K).
9. codex-cli 0.153.4 binary strings confirm `HookStateToml {enabled,
   trusted_hash}`, the handler enum (`command`, `mcp_tool`, `prompt`,
   `agent`), the command fields, the 12-event list including `Interrupt`, and
   the TUI review vocabulary.
10. `codex features list` reports `hooks stable true`.

One run is unexplained: 1 of 7 `codex exec` runs that day fired no hooks at
all, while an exact rerun of the identical tree fired both events twice. Treat
hook execution as observed-but-not-guaranteed and never as a boundary. No
Bridge state, warning, annotation, or report row may be read as a runtime
guarantee that a hook ran or will run.

## Still open

- collected: 2026-09-07
- source: this machine's live evidence gap
- status: watch

- The interactive `/hooks` trust flow has not been exercised here: write a
  hook, confirm it lists as untrusted, trust it through `/hooks`, confirm it
  then runs without the bypass flag, change one identity field, confirm it
  flips to modified, and observe the `[hooks.state."<key>"]` write land in the
  user's `config.toml`. This needs a manual TUI session and cannot be driven
  non-interactively. Until it is done, the three trust entries above rest on
  source and binary reading, and Bridge reads project trust only.
