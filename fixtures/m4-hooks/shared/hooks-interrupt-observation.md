<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->

# Hook intents

## hook: interrupt-note

- Trigger: when the user interrupts the model (`Interrupt`, no matcher).
- Purpose: record that the interrupted step may have left work unfinished.
- Command: run the inert fixture no-op that stands in for the note writer.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: best effort. A non-zero exit never blocks the session.

```yaml
id: interrupt-note
event: Interrupt
class: observation
enabled: true
command: bridge-fixture-noop interrupt-note
timeout: 2
targets:
  claude:
    surface: intent-doc
    tier: semantic
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: Claude has no Interrupt event, so this document itself is the carrier
```
