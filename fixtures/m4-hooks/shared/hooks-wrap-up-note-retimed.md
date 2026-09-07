<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: wrap-up-note

- Trigger: at the end of a session (`SessionEnd`, no matcher).
- Purpose: print the one-line wrap-up note the project asks reviewers to read.
- Command: run the inert fixture no-op that stands in for the wrap-up printer.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: best effort. A non-zero exit never blocks the session.

```yaml
id: wrap-up-note
event: SessionEnd
class: observation
enabled: true
command: bridge-fixture-noop wrap-up-note
timeout: 30
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
    timeout: 3
    override-reason: timeout-cap
intent:
  - date: 2026-09-07
    note: initial declaration; Codex clamps SessionEnd to one to three seconds
  - date: 2026-09-07
    note: Codex timeout raised to three seconds, which changes the trust identity
```
