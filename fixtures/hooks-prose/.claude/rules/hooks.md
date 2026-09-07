<!-- bridge:intent 2026-09-07 Seed the prose-surface hook intent document for the degradation fixture -->

# Hook intents

Every entry below lands on a prose surface: `intent-doc` on Claude, or
`agents-md` on Codex. The project carries no `.claude/settings.json`, so no
entry declares `targets.claude.surface: settings-json` and the document needs
no file-level `bridge:hooks-shared-execution` record.

`Interrupt` is the one event proven non-native on Claude, so it is the only
event a Claude `intent-doc` target may use. The four degraded entries use
Claude events outside the `shared-events/2026-09-07` registry, so every row of
those entries carries `event-unverified`.

## hook: doc-interrupt

- Trigger: when the user interrupts a running turn (`Interrupt`, no matcher).
- Purpose: state that an interrupted turn can leave partial edits behind.
- Command: a no-op fixture command that prints the reminder line.
- Environment: any shell; reads nothing, writes nothing, no network.
- Failure policy: best effort; a non-zero exit never blocks the session.

```yaml
id: doc-interrupt
event: Interrupt
class: observation
enabled: true
command: bridge-fixture-noop interrupt-note
targets:
  claude:
    surface: intent-doc
    tier: semantic
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-07
    note: Interrupt is Codex-only, so the Claude half is this document itself
```

## hook: degraded-diff

- Trigger: after the session switches model (`PostModelSwitch`, no matcher).
- Purpose: restate the review rule that depends on the active model.
- Command: a no-op fixture command that prints the reminder line.
- Environment: any shell; reads nothing, writes nothing, no network.
- Failure policy: best effort; a non-zero exit never blocks the session.

```yaml
id: degraded-diff
event: PostModelSwitch
class: reminder
enabled: true
command: bridge-fixture-noop model-switch-note
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: agents-md
    tier: semantic
intent:
  - date: 2026-09-07
    note: the projected block deliberately differs from the renderer output
```

## hook: degraded-missing

- Trigger: while a prompt is being expanded (`UserPromptExpansion`, no matcher).
- Purpose: state that expanded prompt text is still subject to the same rules.
- Command: a no-op fixture command that prints the reminder line.
- Environment: any shell; reads nothing, writes nothing, no network.
- Failure policy: best effort; a non-zero exit never blocks the session.

```yaml
id: degraded-missing
event: UserPromptExpansion
class: observation
enabled: true
command: bridge-fixture-noop prompt-expansion-note
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: agents-md
    tier: semantic
intent:
  - date: 2026-09-07
    note: no block is projected yet so the read side reports the missing block
```

## hook: degraded-native-present

- Trigger: during project setup (`Setup`, no matcher).
- Purpose: state that setup steps belong in the source tree, not in a session.
- Command: a no-op fixture command that prints the reminder line.
- Environment: any shell; reads nothing, writes nothing, no network.
- Failure policy: best effort; a non-zero exit never blocks the session.

```yaml
id: degraded-native-present
event: Setup
class: observation
enabled: true
command: bridge-fixture-noop setup-note
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: agents-md
    tier: semantic
intent:
  - date: 2026-09-07
    note: a hand-written Codex handler occupies the candidate group for this event
```

## hook: degraded-ok

- Trigger: when the host raises a notification (`Notification`, no matcher).
- Purpose: state that a notification never replaces a written status update.
- Command: a no-op fixture command that prints the reminder line.
- Environment: any shell; reads nothing, writes nothing, no network.
- Failure policy: best effort; a non-zero exit never blocks the session.

```yaml
id: degraded-ok
event: Notification
class: observation
enabled: true
command: bridge-fixture-noop notification-note
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: agents-md
    tier: semantic
intent:
  - date: 2026-09-07
    note: the projected block is byte-equal to the hd1 renderer output
```
