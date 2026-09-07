<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: shell-preview

- Trigger: before a shell tool call (`PreToolUse`, matcher `^(Bash)$`).
- Purpose: show the reviewed command line before the shell call runs.
- Command: run the inert fixture no-op that stands in for the preview program.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: best effort. A non-zero exit never blocks the session.

```yaml
id: shell-preview
event: PreToolUse
class: observation
enabled: true
command: bridge-fixture-noop shell-preview-v2
matcher: ^(Bash)$
timeout: 20
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: initial declaration for the M4 two-sided projection fixtures
  - date: 2026-09-07
    note: command updated; the host passthrough keys must survive in place
```
