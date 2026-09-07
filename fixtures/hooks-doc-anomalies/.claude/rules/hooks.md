<!-- bridge:intent 2026-09-07 Seed the deliberately invalid hook intent document for the anomaly fixture -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

Every entry below is a deliberate `source-tree/v5` schema violation, except
`opt-in-pending`. That last entry is schema-valid: `enabled-by-missing` is a
non-invalidating lint, so the entry keeps both of its unit rows and the read
side annotates them `opt-in-required` instead of emitting an anomaly line. It
also carries the advisory `matcher-grammar-divergent`, and it meets every
clause of that closed predicate: its shared `matcher` is `Write,Edit`, a
string inside the Claude list class that contains a comma; both targets
declare a host-executed JSON surface, `settings-json` on Claude and
`codex-hooks-json` on Codex; and neither target overrides `matcher`. Claude
reads those bytes as a list of two exact tool names while Codex compiles the
same bytes as one unanchored regular expression, which no tool name matches.
A bare literal such as `Bash` never raises the advisory, so the comma form is
what this entry declares.

No carrier exists in this project. `.claude/settings.json` and
`.codex/hooks.json` are both absent on purpose, so a surviving row reports the
absent carrier through H-NOFILE and no carrier observation can mask an
`intent-doc-anomaly` line.

The fenced block below belongs to no entry. It sits before the first
`## hook:` heading, where the closed grammar admits no fenced `yaml` block at
all, so it is a `yaml-block-count` violation. `inspect-hook-intents` scans the
preamble and reports that anomaly itself, carrying the line of the opening
fence and no entry id, so the read side prints one `intent-doc-anomaly` line
whose detail is `(line <n>)` and the scanner never disagrees with the agent
that validates the rest of the v5 schema.

```yaml
id: preamble-stray
event: PreToolUse
class: observation
enabled: false
command: bridge-fixture-noop stray-block
```

## hook: missing-bullet

- Trigger: after a file-writing tool call (`PostToolUse`).
- Purpose: exercise the missing prose bullet lint.
- Command: none; both targets are declared unsynced.
- Environment: none; this entry projects nothing.

```yaml
id: missing-bullet
event: PostToolUse
class: observation
enabled: false
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: two-yaml-blocks

- Trigger: before a shell tool call (`PreToolUse`, matcher `Bash`).
- Purpose: exercise the single fenced block rule.
- Command: a no-op fixture command.
- Environment: none; this entry never reaches a carrier.
- Failure policy: not applicable; the entry is invalid by construction.

```yaml
id: two-yaml-blocks
event: PreToolUse
class: observation
enabled: false
command: bridge-fixture-noop two-blocks
matcher: Bash
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: none
    tier: declared-unsynced
```

```yaml
id: two-yaml-blocks
event: PreToolUse
class: observation
enabled: false
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: duplicate-id

- Trigger: before a compaction (`PreCompact`).
- Purpose: exercise the duplicate id lint, first occurrence.
- Command: none; both targets are declared unsynced.
- Environment: none; this entry projects nothing.
- Failure policy: not applicable; the entry is invalid by construction.

```yaml
id: duplicate-id
event: PreCompact
class: observation
enabled: false
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: duplicate-id

- Trigger: after a compaction (`PostCompact`).
- Purpose: exercise the duplicate id lint, second occurrence.
- Command: none; both targets are declared unsynced.
- Environment: none; this entry projects nothing.
- Failure policy: not applicable; the entry is invalid by construction.

```yaml
id: duplicate-id
event: PostCompact
class: observation
enabled: false
targets:
  claude:
    surface: none
    tier: declared-unsynced
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: dup-own-a

- Trigger: after a file-writing tool call (`PostToolUse`, matcher `Write`).
- Purpose: exercise the duplicate ownership lint, first claimant.
- Command: a no-op fixture command.
- Environment: any shell; reads nothing and writes nothing.
- Failure policy: not applicable; the entry is invalid by construction.

```yaml
id: dup-own-a
event: PostToolUse
class: observation
enabled: true
command: bridge-fixture-noop dup-own-a
matcher: Write
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: dup-own-b

- Trigger: after a file-writing tool call (`PostToolUse`, matcher `Write`).
- Purpose: exercise the duplicate ownership lint, second claimant.
- Command: a no-op fixture command.
- Environment: any shell; reads nothing and writes nothing.
- Failure policy: not applicable; the entry is invalid by construction.

```yaml
id: dup-own-b
event: PostToolUse
class: observation
enabled: true
command: bridge-fixture-noop dup-own-b
matcher: Write
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: override-no-reason

- Trigger: before a file-reading tool call (`PreToolUse`, Claude matcher `Read`).
- Purpose: exercise the override without reason lint.
- Command: a no-op fixture command.
- Environment: any shell; reads nothing and writes nothing.
- Failure policy: not applicable; the entry is invalid by construction.

```yaml
id: override-no-reason
event: PreToolUse
class: observation
enabled: true
command: bridge-fixture-noop override
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
    matcher: Read
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: interrupt-native

- Trigger: when the user interrupts a running turn (`Interrupt`, no matcher).
- Purpose: exercise the unsupported native tier lint on Claude.
- Command: a no-op fixture command.
- Environment: any shell; reads nothing and writes nothing.
- Failure policy: not applicable; the entry is invalid by construction.

```yaml
id: interrupt-native
event: Interrupt
class: observation
enabled: true
command: bridge-fixture-noop interrupt
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: none
    tier: declared-unsynced
```

## hook: opt-in-pending

- Trigger: before a write tool call (`PreToolUse`, matcher `Write,Edit`).
- Purpose: hold a side-effect intent until a dated opt-in record exists.
- Command: a no-op fixture command.
- Environment: any shell; reads nothing and writes nothing.
- Failure policy: best effort; a non-zero exit never blocks the session.

```yaml
id: opt-in-pending
event: PreToolUse
class: side-effect
enabled: true
command: bridge-fixture-noop opt-in
matcher: Write,Edit
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
    note: declared without an enabled-by record so both rows carry opt-in-required
```
