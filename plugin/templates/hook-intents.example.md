<!-- Example only. Nothing installs this file, and no entry below is a hook of this repository. -->
<!-- bridge:intent 2026-09-07 Example hook intent document rewritten for source-tree/v5 -->
<!-- bridge:hooks-shared-execution 2026-09-07 acknowledged: committed Claude hooks run for every clone without a trust prompt -->

# Hook intents

This is an example `source-tree/v5` hook intent document, not an installation
asset. Bridge installs only the two covenant halves; a project author copies
what is useful here into that project's own `.claude/rules/hooks.md` and owns
the result. In a real document the two `bridge:*` control comments above start
at byte zero, the leading example note is absent, and the explanatory sections
before the first entry are optional commentary.

Hooks committed to a repository run for everyone who clones it, and Bridge
classification is review metadata, not a sandbox. The
`bridge:hooks-shared-execution` record above is required before the first entry
that declares `targets.claude.surface: settings-json`. It is a reviewable
checkpoint in Git, never an enforcement boundary: Claude Code uses hooks from
settings files even in a folder you have not trusted, including under
`claude -p`. An interactive session still holds those hooks until the workspace
trust dialog is accepted; a `-p` or SDK session never shows that dialog. A
teammate who wants out opts out per run with `--bare`, `--safe-mode`,
`--setting-sources user`, or `--settings '{"disableAllHooks": true}'`.

Both entries below are `class: reminder` on `SessionStart`, the one shared event
where both hosts document plain stdout as model-visible context (collected
2026-09-07). A reminder declared on another event still runs, but its text is
not delivered to the model, and the plan says so with the informational
`hook-output-not-delivered` rather than pretending the reminder arrives. A
`gate` or `side-effect` intent is a different question entirely; see the opt-in
section below.

## Portable commands and per-host branches

On the same Windows machine Claude runs `command` under Git Bash (PowerShell
where Git Bash is absent) while Codex runs `commandWindows` under
`pwsh -NoProfile -Command` (collected 2026-09-07, re-checked 2026-10-19),
so a shared `command` has to be a plain program invocation valid in both
shells. `bridge-reminder-session-start` meets that bar: `echo` plus one
double-quoted argument behaves the same way in bash and in PowerShell.
`bridge-reminder-compaction` does not, because `printf` is not a PowerShell
command, so its Codex target carries a `commandWindows` branch and the required
`override-reason: platform-command`. Bridge discloses the split with the
acknowledged warning `platform-branch-divergence`, because Windows and POSIX
then run different code.

Two more portability facts belong to the same decision. Project-scoped Codex
hooks receive no injected environment variables at all, while Claude exports
`${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, and `${CLAUDE_PLUGIN_DATA}`,
so a command naming any path placeholder cannot be one shared string and needs a
per-host `command` with `override-reason: env-placeholder`. And a bare literal
matcher such as `compact` is an exact string on Claude but an unanchored regular
expression on Codex; declare per-host matchers with
`override-reason: matcher-grammar` when that difference is load-bearing.

## Opt-in record for a gate or side-effect entry

Neither entry below needs one. An entry whose `class` is `gate` or
`side-effect` with `enabled: true` is different: Bridge refuses to project it
until the source document itself carries a dated `enabled-by` record, so the
acknowledgement travels with the repository to every clone instead of living in
one person's session. Inside such an entry's YAML block the three fields look
like this:

```yaml
# class: side-effect
# enabled: true
# enabled-by:
#   - date: 2026-09-07
#     note: reviewed the exact command line and accepted repository-wide execution
```

Until a covering record exists the entry stays schema-valid and still emits its
rows. The plan serializes a selected zero-write decision closure with action
`opt-in-or-skip`, annotation `opt-in-required`, and the closure-scoped blocker
warning `hook-opt-in-required`. Confirming the opt-in appends the record through
`closure/hooks/source`, and the next selection projects normally. `class` is
author-declared throughout; Bridge never reads a command string and decides how
dangerous it is.

## hook: bridge-reminder-session-start

- Trigger: session start on both hosts (`SessionStart`, no matcher).
- Purpose: make the source-first rule salient before any configuration work
  begins.
- Command: print one line stating that agent configuration changes land in the
  source tree first.
- Environment: any shell with `echo`; reads nothing, writes nothing, no network.
- Failure policy: best effort. A non-zero exit never blocks the session, and a
  missed reminder never blocks a change.

```yaml
id: bridge-reminder-session-start
event: SessionStart
class: reminder
enabled: true
command: 'echo "bridge: agent configuration changes land in the source tree first; project them in the same unit of work."'
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
    note: rewritten for source-tree/v5 with an explicit reminder class
```

## hook: bridge-reminder-compaction

- Trigger: session start after a compaction, on both hosts (`SessionStart`,
  matcher `compact`).
- Purpose: restate the projection check once the earlier transcript is gone.
- Command: print one line asking for a bridge-sentinel run before committing
  agent configuration changes.
- Environment: a POSIX shell or Git Bash for `command`, PowerShell for the Codex
  Windows branch; reads nothing, writes nothing, no network.
- Failure policy: best effort. A non-zero exit never blocks the session, and the
  two platform branches print the same sentence.

```yaml
id: bridge-reminder-compaction
event: SessionStart
class: reminder
enabled: true
command: 'printf "bridge: verify that projections still match the source before committing.\n"'
matcher: compact
timeout: 5
targets:
  claude:
    surface: settings-json
    tier: native
  codex:
    surface: codex-hooks-json
    tier: native
    commandWindows: 'Write-Output "bridge: verify that projections still match the source before committing."'
    override-reason: platform-command
intent:
  - date: 2026-09-07
    note: Codex Windows branch added; printf is not a PowerShell command
```
