<!-- bridge:intent 2026-09-07 Seed hook intent document for the foreign hook handler fixture -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Every command below is the inert fixture no-op `bridge-fixture-noop <token>`, a
program that exists on no machine, so an accidental run is a harmless ENOENT.
The fence is binding on this fixture; see `.claude/rules/fixtures.md`.

Each entry below is converged on its declared surfaces except for one host key
outside the declared schema, so the carrier bytes alone decide whether the row
is in-sync, drift, or degraded.

## hook: foreign-mcp

- Trigger: before shell tool calls on both hosts (`PreToolUse`, matcher `Bash`).
- Purpose: note shell calls before they run.
- Command: run the inert fixture no-op `bridge-fixture-noop shell-observe`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; a non-zero exit must not block the tool call.

```yaml
id: foreign-mcp
event: PreToolUse
class: observation
enabled: true
command: bridge-fixture-noop shell-observe
matcher: Bash
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: a hand-written mcp_tool handler shares the owned Claude group
```

## hook: semantics-async

- Trigger: after file-writing tools run (`PostToolUse`, matcher `Write`).
- Purpose: note completed writes.
- Command: run the inert fixture no-op `bridge-fixture-noop write-observe`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; a non-zero exit must not block the session.

```yaml
id: semantics-async
event: PostToolUse
class: observation
enabled: true
command: bridge-fixture-noop write-observe
matcher: Write
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
    note: the Claude handler was hand-edited to async, which changes semantics
```

## hook: prompt-note

- Trigger: every submitted prompt on both hosts (`UserPromptSubmit`, no
  matcher).
- Purpose: restate the source-first rule where stdout still reaches the model.
- Command: run the inert fixture no-op `bridge-fixture-noop prompt-note`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; a missed reminder never blocks a change.

```yaml
id: prompt-note
event: UserPromptSubmit
class: reminder
enabled: true
command: bridge-fixture-noop prompt-note
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
intent:
  - date: 2026-09-07
    note: carries a Claude passthrough key and an unknown Codex handler key
```

## hook: session-note

- Trigger: session startup on Claude (`SessionStart`, matcher `startup`).
- Purpose: keep one fully converged Claude control row with no host extras.
- Command: run the inert fixture no-op `bridge-fixture-noop session-note`.
- Environment: none; the fixture command runs nowhere and reads nothing.
- Failure policy: best-effort; a missed reminder never blocks a change.

```yaml
id: session-note
event: SessionStart
class: reminder
enabled: true
command: bridge-fixture-noop session-note
matcher: startup
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
intent:
  - date: 2026-09-07
    note: Codex declared unsynced so the control row has no counterpart
```
