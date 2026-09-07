<!-- bridge:intent 2026-09-08 Seed hook intent document for the unmodelled-hook-carrier fixture -->
<!-- bridge:hooks-shared-execution 2026-09-08 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Both entries below target the Claude carrier `.claude/settings.json` and
declare `surface: none` on Codex, so this project needs no `.codex/hooks.json`.
The Claude carrier is valid JSON, yet its `Stop` member holds an object where
the closed hooks shape allows only an array of matcher groups. That node is
outside the model, so the carrier is disclosed as
`hooks-carrier-unmodelled (unmodelled-shape)` while the sentinel still applies
the hooks decision table to what it can read: `session-note` keeps its readable
owned group and stays H-OK, and `wrap-up` finds no readable owned group at all
and falls to H-MISSING. Read-side disclosure never becomes a refusal; only the
write side fails closed on the same condition. Every command is the inert
`bridge-fixture-noop` program, which exists on no machine.

## hook: session-note

- Trigger: session start (`SessionStart`, matcher `startup`).
- Purpose: show that a readable owned group is still compared beside an unmodelled node.
- Command: run the inert fixture no-op program.
- Environment: none; the program exists on no machine and always fails to start.
- Failure policy: best effort; the fixture never runs this command.

```yaml
id: session-note
event: SessionStart
class: observation
enabled: true
command: bridge-fixture-noop session-note
matcher: startup
timeout: 10
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-08
    note: this group is a well-formed array so the row stays H-OK despite the carrier disclosure
```

## hook: wrap-up

- Trigger: end of a turn (`Stop`, no matcher).
- Purpose: show the row an entry gets when its owned group sits inside the unmodelled node.
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
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-08
    note: the Stop member is an object rather than an array so no owned group is readable and the row is H-MISSING
```
