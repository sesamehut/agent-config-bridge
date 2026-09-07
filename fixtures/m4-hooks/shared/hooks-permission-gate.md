<!-- bridge:intent 2026-09-07 Seed hook intent document for the M4 write-side fixtures -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

## hook: permission-gate

- Trigger: when the host asks for a permission decision (`PermissionRequest`).
- Purpose: apply the project's own answer to a repeated permission question.
- Command: run the inert fixture no-op that stands in for the decision program.
- Environment: no variables are read, nothing is written, no network access.
- Failure policy: fail closed. An unusable answer must leave the host asking.

```yaml
id: permission-gate
event: PermissionRequest
class: gate
enabled: true
command: bridge-fixture-noop permission-gate
timeout: 15
enabled-by:
  - date: 2026-09-07
    note: reviewed the exact command line and accepted repository-wide execution
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-07
    note: the two hosts decide permissions differently, so Codex stays unsynced
```
