<!-- bridge:intent 2026-09-07 Seed hook intent document for the inline Codex hooks fixture -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Every command below is the inert fixture no-op `bridge-fixture-noop <token>`, a
program that exists on no machine, so an accidental run is a harmless ENOENT.
The fence is binding on this fixture; see `.claude/rules/fixtures.md`.

## hook: stop-note

- Trigger: end of a turn on both hosts (`Stop`, no matcher).
- Purpose: keep one converged native hook beside an inline Codex hooks table.
- Command: run the inert fixture no-op `bridge-fixture-noop stop-note`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; a non-zero exit must not block the session.

```yaml
id: stop-note
event: Stop
class: observation
enabled: true
command: bridge-fixture-noop stop-note
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
    note: converged on both carriers, so the inline table is the only anomaly
```
