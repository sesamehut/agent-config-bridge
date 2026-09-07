<!-- bridge:intent 2026-07-08 Seed hook intent document for the onboarded fixture -->
<!-- bridge:intent 2026-09-07 source-tree/v5 rewrite: classes, opt-in record, inert fixture commands -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Every command below is the inert fixture no-op `bridge-fixture-noop <token>`, a
program that exists on no machine, so an accidental run is a harmless ENOENT.
The fence is binding on this fixture; see the Bridge repository rule
`.claude/rules/fixtures.md`, which lives outside this fixture project.

## hook: fmt-on-save

- Trigger: after file-writing tools run (`PostToolUse`, matcher `Write|Edit`).
- Purpose: surface formatting-relevant changes right after edits.
- Command: run the inert fixture no-op `bridge-fixture-noop fmt-on-save`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; non-zero exit must not block the session.

```yaml
id: fmt-on-save
event: PostToolUse
class: observation
enabled: true
command: bridge-fixture-noop fmt-on-save
matcher: Write|Edit
timeout: 10
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-07-08
    note: declared but deliberately not projected, to exercise reproject-from-source
  - date: 2026-09-07
    note: class observation added; the command now uses the inert fixture fence
```

## hook: sandbox-guard

- Trigger: before shell tool calls (`PreToolUse`, matcher `Bash`).
- Purpose: cheap pre-flight sanity check before shell execution.
- Command: run the inert fixture no-op `bridge-fixture-noop sandbox-guard`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort on Claude. On Codex this intent is declared
  not-synced: enforcement would need `permissionDecision: "ask"`, which is
  unimplemented, and prose simulation would fake an enforcement boundary.

```yaml
id: sandbox-guard
event: PreToolUse
class: gate
enabled: true
command: bridge-fixture-noop sandbox-guard
matcher: Bash
timeout: 5
enabled-by:
  - date: 2026-09-07
    note: reviewed the exact inert command line and accepted repository-wide execution
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-07-08
    note: tier-4 on codex to exercise declared-unsynced
  - date: 2026-09-07
    note: class gate with a dated enabled-by record, so no opt-in stays pending
```

## hook: sentinel-stop

- Trigger: end of a turn (`Stop`, no matcher).
- Purpose: make pending changes visible at wrap-up.
- Command: run the inert fixture no-op `bridge-fixture-noop sentinel-stop`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; non-zero exit must not block the session.

```yaml
id: sentinel-stop
event: Stop
class: reminder
enabled: true
command: bridge-fixture-noop sentinel-stop
timeout: 30
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-07-08
    note: initial declaration
  - date: 2026-09-07
    note: class reminder kept on Stop, which covers hook-output-not-delivered
```
