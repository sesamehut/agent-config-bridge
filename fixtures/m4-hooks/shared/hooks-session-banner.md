<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: session-banner

- Trigger: at the start of a session (`SessionStart`, no matcher).
- Purpose: print the project's one-line configuration reminder at session start.
- Command: run the inert fixture no-op that stands in for the banner printer.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: best effort. A non-zero exit never blocks the session.

```yaml
id: session-banner
event: SessionStart
class: reminder
enabled: true
command: bridge-fixture-noop session-banner
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
    commandWindows: bridge-fixture-noop session-banner-windows
    override-reason: platform-command
intent:
  - date: 2026-09-07
    note: initial declaration with a Codex Windows command branch
```
