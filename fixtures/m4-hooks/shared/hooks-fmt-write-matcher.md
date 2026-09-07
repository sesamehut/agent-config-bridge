<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: fmt-on-save

- Trigger: after a write-shaped tool call (`PostToolUse`, matcher `^(Write)$`).
- Purpose: make formatting-relevant changes visible right after an edit.
- Command: run the inert fixture no-op that stands in for a formatter report.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: best effort. A non-zero exit never blocks the session.

```yaml
id: fmt-on-save
event: PostToolUse
class: observation
enabled: true
command: bridge-fixture-noop fmt-on-save-v2
matcher: ^(Write)$
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
    note: initial declaration for the M4 two-sided projection fixtures
  - date: 2026-09-07
    note: command updated so the Claude carrier needs a guarded replacement
```
