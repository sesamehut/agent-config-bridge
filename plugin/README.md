# Agent Config Bridge (plugin payload)

<!-- GENERATED FILE. Assembled by scripts/package_plugin.py in the upstream
     repository https://github.com/sesamehut/agent-config-bridge from an explicit allowlist of audited files.
     Do not edit anything under plugin/: edit the upstream sources and rebuild. -->

Version: **0.1.0**

This directory is the installable plugin for both Claude Code and Codex. It is
a generated boundary artifact: `scripts/package_plugin.py build` assembles it
from the upstream `skills/`, `templates/`, `knowledge/`, and `scripts/`
sources, applies a secret scan, and `scripts/package_plugin.py verify` fails
whenever the committed bytes drift from what the allowlist produces. Change
behavior upstream and rebuild; never hand-edit files here.

## What you get

- `skills/bridge-sentinel/` - a read-only sentinel that reports drift between
  a project's canonical agent configuration and its Claude Code / Codex
  projections. It never writes.
- `skills/bridge-sync/` - the write side: it plans, asks for confirmation,
  then projects, adopts, or reconciles project skills, entry instructions,
  rule shards, and hook intents, writing only inside managed regions with
  Git-proven baselines.
- `templates/covenant/` - the exact covenant bytes the skills install into a
  project (current `covenant/v3` plus the archived v1 / v2 migration
  evidence), and `templates/hook-intents.example.md`, an example document that
  nothing installs.
- `knowledge/` - the dated host fact base about Claude Code and Codex that the
  skills cite as evidence.
- `scripts/bridge_doctor.py` - an offline preflight (see below).

Skill names after installation:

| Host | Sentinel | Sync |
| --- | --- | --- |
| Claude Code | `/agent-config-bridge:bridge-sentinel` | `/agent-config-bridge:bridge-sync` |
| Codex | `$agent-config-bridge:bridge-sentinel` | `$agent-config-bridge:bridge-sync` |

## Prerequisites

- Git on `PATH`, and a Git worktree for the project you want to bridge.
- Python 3.9 or newer. The skills probe `python3`, then `python`, then
  `py -3`, and use the first real interpreter they find; use the same name
  below. No Node.js and no npm packages are needed.
- Verified against Claude Code 2.1.263 and codex-cli 0.153.4 (checked 2026-09-08). Other versions may work but were not checked.

The skills run their own preflight (Git, interpreter, mechanics self-test)
before doing anything. For manual troubleshooting, the same checks are
available as a script that writes nothing and needs no network:

```text
python3 <plugin-root>/scripts/bridge_doctor.py          # Unix-like
python  <plugin-root>\scripts\bridge_doctor.py          # Windows
python3 <plugin-root>/scripts/bridge_doctor.py --json
```

`<plugin-root>` is this directory: `./plugin` in a checkout, or the installed
copy, which lives at
`~/.claude/plugins/cache/agent-config-bridge/agent-config-bridge/0.1.0/` on Claude Code and
`~/.codex/plugins/cache/agent-config-bridge/agent-config-bridge/0.1.0/` on Codex. The doctor
checks the interpreter version, Git, the payload layout, manifest agreement,
and runs the sentinel mechanics self-test.

## Install on Claude Code

Try it from a checkout without installing anything:

```text
claude --plugin-dir ./plugin
```

Install through the repository's own marketplace, from a local checkout or
from GitHub:

```text
claude plugin marketplace add ./                     # local checkout, run at the repository root
claude plugin marketplace add sesamehut/agent-config-bridge#<ref>   # or from GitHub
claude plugin install agent-config-bridge@agent-config-bridge
```

The GitHub form needs a `<ref>` (branch or tag) that carries `plugin/` and
`.claude-plugin/marketplace.json`; without `#<ref>` it takes the default
branch. The shorthand clones over SSH unless `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`
is set. Then restart Claude Code or run `/reload-plugins`.

Third-party marketplaces do not auto-update, and a plugin only updates when
its declared version changes. Update with
`claude plugin marketplace update agent-config-bridge` followed by
`claude plugin update agent-config-bridge`; remove with
`claude plugin uninstall agent-config-bridge@agent-config-bridge` and
`claude plugin marketplace remove agent-config-bridge`.

What these commands write: `marketplace add` records the marketplace in
`~/.claude/plugins/known_marketplaces.json`; the GitHub form also clones the
whole upstream repository (including its docs and its inert fixture projects)
under `~/.claude/plugins/marketplaces/agent-config-bridge/`, and you should never start a
Claude Code or Codex session inside that clone. `install` writes `enabledPlugins` into your user
settings by default; `--scope project` writes it into the current
repository's `.claude/settings.json` instead. It copies only this directory
into `~/.claude/plugins/cache/`. `--plugin-dir` writes none of that.

Permissions: both skills declare `allowed-tools: Read`, so they can read
their own bundled references, templates, and knowledge from the plugin cache
outside your project without a prompt (your own deny rules still apply).
Running the bundled Python script goes through the normal Bash permission
prompt in interactive sessions. Non-interactive `claude -p` runs deny what has
not been pre-approved, so pass an `--allowedTools` rule for that invocation.

## Install on Codex

Codex installs plugins only from a marketplace. This repository is its own
single-plugin marketplace (`.claude-plugin/marketplace.json` at the repository
root, which Codex reads as well), so register it first:

```text
codex plugin marketplace add <absolute path to the repository root>   # local checkout
codex plugin marketplace add sesamehut/agent-config-bridge --ref <ref>   # or from GitHub
codex plugin add agent-config-bridge@agent-config-bridge
```

The GitHub form needs a `<ref>` that carries `plugin/` and the marketplace
manifest; without `--ref` it takes the default branch. Start a new Codex
session afterwards; skills are loaded at session start. Update a GitHub
marketplace with `codex plugin marketplace upgrade agent-config-bridge` and run
`codex plugin add agent-config-bridge@agent-config-bridge` again; a local marketplace is read live,
but the plugin copy only refreshes when you run `codex plugin add` again.
Remove with `codex plugin remove agent-config-bridge@agent-config-bridge` and
`codex plugin marketplace remove agent-config-bridge`.

What these commands write: `marketplace add` writes a `[marketplaces.agent-config-bridge]`
table into `~/.codex/config.toml` (a GitHub source also keeps a full clone of
the upstream repository under `~/.codex/.tmp/marketplaces/`; never start a
session inside it); `plugin add` writes
`[plugins."agent-config-bridge@agent-config-bridge"] enabled = true` there and copies this directory
into `~/.codex/plugins/cache/`. Neither command asks for confirmation. Codex
refuses to re-point an existing marketplace name at a different source, so
remove the marketplace before switching between a local checkout and GitHub.

## Safety boundaries

- `bridge-sentinel` never writes. `bridge-sync` writes only after you confirm
  a complete plan, only inside Bridge-managed regions, and never overwrites
  unmanaged or hand-written host files. Claude Code cannot disable a single
  plugin skill: to keep only the sentinel there, disable or remove the whole
  plugin (`claude plugin disable`).
- This plugin ships no hooks, no MCP servers, and no apps. Nothing runs at
  install time.
- Under Codex's default sandbox, a `bridge-sync` write into a project's
  `.codex/` or `.agents/` directory needs your approval, because those
  directories are read-only carve-outs there.
- Hooks that `bridge-sync` projects into a project's `.claude/settings.json`
  or `.codex/hooks.json` are committed to that repository and run for everyone
  who clones it. Bridge's hook classification is review metadata, not a
  sandbox. Codex additionally requires each project hook to be trusted in
  `/hooks` before it runs, and Bridge never edits host configuration outside
  the repository.
- Claude Code's own warning applies to every plugin: plugins and marketplaces
  can execute code with your user privileges, so install only from sources you
  trust.
- Both hosts copy this directory into a per-version cache and replace it on
  update. Nothing should ever be stored inside it.

## Layout

```text
.claude-plugin/plugin.json   Claude Code manifest
.codex-plugin/plugin.json    Codex manifest
.gitattributes               LF checkout for every text file
README.md                    this file
scripts/bridge_doctor.py     offline preflight
skills/                      bridge-sentinel and bridge-sync
templates/                   covenant bytes and the hook intent example
knowledge/                   dated host fact base
```

Design documents live upstream under `docs/` (written in Chinese); links from
`knowledge/` into `docs/` point at https://github.com/sesamehut/agent-config-bridge.
