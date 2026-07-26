<!-- bridge:intent 2026-07-08 Seed hook intent document for the onboarded fixture -->

# Hook intents

## hook: fmt-on-save

- Trigger: after file-writing tools run (`PostToolUse`, matcher `Write|Edit`).
- Purpose: surface formatting-relevant changes right after edits.
- Command: print a short diff stat of the working tree.
- Environment: requires git in PATH; read-only.
- Failure policy: best-effort; non-zero exit must not block the session.

```yaml
id: fmt-on-save
event: PostToolUse
matcher: Write|Edit
command: git diff --stat
timeout: 10
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
    note: declared but deliberately not projected, to exercise reproject-from-source
```

## hook: sandbox-guard

- Trigger: before shell tool calls (`PreToolUse`, matcher `Bash`).
- Purpose: cheap pre-flight sanity check before shell execution.
- Command: verify the session is inside a git work tree.
- Environment: requires git in PATH; read-only.
- Failure policy: best-effort on Claude. On Codex this intent is declared
  not-synced: enforcement would need `permissionDecision: "ask"`, which is
  unimplemented, and prose simulation would fake an enforcement boundary.

```yaml
id: sandbox-guard
event: PreToolUse
matcher: Bash
command: git rev-parse --is-inside-work-tree
timeout: 5
enabled: true
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
```

## hook: sentinel-stop

- Trigger: end of a turn (`Stop`, no matcher).
- Purpose: make pending changes visible at wrap-up.
- Command: print the short working-tree status.
- Environment: requires git in PATH; read-only.
- Failure policy: best-effort; non-zero exit must not block the session.

```yaml
id: sentinel-stop
event: Stop
command: git status --short
timeout: 30
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
    note: initial declaration
```
