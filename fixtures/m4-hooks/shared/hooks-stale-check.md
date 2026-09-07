<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: stale-check

- Trigger: after a file-writing tool call completes (`PostToolUse`, no matcher).
- Purpose: report whether the projected carriers still match their source.
- Command: run the inert fixture no-op that stands in for the staleness check.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: best effort. A non-zero exit never blocks the session.

```yaml
id: stale-check
event: PostToolUse
class: observation
enabled: true
command: bridge-fixture-noop stale-check
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
    note: initial declaration for the managed-deletion fixture
```
