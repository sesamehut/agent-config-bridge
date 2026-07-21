# Bridge covenant hook intents

Reminder hooks for the bridge covenant. Both entries are low-side-effect
(print-only). High-side-effect hooks require explicit opt-in and are never
part of the covenant defaults.

## hook: bridge-reminder-session-start

- Trigger: session start, both hosts (`SessionStart`).
- Purpose: make the covenant salient before any configuration work happens.
- Command: print a one-line reminder that config changes land in the source
  tree first and projections update in the same unit of work.
- Environment: any shell with `echo`; read-only; no network.
- Failure policy: best-effort; non-zero exit must never block the session.
  Stdout visibility varies by host and event; delivery is verified at
  install time.

```yaml
id: bridge-reminder-session-start
event: SessionStart
command: 'echo "bridge: project agent-config changes go to the source tree first; update projections in the same unit of work."'
timeout: 5
enabled: true
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-07-08
    note: initial covenant reminder draft
```

## hook: bridge-reminder-stop

- Trigger: end of a turn / session wrap-up, both hosts (`Stop`).
- Purpose: wrap-up self-check — if agent configuration changed, verify
  projections before committing.
- Command: print a one-line reminder to run the bridge-sentinel skill when
  agent configuration changed this session.
- Environment: any shell with `echo`; read-only; no network.
- Failure policy: best-effort; non-zero exit must never block the session.
  Stdout visibility varies by host and event; delivery is verified at
  install time.

```yaml
id: bridge-reminder-stop
event: Stop
command: 'echo "bridge: if agent configuration changed this session, verify projections match the source (run bridge-sentinel) before committing."'
timeout: 5
enabled: true
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-07-08
    note: initial covenant reminder draft
```
