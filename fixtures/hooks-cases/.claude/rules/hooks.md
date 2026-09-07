<!-- bridge:intent 2026-09-07 Seed hook intent document for the hook decision-table fixture -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Every entry below targets the Claude carrier `.claude/settings.json` so one
entry reaches exactly one `report/v5` hooks case, and `ok-both` also targets
`.codex/hooks.json` as the two-host control. Every command is the inert
`bridge-fixture-noop` program, which exists on no machine.

## hook: extra-keys

- Trigger: before shell tool calls (`PreToolUse`, matcher `Bash`).
- Purpose: exercise the H-EXTRA-KEYS branch of the hooks decision table.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: extra-keys
event: PreToolUse
class: observation
enabled: true
command: bridge-fixture-noop guard
matcher: Bash
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-07
    note: the owned Claude handler carries an unknown key so the row is H-EXTRA-KEYS
```

## hook: field-absent

- Trigger: after file-writing tool calls (`PostToolUse`, matcher `Write`).
- Purpose: exercise the H-FIELD-ABSENT branch of the hooks decision table.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: field-absent
event: PostToolUse
class: observation
enabled: true
command: bridge-fixture-noop post-write
matcher: Write
timeout: 15
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-07
    note: the owned Claude handler omits the declared timeout so the row is H-FIELD-ABSENT
```

## hook: field-diff

- Trigger: before a compaction (`PreCompact`, no matcher).
- Purpose: exercise the H-FIELD-DIFF branch of the hooks decision table.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: field-diff
event: PreCompact
class: observation
enabled: true
command: bridge-fixture-noop pre-compact
timeout: 20
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-07
    note: the owned Claude handler carries a different command so the row is H-FIELD-DIFF
```

## hook: multi-handler

- Trigger: when a subagent stops (`SubagentStop`, no matcher).
- Purpose: exercise the H-MULTI branch of the hooks decision table.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: multi-handler
event: SubagentStop
class: observation
enabled: true
command: bridge-fixture-noop subagent-note
timeout: 10
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-07
    note: the owned Claude group holds two command handlers so the row is H-MULTI
```

## hook: ok-both

- Trigger: session start (`SessionStart`, matcher `startup`).
- Purpose: hold the H-OK control row on both hosts.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: ok-both
event: SessionStart
class: reminder
enabled: true
command: bridge-fixture-noop session-note
matcher: startup
timeout: 10
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: both carriers already match so this entry is the converged control
```
