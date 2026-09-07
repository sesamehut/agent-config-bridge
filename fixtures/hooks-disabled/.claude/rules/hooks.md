<!-- bridge:intent 2026-09-07 Seed hook intent document for the disabled-hook fixture -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Both entries below declare `enabled: false` and target `.claude/settings.json`,
so they sit side by side as the two disabled cases: `retired-guard` still has a
command handler in its owned group, while `retired-note` has none. The project
settings file also sets `disableAllHooks`, and a tracked
`.claude/settings.local.json` carries its own `hooks` key; both are disclosure
only and neither is a row state. Every command is the inert
`bridge-fixture-noop` program, which exists on no machine.

## hook: retired-guard

- Trigger: before shell tool calls (`PreToolUse`, matcher `Bash`).
- Purpose: exercise the H-DISABLED-PRESENT branch of the hooks decision table.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: retired-guard
event: PreToolUse
class: observation
enabled: false
command: bridge-fixture-noop retired-guard
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
    note: disabled while the owned Claude group still holds a command handler
```

## hook: retired-note

- Trigger: on every user prompt (`UserPromptSubmit`, no matcher).
- Purpose: exercise the H-DISABLED-OK branch of the hooks decision table.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: retired-note
event: UserPromptSubmit
class: observation
enabled: false
command: bridge-fixture-noop retired-note
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
    note: disabled with no owned handler left, so the absence is vacuously consistent
```
