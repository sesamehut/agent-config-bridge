<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: journal-writer

- Trigger: at the end of a session (`SessionEnd`, no matcher).
- Purpose: write the session's configuration summary into the project journal.
- Command: run the inert fixture no-op that stands in for the journal writer.
- Environment: no variables are read; a real command would write one file.
- Failure policy: best effort. A non-zero exit never blocks the session.

```yaml
id: journal-writer
event: SessionEnd
class: side-effect
enabled: true
command: bridge-fixture-noop journal-writer
timeout: 3
enabled-by:
  - date: 2026-09-07
    note: reviewed the exact command line and accepted repository-wide execution
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: declared without an opt-in record so the plan must ask before projecting
  - date: 2026-09-07
    note: opt-in confirmed; the dated enabled-by record was appended by this plan
```
