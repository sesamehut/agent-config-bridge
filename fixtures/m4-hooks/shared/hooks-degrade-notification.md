<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: notify-reminder

- Trigger: when the host raises a notification (`Notification`, no matcher).
- Purpose: restate that agent configuration changes land in the source first.
- Command: run the inert fixture no-op that stands in for the reminder printer.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: best effort. A missed reminder never blocks a change.

```yaml
id: notify-reminder
event: Notification
class: reminder
enabled: true
command: bridge-fixture-noop notify-reminder
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: agents-md
    tier: semantic
intent:
  - date: 2026-09-07
    note: Codex has no Notification carrier, so the intent degrades to prose
```
