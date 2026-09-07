<!-- bridge:intent 2026-09-07 Seed hook intent document for the legacy Codex hooks pointer fixture -->

# Hook intents

Every command below is the inert fixture no-op `bridge-fixture-noop <token>`, a
program that exists on no machine, so an accidental run is a harmless ENOENT.
No entry declares a `settings-json` Claude surface, so this document carries no
`bridge:hooks-shared-execution` acknowledgement.

## hook: pointer-note

- Trigger: session startup on Codex (`SessionStart`, matcher `startup`).
- Purpose: keep one converged Codex hook beside a legacy inline hooks pointer.
- Command: run the inert fixture no-op `bridge-fixture-noop pointer-note`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; a non-zero exit must not block the session.

```yaml
id: pointer-note
event: SessionStart
class: reminder
enabled: true
command: bridge-fixture-noop pointer-note
matcher: startup
timeout: 5
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: Codex-only declaration, so the project needs no Claude hooks carrier
```
