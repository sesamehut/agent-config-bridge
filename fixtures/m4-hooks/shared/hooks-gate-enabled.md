<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: repo-guard

- Trigger: before a shell tool call (`PreToolUse`, matcher `^(Bash)$`).
- Purpose: refuse a shell call that the project has not reviewed.
- Command: run the inert fixture no-op that stands in for the guard program.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: fail closed. A non-zero exit is a refusal, never a warning.

```yaml
id: repo-guard
event: PreToolUse
class: gate
enabled: true
command: bridge-fixture-noop repo-guard
matcher: ^(Bash)$
timeout: 30
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
    note: class gate declared so a blocked carrier forces the sibling to zero writes
```
