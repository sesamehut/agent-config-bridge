<!-- bridge:intent 2026-09-07 Seed hook intent document for the unreadable-hook-carrier fixture -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Both entries below target both native carriers. `.codex/hooks.json` is valid
UTF-8 but not valid JSON, so every Codex row falls to H-NOFILE, while the
Claude rows are still evaluated against `.claude/settings.json`. That Claude
carrier parses, yet it repeats the `command` key inside one handler of its
`hooks` value, so the report discloses the carrier without refusing to read it.
The two repeated values differ from each other and from the declared command,
so the row is H-FIELD-DIFF whichever duplicate a reader resolves to. Every
command is the inert `bridge-fixture-noop` program, which exists on no machine.

## hook: guard-tools

- Trigger: before shell tool calls (`PreToolUse`, matcher `Bash`).
- Purpose: show that a Claude row is still evaluated while the Codex carrier is unreadable.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: guard-tools
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
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: the Claude carrier holds no owned group for this entry so the row is H-MISSING
```

## hook: wrap-up

- Trigger: end of a turn (`Stop`, no matcher).
- Purpose: show that a duplicated handler key resolves to the same row under either reading.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: wrap-up
event: Stop
class: observation
enabled: true
command: bridge-fixture-noop wrap-up
timeout: 30
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: the owned Claude handler repeats its command key with two divergent values, so both readings are H-FIELD-DIFF
```
