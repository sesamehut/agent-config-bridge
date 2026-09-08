#!/usr/bin/env python3
"""Assemble and verify the committed `plugin/` payload of agent-config-bridge.

Usage:
  python -B scripts/package_plugin.py build      # regenerate plugin/ and .claude-plugin/marketplace.json
  python -B scripts/package_plugin.py verify     # drift gate plus payload audits (release gate)
  python -B scripts/package_plugin.py self-test  # synthetic tests of the mechanics

The payload is generated from an explicit allowlist: every Git-tracked file
under `skills/`, `templates/`, and `knowledge/`, the doctor script from
`scripts/bridge_doctor.py`, and four rendered files (both host manifests, the
payload README, and a `.gitattributes`). Nothing else is ever copied. Two
deterministic rewrites are applied while copying: knowledge links into
`../docs/` become GitHub URLs, and the Codex `default_prompt` mentions in
`agents/openai.yaml` are qualified with the plugin name.

All output is JSON on stdout. Exit 0 = pass, 1 = failure, 2 = usage error.
Python 3.9+ standard library only. Every file is read and written as bytes so
exact template bytes and LF endings survive on every platform.
"""

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

PLUGIN_NAME = "agent-config-bridge"
REPO_URL = "https://github.com/sesamehut/agent-config-bridge"
PAYLOAD_DIR = "plugin"
MARKETPLACE_FILE = ".claude-plugin/marketplace.json"
VERSION_FILE = "VERSION"
SOURCE_ROOTS = ("skills", "templates", "knowledge")
DOCTOR_SOURCE = "scripts/bridge_doctor.py"
DOCTOR_TARGET = "scripts/bridge_doctor.py"
SKILL_NAMES = ("bridge-sentinel", "bridge-sync")
DOCS_LINK_OLD = b"](../docs/"
DOCS_LINK_NEW = b"](" + REPO_URL.encode("ascii") + b"/blob/main/docs/"
DOCS_LABEL_OLD = b"[`../docs/"
DOCS_LABEL_NEW = b"[`docs/"
DOCS_RESIDUE = b"../docs/"
DOCS_URL_RE = re.compile(re.escape(DOCS_LINK_NEW) + rb"([^)#\s]+)")
OPENAI_YAML_REWRITES = tuple(
    (("$" + name).encode("ascii"), ("$" + PLUGIN_NAME + ":" + name).encode("ascii"))
    for name in SKILL_NAMES
)
VERIFIED_HOSTS = "Claude Code 2.1.263 and codex-cli 0.153.4 (checked 2026-09-08)"

DESCRIPTION = (
    "Bridge project-level agent configuration between Claude Code and Codex: "
    "a read-only drift sentinel and a plan-confirm-write sync for project "
    "skills, entry instructions, rule shards, and hook intents."
)
AUTHOR = {"name": "Zehua Hu", "email": "zehua.hu.cs@outlook.com"}
KEYWORDS = ["claude-code", "codex", "agent-config", "skills", "rules", "hooks"]
CODEX_INTERFACE = {
    "displayName": "Agent Config Bridge",
    "shortDescription": "Keep Claude Code and Codex project config in sync",
    "longDescription": (
        "Agent Config Bridge keeps one canonical source for a project's agent "
        "skills, entry instructions, rule shards, and hook intents, then "
        "projects it into the host-native Claude Code and Codex layouts. "
        "bridge-sentinel reports drift without writing; bridge-sync plans, "
        "confirms, and reconciles writes with Git-proven baselines."
    ),
    "developerName": AUTHOR["name"],
    "category": "Developer Tools",
    "capabilities": ["Interactive", "Read", "Write"],
    "defaultPrompt": [
        "Use $" + PLUGIN_NAME + ":bridge-sentinel to check this repository for "
        "agent-configuration drift without modifying files.",
        "Use $" + PLUGIN_NAME + ":bridge-sync to plan, confirm, and reconcile "
        "Bridge-managed writes in this repository.",
    ],
    "brandColor": "#2563EB",
}

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
CLAUDE_MANIFEST_KEYS = frozenset(
    {
        "name",
        "$schema",
        "displayName",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "metadata",
        "defaultEnabled",
        "skills",
        "commands",
        "agents",
        "workflows",
        "hooks",
        "mcpServers",
        "outputStyles",
        "lspServers",
        "experimental",
        "userConfig",
        "channels",
        "dependencies",
    }
)
CODEX_REQUIRED_KEYS = ("name", "version", "description", "author", "skills", "interface")
CODEX_INTERFACE_REQUIRED = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "capabilities",
    "defaultPrompt",
)
MARKETPLACE_TOP_KEYS = frozenset({"name", "owner", "description", "plugins"})
MARKETPLACE_ENTRY_KEYS = frozenset({"name", "description", "source"})
FORBIDDEN_ROOT_FILES = (
    "CLAUDE.md",
    "AGENTS.md",
    "plugin.json",
    "package.json",
    "package-lock.json",
    ".mcp.json",
    ".app.json",
)
FORBIDDEN_TOP_DIRS = ("bin", "hooks", "node_modules", ".git", "fixtures", "docs")
SECRET_FILENAME_RE = re.compile(
    r"(\.p8|\.pem|\.key|\.pfx|\.p12|\.jks|\.keystore)$"
    r"|(^|/)\.env(\.|$)"
    r"|(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$"
)
SECRET_CONTENT_PATTERNS = (
    ("private-key-block", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-access-key-id", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github-fine-grained-token", re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("secret-key-prefix", re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("slack-token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
)
BYPASS_FLAG = b"--dangerously-bypass-hook-trust"
# The flag is documented host behavior in exactly one knowledge file; every
# other payload byte, markdown included, must not mention it.
BYPASS_ALLOWLIST = {"knowledge/hooks.md": 2}
README_HEADINGS = (
    b"## What you get",
    b"## Prerequisites",
    b"## Install on Claude Code",
    b"## Install on Codex",
    b"## Safety boundaries",
    b"## Layout",
)
LINK_RE = re.compile(rb"\]\(([^)\s]+)\)")
FRONTMATTER_RE = re.compile(rb"\A---\n(.*?)\n---\n", re.S)


class PackagingError(Exception):
    """A condition that makes the payload unbuildable or unverifiable."""


# --- rendering -----------------------------------------------------------------


def json_bytes(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def render_claude_manifest(version):
    return json_bytes(
        {
            "name": PLUGIN_NAME,
            "version": version,
            "description": DESCRIPTION,
            "author": dict(AUTHOR),
            "homepage": REPO_URL,
            "repository": REPO_URL,
            "keywords": list(KEYWORDS),
        }
    )


def render_codex_manifest(version):
    return json_bytes(
        {
            "name": PLUGIN_NAME,
            "version": version,
            "description": DESCRIPTION,
            "author": dict(AUTHOR),
            "homepage": REPO_URL,
            "repository": REPO_URL,
            "keywords": list(KEYWORDS),
            "skills": "./skills/",
            "interface": json.loads(json.dumps(CODEX_INTERFACE)),
        }
    )


def render_marketplace():
    return json_bytes(
        {
            "name": PLUGIN_NAME,
            "owner": dict(AUTHOR),
            "description": (
                "Single-plugin marketplace for Agent Config Bridge, served from "
                "its own repository so both Claude Code and Codex can install "
                "the committed plugin/ payload directly."
            ),
            "plugins": [
                {
                    "name": PLUGIN_NAME,
                    "description": DESCRIPTION,
                    "source": "./" + PAYLOAD_DIR,
                }
            ],
        }
    )


def render_gitattributes():
    return b"* text=auto eol=lf\n"


def render_readme(version):
    text = r"""# Agent Config Bridge (plugin payload)

<!-- GENERATED FILE. Assembled by scripts/package_plugin.py in the upstream
     repository %(repo)s from an explicit allowlist of audited files.
     Do not edit anything under plugin/: edit the upstream sources and rebuild. -->

Version: **%(version)s**

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
| Claude Code | `/%(name)s:bridge-sentinel` | `/%(name)s:bridge-sync` |
| Codex | `$%(name)s:bridge-sentinel` | `$%(name)s:bridge-sync` |

## Prerequisites

- Git on `PATH`, and a Git worktree for the project you want to bridge.
- Python 3.9 or newer. The skills probe `python3`, then `python`, then
  `py -3`, and use the first real interpreter they find; use the same name
  below. No Node.js and no npm packages are needed.
- Verified against %(hosts)s. Other versions may work but were not checked.

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
`~/.claude/plugins/cache/%(name)s/%(name)s/%(version)s/` on Claude Code and
`~/.codex/plugins/cache/%(name)s/%(name)s/%(version)s/` on Codex. The doctor
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
claude plugin install %(name)s@%(name)s
```

The GitHub form needs a `<ref>` (branch or tag) that carries `plugin/` and
`.claude-plugin/marketplace.json`; without `#<ref>` it takes the default
branch. The shorthand clones over SSH unless `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`
is set. Then restart Claude Code or run `/reload-plugins`.

Third-party marketplaces do not auto-update, and a plugin only updates when
its declared version changes. Update with
`claude plugin marketplace update %(name)s` followed by
`claude plugin update %(name)s`; remove with
`claude plugin uninstall %(name)s@%(name)s` and
`claude plugin marketplace remove %(name)s`.

What these commands write: `marketplace add` records the marketplace in
`~/.claude/plugins/known_marketplaces.json`; the GitHub form also clones the
whole upstream repository (including its docs and its inert fixture projects)
under `~/.claude/plugins/marketplaces/%(name)s/`, and you should never start a
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
codex plugin add %(name)s@%(name)s
```

The GitHub form needs a `<ref>` that carries `plugin/` and the marketplace
manifest; without `--ref` it takes the default branch. Start a new Codex
session afterwards; skills are loaded at session start. Update a GitHub
marketplace with `codex plugin marketplace upgrade %(name)s` and run
`codex plugin add %(name)s@%(name)s` again; a local marketplace is read live,
but the plugin copy only refreshes when you run `codex plugin add` again.
Remove with `codex plugin remove %(name)s@%(name)s` and
`codex plugin marketplace remove %(name)s`.

What these commands write: `marketplace add` writes a `[marketplaces.%(name)s]`
table into `~/.codex/config.toml` (a GitHub source also keeps a full clone of
the upstream repository under `~/.codex/.tmp/marketplaces/`; never start a
session inside it); `plugin add` writes
`[plugins."%(name)s@%(name)s"] enabled = true` there and copies this directory
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
`knowledge/` into `docs/` point at %(repo)s.
""" % {
        "repo": REPO_URL,
        "version": version,
        "name": PLUGIN_NAME,
        "hosts": VERIFIED_HOSTS,
    }
    return text.encode("utf-8")


# --- sources -------------------------------------------------------------------


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def write_bytes(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def parse_version(data):
    text = data.decode("utf-8")
    if "\r" in text:
        raise PackagingError("VERSION contains CR bytes; check that .gitattributes pins it to LF")
    if not text.endswith("\n"):
        raise PackagingError("VERSION must hold exactly one semver line ending in LF")
    text = text[:-1]
    if "\n" in text or text != text.strip():
        raise PackagingError("VERSION must hold exactly one semver line ending in LF")
    if not SEMVER_RE.match(text):
        raise PackagingError("VERSION %r is not strict semver" % text)
    return text


def read_version(root):
    return parse_version(read_bytes(os.path.join(root, VERSION_FILE)))


def git_tracked_entries(root, paths):
    """Return [(mode, posix-relative-path)] for tracked files under paths."""
    out = subprocess.run(
        ["git", "-C", root, "ls-files", "-z", "-s", "--"] + list(paths),
        capture_output=True,
        check=True,
    ).stdout
    entries = []
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, rel = record.split(b"\t", 1)
        mode = meta.split(b" ")[0].decode("ascii")
        entries.append((mode, rel.decode("utf-8")))
    return entries


def rewrite_docs_links(data):
    """Point knowledge links into ../docs/ at GitHub; fix the visible label too."""
    count = data.count(DOCS_LINK_OLD)
    data = data.replace(DOCS_LINK_OLD, DOCS_LINK_NEW)
    data = data.replace(DOCS_LABEL_OLD, DOCS_LABEL_NEW)
    return data, count


def rewrite_openai_yaml(data):
    count = 0
    for old, new in OPENAI_YAML_REWRITES:
        count += data.count(old)
        data = data.replace(old, new)
    return data, count


def assemble(root, version, entries=None):
    """Build the payload map {posix path: bytes} from the allowlist.

    Content is taken from the working tree; `entries` (tracked files with
    modes) decides which paths are eligible. The function has no side effects.
    """
    if entries is None:
        entries = git_tracked_entries(root, SOURCE_ROOTS)
    payload = {}
    stats = {"copied": 0, "docs_links_rewritten": 0, "openai_yaml_rewritten": 0}
    for mode, rel in entries:
        if mode not in ("100644", "100755"):
            raise PackagingError("%s has mode %s; only regular files ship" % (rel, mode))
        top = rel.split("/", 1)[0]
        if top not in SOURCE_ROOTS:
            raise PackagingError("%s is outside the allowlist roots" % rel)
        source = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(source):
            raise PackagingError("%s is tracked but missing from the working tree" % rel)
        data = read_bytes(source)
        if top == "knowledge" and rel.endswith(".md"):
            data, count = rewrite_docs_links(data)
            stats["docs_links_rewritten"] += count
        elif top == "skills" and rel.endswith("/agents/openai.yaml"):
            data, count = rewrite_openai_yaml(data)
            stats["openai_yaml_rewritten"] += count
        payload[rel] = data
        stats["copied"] += 1
    doctor = os.path.join(root, *DOCTOR_SOURCE.split("/"))
    if not os.path.isfile(doctor):
        raise PackagingError("%s is missing" % DOCTOR_SOURCE)
    payload[DOCTOR_TARGET] = read_bytes(doctor)
    payload[".claude-plugin/plugin.json"] = render_claude_manifest(version)
    payload[".codex-plugin/plugin.json"] = render_codex_manifest(version)
    payload["README.md"] = render_readme(version)
    payload[".gitattributes"] = render_gitattributes()
    return payload, stats


# --- audits --------------------------------------------------------------------


def parse_frontmatter(data):
    match = FRONTMATTER_RE.match(data)
    if not match:
        return None
    fields = {}
    for line in match.group(1).split(b"\n"):
        if b":" in line and not line.startswith((b" ", b"\t")):
            key, value = line.split(b":", 1)
            fields[key.strip().decode("utf-8")] = value.strip().decode("utf-8")
    return fields


def link_resolves(payload, source, target):
    base = source.rsplit("/", 1)[0] if "/" in source else ""
    parts = base.split("/") if base else []
    for piece in target.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if not parts:
                return False
            parts.pop()
        else:
            parts.append(piece)
    resolved = "/".join(parts)
    if resolved in payload:
        return True
    prefix = resolved + "/" if resolved else ""
    return any(key.startswith(prefix) for key in payload) if resolved else True


def audit_payload(payload, version, marketplace, docs_exists=None):
    """Return (problems, checks) for an assembled payload and marketplace bytes.

    `docs_exists(rel)` answers whether a repo-relative docs path exists, so
    every GitHub link the build manufactures is checked against the tree it
    was built from.
    """
    problems = []
    checks = 0

    def check(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            problems.append(message)

    bypass_counts = {}
    for rel in sorted(payload):
        parts = rel.split("/")
        check(parts[-1] not in FORBIDDEN_ROOT_FILES or len(parts) > 1, "forbidden root file: " + rel)
        check(parts[0] not in FORBIDDEN_TOP_DIRS, "forbidden top-level directory: " + rel)
        check("__pycache__" not in parts and not rel.endswith((".pyc", ".pyo")), "bytecode shipped: " + rel)
        check(not SECRET_FILENAME_RE.search(rel), "secret-like filename: " + rel)
        data = payload[rel]
        for label, pattern in SECRET_CONTENT_PATTERNS:
            check(not pattern.search(data), "%s matched in %s" % (label, rel))
        bypass_counts[rel] = data.count(BYPASS_FLAG)
        check(
            bypass_counts[rel] == BYPASS_ALLOWLIST.get(rel, 0),
            "hook-trust bypass flag appears %d time(s) in %s (allowed %d)"
            % (bypass_counts[rel], rel, BYPASS_ALLOWLIST.get(rel, 0)),
        )
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            check(False, "not UTF-8: " + rel)
            continue
        check(not text.startswith("﻿"), "UTF-8 BOM: " + rel)
        check(b"\r" not in data, "CR byte: " + rel)
        check(data.endswith(b"\n") and not data.endswith(b"\n\n"), "final newline discipline: " + rel)
        check(
            not any(line.rstrip(b"\n") != line.rstrip(b"\n").rstrip(b" \t") for line in data.split(b"\n")),
            "trailing whitespace: " + rel,
        )
        check(DOCS_RESIDUE not in data, "literal ../docs/ path left in " + rel)
        if rel.endswith(".md"):
            for match in DOCS_URL_RE.finditer(data):
                target = "docs/" + match.group(1).decode("utf-8", "replace")
                check(
                    docs_exists is None or docs_exists(target),
                    "rewritten link target missing upstream: %s in %s" % (target, rel),
                )
            for match in LINK_RE.finditer(data):
                target = match.group(1).decode("utf-8", "replace")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = target.split("#", 1)[0]
                check(link_resolves(payload, rel, target), "dangling link %s in %s" % (target, rel))

    claude = codex = None
    try:
        claude = json.loads(payload[".claude-plugin/plugin.json"].decode("utf-8"))
    except (KeyError, ValueError) as exc:
        check(False, "Claude manifest unreadable: %s" % exc)
    try:
        codex = json.loads(payload[".codex-plugin/plugin.json"].decode("utf-8"))
    except (KeyError, ValueError) as exc:
        check(False, "Codex manifest unreadable: %s" % exc)
    if claude is not None:
        check(claude.get("name") == PLUGIN_NAME, "Claude manifest name")
        check(claude.get("version") == version, "Claude manifest version != VERSION")
        check(set(claude) <= CLAUDE_MANIFEST_KEYS, "Claude manifest has unrecognized keys: %s" % sorted(set(claude) - CLAUDE_MANIFEST_KEYS))
        check(bool(claude.get("description")), "Claude manifest description")
        check(isinstance(claude.get("author"), dict) and claude["author"].get("name"), "Claude manifest author")
        check("hooks" not in claude and "mcpServers" not in claude, "Claude manifest declares hooks or MCP")
    if codex is not None:
        check(codex.get("name") == PLUGIN_NAME, "Codex manifest name")
        check(codex.get("version") == version, "Codex manifest version != VERSION")
        check(all(key in codex for key in CODEX_REQUIRED_KEYS), "Codex manifest required keys")
        check(codex.get("skills") == "./skills/", "Codex manifest skills path")
        interface = codex.get("interface") or {}
        check(all(interface.get(key) for key in CODEX_INTERFACE_REQUIRED), "Codex interface required keys")
        check(isinstance(interface.get("capabilities"), list), "Codex interface capabilities list")
        check(bool(re.match(r"^#[0-9A-F]{6}$", str(interface.get("brandColor", "")))), "Codex brandColor")
        check(isinstance(codex.get("author"), dict) and codex["author"].get("name"), "Codex manifest author")
        check("hooks" not in codex and "mcpServers" not in codex and "apps" not in codex, "Codex manifest declares hooks, MCP, or apps")
    check(bool(SEMVER_RE.match(version)), "version is not strict semver")

    try:
        market = json.loads(marketplace.decode("utf-8"))
    except ValueError as exc:
        market = None
        check(False, "marketplace unreadable: %s" % exc)
    if market is not None:
        check(set(market) <= MARKETPLACE_TOP_KEYS and {"name", "owner", "plugins"} <= set(market), "marketplace top-level keys")
        check(market.get("name") == PLUGIN_NAME, "marketplace name")
        check(bool(market.get("description")), "marketplace description")
        check(isinstance(market.get("owner"), dict) and market["owner"].get("name"), "marketplace owner")
        entries = market.get("plugins") or []
        check(len(entries) == 1, "marketplace must list exactly one plugin")
        for entry in entries:
            check(set(entry) <= MARKETPLACE_ENTRY_KEYS and {"name", "source"} <= set(entry), "marketplace entry keys")
            check(entry.get("name") == PLUGIN_NAME, "marketplace entry name")
            check(entry.get("source") == "./" + PAYLOAD_DIR, "marketplace entry source")
            check("version" not in entry, "marketplace entry must not pin a version")

    for name in SKILL_NAMES:
        skill = "skills/%s/SKILL.md" % name
        fields = parse_frontmatter(payload.get(skill, b""))
        check(fields is not None, "missing or unparsable frontmatter: " + skill)
        if fields is not None:
            check(fields.get("name") == name, "frontmatter name mismatch in " + skill)
            check(bool(fields.get("description")), "frontmatter description missing in " + skill)
        yaml_path = "skills/%s/agents/openai.yaml" % name
        yaml_data = payload.get(yaml_path, b"")
        check(bool(yaml_data), "missing " + yaml_path)
        check(("$" + PLUGIN_NAME + ":" + name).encode("ascii") in yaml_data, "unqualified default_prompt in " + yaml_path)
        check(not re.search(rb"\$bridge-(sentinel|sync)\b", yaml_data), "bare skill mention left in " + yaml_path)
    for required in (
        "skills/bridge-sentinel/scripts/sentinel_mechanics.py",
        "templates/covenant/README.md",
        "knowledge/README.md",
        DOCTOR_TARGET,
        "README.md",
        ".gitattributes",
    ):
        check(required in payload, "missing required payload file: " + required)
    readme = payload.get("README.md", b"")
    check(version.encode("utf-8") in readme, "README does not show the version")
    check(b"GENERATED FILE" in readme, "README lacks the generated-file banner")
    for heading in README_HEADINGS:
        check(heading in readme, "README lacks section " + heading.decode("ascii"))
    for rel, allowed in BYPASS_ALLOWLIST.items():
        check(bypass_counts.get(rel, 0) == allowed, "bypass-flag allowlist entry %s not satisfied" % rel)
    return problems, checks


# --- disk comparison -----------------------------------------------------------


def disk_tree(base):
    """Return ({posix rel: bytes}, [symlinks]) for every file under base."""
    files = {}
    symlinks = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(dirnames)
        for name in dirnames:
            if os.path.islink(os.path.join(dirpath, name)):
                symlinks.append(os.path.relpath(os.path.join(dirpath, name), base).replace(os.sep, "/"))
        for name in sorted(filenames):
            if name.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            if os.path.islink(full):
                symlinks.append(rel)
                continue
            files[rel] = read_bytes(full)
    return files, symlinks


def compare_trees(expected, actual):
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    differs = sorted(rel for rel in set(expected) & set(actual) if expected[rel] != actual[rel])
    return {"missing": missing, "extra": extra, "differs": differs}


def _force_writable(func, path, exc_info):
    """rmtree handler: retry read-only files, re-raise every other error."""
    if not isinstance(exc_info[1], PermissionError):
        raise exc_info[1]
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _is_link(path):
    is_junction = getattr(os.path, "isjunction", None)
    return os.path.islink(path) or bool(is_junction and is_junction(path))


def write_payload(root, payload, marketplace):
    target = os.path.join(root, PAYLOAD_DIR)
    if os.path.lexists(os.path.join(target, ".git")):
        raise PackagingError("refusing to wipe %s: it contains a .git entry" % target)
    if os.path.lexists(target):
        if _is_link(target):
            raise PackagingError("refusing to wipe %s: it is a link" % target)
        shutil.rmtree(target, onerror=_force_writable)
    for rel in sorted(payload):
        write_bytes(os.path.join(target, *rel.split("/")), payload[rel])
    write_bytes(os.path.join(root, *MARKETPLACE_FILE.split("/")), marketplace)


# --- commands ------------------------------------------------------------------


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def docs_exists_in(root):
    return lambda rel: os.path.isfile(os.path.join(root, *rel.split("/")))


def perform_build(root, version, entries=None, docs_exists=None):
    """Assemble, audit, and write only when the audit is clean (fail closed)."""
    payload, stats = assemble(root, version, entries=entries)
    marketplace = render_marketplace()
    problems, checks = audit_payload(payload, version, marketplace, docs_exists=docs_exists)
    wrote = []
    if not problems:
        write_payload(root, payload, marketplace)
        wrote = [PAYLOAD_DIR + "/", MARKETPLACE_FILE]
    return {
        "command": "build",
        "pass": not problems,
        "version": version,
        "files": len(payload),
        "stats": stats,
        "audit_checks": checks,
        "problems": problems,
        "wrote": wrote,
    }


def command_build(root):
    version = read_version(root)
    return perform_build(root, version, docs_exists=docs_exists_in(root))


def command_verify(root):
    version = read_version(root)
    payload, stats = assemble(root, version)
    marketplace = render_marketplace()
    problems, checks = audit_payload(payload, version, marketplace, docs_exists=docs_exists_in(root))
    target = os.path.join(root, PAYLOAD_DIR)
    if not os.path.isdir(target):
        raise PackagingError("%s/ does not exist; run build first" % PAYLOAD_DIR)
    actual, symlinks = disk_tree(target)
    drift = compare_trees(payload, actual)
    market_path = os.path.join(root, *MARKETPLACE_FILE.split("/"))
    market_ok = os.path.isfile(market_path) and read_bytes(market_path) == marketplace
    for rel in symlinks:
        problems.append("symlink inside payload: " + rel)
    for kind in ("missing", "extra", "differs"):
        for rel in drift[kind]:
            problems.append("%s: %s" % (kind, rel))
    if not market_ok:
        problems.append("marketplace file drifted or missing: " + MARKETPLACE_FILE)
    checks += 2 + len(payload)
    return {
        "command": "verify",
        "pass": not problems,
        "version": version,
        "files": len(payload),
        "stats": stats,
        "checks": checks,
        "drift": drift,
        "marketplace_in_sync": market_ok,
        "problems": problems,
    }


# --- self-test -----------------------------------------------------------------


def _synthetic_source(root):
    files = {
        "skills/bridge-sentinel/SKILL.md": b"---\nname: bridge-sentinel\ndescription: Synthetic sentinel.\n---\n\nRun `<skill-dir>/scripts/sentinel_mechanics.py`.\nSee [spec](references/spec.md) and [covenant](../../templates/covenant/README.md).\n",
        "skills/bridge-sentinel/agents/openai.yaml": b"interface:\n  default_prompt: \"Use $bridge-sentinel to check drift.\"\n",
        "skills/bridge-sentinel/references/spec.md": b"# spec\n",
        "skills/bridge-sentinel/scripts/sentinel_mechanics.py": b"print('ok')\n",
        "skills/bridge-sync/SKILL.md": b"---\nname: bridge-sync\ndescription: Synthetic sync.\n---\n\nUses [sibling](../bridge-sentinel/scripts/sentinel_mechanics.py).\n",
        "skills/bridge-sync/agents/openai.yaml": b"interface:\n  default_prompt: \"Use $bridge-sync to sync. Also $bridge-sentinel first.\"\n",
        "templates/covenant/README.md": b"# covenant\n\nSee [v1](v1/).\n",
        "templates/covenant/v1/block.md": b"exact bytes\n",
        "knowledge/README.md": b"# knowledge\n\n- [entry](entry.md)\n- [spec](../skills/bridge-sentinel/references/spec.md)\n",
        "knowledge/entry.md": b"Dated notes in [`../docs/research/x.md`](../docs/research/x.md) and [again](../docs/research/y.md).\n",
        "knowledge/hooks.md": b"Documented flag --dangerously-bypass-hook-trust, and again --dangerously-bypass-hook-trust.\n",
        "scripts/bridge_doctor.py": b"print('doctor')\n",
        "docs/research/x.md": b"x\n",
        "docs/research/y.md": b"y\n",
    }
    for rel, data in files.items():
        write_bytes(os.path.join(root, *rel.split("/")), data)
    entries = [("100644", rel) for rel in files if rel.split("/", 1)[0] in SOURCE_ROOTS]
    return entries


def command_self_test():
    passed = 0
    failures = []

    def expect(condition, label):
        nonlocal passed
        if condition:
            passed += 1
        else:
            failures.append(label)

    def expect_raises(func, label):
        try:
            func()
        except PackagingError:
            expect(True, label)
        else:
            expect(False, label)

    # version parsing
    expect(parse_version(b"0.1.0\n") == "0.1.0", "semver-basic")
    expect(parse_version(b"1.2.3-rc.1+build.5\n") == "1.2.3-rc.1+build.5", "semver-prerelease-build")
    for bad in (b"v0.1.0\n", b"0.1\n", b"01.0.0\n", b"0.1.0\r\n", b"0.1.0\n\n", b" 0.1.0\n", b"0.1.0\nx\n", b"0.1.0"):
        expect_raises(lambda bad=bad: parse_version(bad), "semver-reject-%r" % bad)
    try:
        parse_version(b"0.1.0\r\n")
    except PackagingError as exc:
        expect("CR" in str(exc), "semver-crlf-named-error")

    # rewrites
    data, count = rewrite_docs_links(b"a [x](../docs/a.md) b [`../docs/b/c.md`](../docs/b/c.md) c [z](../skills/s.md)")
    expect(count == 2 and data.count(DOCS_LINK_NEW) == 2 and b"](../skills/s.md)" in data, "docs-link-rewrite")
    expect(b"[`docs/b/c.md`]" in data and DOCS_RESIDUE not in data, "docs-label-rewrite")
    expect(rewrite_docs_links(data) == (data, 0), "docs-link-rewrite-idempotent")
    yaml_data, count = rewrite_openai_yaml(b"Use $bridge-sentinel then $bridge-sync; $bridge-sentinel again")
    expect(count == 3 and yaml_data == b"Use $agent-config-bridge:bridge-sentinel then $agent-config-bridge:bridge-sync; $agent-config-bridge:bridge-sentinel again", "openai-yaml-rewrite")
    expect(rewrite_openai_yaml(yaml_data) == (yaml_data, 0), "openai-yaml-rewrite-idempotent")

    # rendering determinism and content
    expect(render_claude_manifest("0.1.0") == render_claude_manifest("0.1.0"), "claude-manifest-deterministic")
    expect(render_codex_manifest("0.1.0") == render_codex_manifest("0.1.0"), "codex-manifest-deterministic")
    expect(b'"version": "9.8.7"' in render_claude_manifest("9.8.7"), "claude-manifest-version")
    expect(b"9.8.7" in render_readme("9.8.7") and b"GENERATED FILE" in render_readme("9.8.7"), "readme-version-and-banner")
    expect(json.loads(render_marketplace().decode("utf-8"))["plugins"][0]["source"] == "./plugin", "marketplace-source")

    with tempfile.TemporaryDirectory(prefix="acb-package-selftest-") as tmp:
        src = os.path.join(tmp, "src")
        entries = _synthetic_source(src)
        docs_exists = docs_exists_in(src)
        payload, stats = assemble(src, "0.1.0", entries=entries)
        expect(stats == {"copied": 11, "docs_links_rewritten": 2, "openai_yaml_rewritten": 3}, "assemble-stats %r" % (stats,))
        expect(set(payload) == set(rel for _, rel in entries) | {DOCTOR_TARGET, ".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "README.md", ".gitattributes"}, "assemble-keys")
        expect(payload["templates/covenant/v1/block.md"] == b"exact bytes\n", "assemble-byte-identical")
        expect(DOCS_LINK_OLD not in payload["knowledge/entry.md"], "assemble-rewrote-knowledge")
        expect(b"$agent-config-bridge:bridge-sync" in payload["skills/bridge-sync/agents/openai.yaml"], "assemble-rewrote-yaml")
        expect_raises(lambda: assemble(src, "0.1.0", entries=entries + [("120000", "skills/link")]), "assemble-rejects-symlink-mode")
        expect_raises(lambda: assemble(src, "0.1.0", entries=entries + [("100644", "docs/x.md")]), "assemble-rejects-outside-root")
        expect_raises(lambda: assemble(src, "0.1.0", entries=entries + [("100644", "skills/missing.md")]), "assemble-rejects-missing-file")

        marketplace = render_marketplace()
        problems, checks = audit_payload(payload, "0.1.0", marketplace, docs_exists=docs_exists)
        expect(problems == [] and checks > 50, "audit-clean %r" % (problems,))

        def broken(mutate, label):
            copy = dict(payload)
            market = marketplace
            result = mutate(copy)
            if isinstance(result, bytes):
                market = result
            found, _ = audit_payload(copy, "0.1.0", market, docs_exists=docs_exists)
            expect(bool(found), "audit-catches-" + label)

        broken(lambda p: p.__setitem__("CLAUDE.md", b"# no\n"), "root-claude-md")
        broken(lambda p: p.__setitem__("AGENTS.md", b"# no\n"), "root-agents-md")
        broken(lambda p: p.__setitem__("plugin.json", b"{}\n"), "root-plugin-json")
        broken(lambda p: p.__setitem__("bin/x", b"#!/bin/sh\n"), "bin-dir")
        broken(lambda p: p.__setitem__("hooks/hooks.json", b"{}\n"), "hooks-dir")
        broken(lambda p: p.__setitem__("skills/x/__pycache__/a.pyc", b"\x00\n"), "pycache")
        broken(lambda p: p.__setitem__("skills/cert.pem", b"x\n"), "secret-filename-pem")
        broken(lambda p: p.__setitem__("skills/.env", b"x\n"), "secret-filename-env")
        broken(lambda p: p.__setitem__("knowledge/id_rsa", b"x\n"), "secret-filename-id-rsa")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----\n"), "pem-block")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"key AKIAABCDEFGHIJKLMNOP here\n"), "aws-key")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"token ghp_" + b"a" * 36 + b"\n"), "github-token")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"sk-" + b"b" * 24 + b"\n"), "sk-token")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"xoxb-1234567890-abc\n"), "slack-token")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"github_pat_" + b"c" * 30 + b"\n"), "github-fine-grained-token")
        broken(lambda p: p.__setitem__("scripts/run.py", b"flag = '--dangerously-bypass-hook-trust'\n"), "bypass-flag-in-code")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"prose --dangerously-bypass-hook-trust\n"), "bypass-flag-in-other-markdown")
        broken(lambda p: p.__setitem__("knowledge/hooks.md", b"once --dangerously-bypass-hook-trust\n"), "bypass-flag-count-drift")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"see `../docs/research/x.md`\n"), "docs-residue-in-prose")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"[x](" + DOCS_LINK_NEW[2:] + b"research/missing.md)\n"), "rewritten-target-missing")
        broken(lambda p: p.__setitem__("README.md", b"GENERATED FILE 0.1.0\n## What you get\n"), "readme-missing-sections")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"\xef\xbb\xbf# bom\n"), "bom")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"crlf\r\n"), "crlf")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"no newline"), "missing-final-newline")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"two\n\n"), "double-final-newline")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"trailing \n"), "trailing-whitespace")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"\xff\xfe\n"), "non-utf8")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"[x](../docs/a.md)\n"), "unrewritten-docs-link")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"[x](missing.md)\n"), "dangling-link")
        broken(lambda p: p.__setitem__("knowledge/k.md", b"[x](../../escape.md)\n"), "escaping-link")
        broken(lambda p: p.__setitem__(".claude-plugin/plugin.json", render_claude_manifest("0.2.0")), "claude-version-mismatch")
        broken(lambda p: p.__setitem__(".codex-plugin/plugin.json", render_codex_manifest("0.2.0")), "codex-version-mismatch")
        broken(lambda p: p.__setitem__(".claude-plugin/plugin.json", json_bytes({"name": PLUGIN_NAME, "version": "0.1.0", "description": "d", "author": {"name": "a"}, "interface": {}})), "claude-unknown-key")
        broken(lambda p: p.__setitem__(".claude-plugin/plugin.json", json_bytes({"name": "other", "version": "0.1.0", "description": "d", "author": {"name": "a"}})), "claude-name-mismatch")
        broken(lambda p: p.__setitem__(".codex-plugin/plugin.json", json_bytes({"name": PLUGIN_NAME, "version": "0.1.0", "description": "d", "author": {"name": "a"}, "skills": "./skills/"})), "codex-missing-interface")
        broken(lambda p: p.__setitem__(".codex-plugin/plugin.json", json_bytes(dict(json.loads(render_codex_manifest("0.1.0").decode("utf-8")), skills="skills"))), "codex-skills-path")
        broken(lambda p: p.__setitem__("skills/bridge-sync/agents/openai.yaml", b"interface:\n  default_prompt: \"Use $bridge-sync\"\n"), "bare-mention")
        broken(lambda p: p.__setitem__("skills/bridge-sync/SKILL.md", b"---\nname: other\ndescription: d\n---\n\nbody\n"), "frontmatter-name")
        broken(lambda p: p.__setitem__("skills/bridge-sync/SKILL.md", b"---\nname: bridge-sync\n---\n\nbody\n"), "frontmatter-description")
        broken(lambda p: p.pop("skills/bridge-sentinel/scripts/sentinel_mechanics.py"), "missing-mechanics")
        broken(lambda p: p.pop("README.md"), "missing-readme")
        broken(lambda p: p.__setitem__("README.md", b"# no version here\n"), "readme-without-version")
        broken(lambda p: json_bytes({"name": PLUGIN_NAME, "owner": {"name": "a"}, "description": "d", "plugins": [{"name": PLUGIN_NAME, "source": "./plugin", "version": "0.1.0"}]}), "marketplace-entry-version")
        broken(lambda p: json_bytes({"name": PLUGIN_NAME, "owner": {"name": "a"}, "description": "d", "plugins": [{"name": PLUGIN_NAME, "source": "./"}]}), "marketplace-entry-source")
        broken(lambda p: json_bytes({"name": PLUGIN_NAME, "owner": {"name": "a"}, "description": "d", "policy": {}, "plugins": [{"name": PLUGIN_NAME, "source": "./plugin"}]}), "marketplace-extra-top-key")
        broken(lambda p: json_bytes({"name": PLUGIN_NAME, "owner": {"name": "a"}, "plugins": [{"name": PLUGIN_NAME, "source": "./plugin"}]}), "marketplace-missing-description")
        broken(lambda p: json_bytes({"name": "other", "owner": {"name": "a"}, "description": "d", "plugins": [{"name": PLUGIN_NAME, "source": "./plugin"}]}), "marketplace-name")
        found, _ = audit_payload(payload, "0.1", marketplace)
        expect(bool(found), "audit-catches-bad-version-string")

        # disk round trip and drift detection
        out_root = os.path.join(tmp, "out")
        write_payload(out_root, payload, marketplace)
        actual, symlinks = disk_tree(os.path.join(out_root, PAYLOAD_DIR))
        expect(compare_trees(payload, actual) == {"missing": [], "extra": [], "differs": []} and not symlinks, "disk-roundtrip-byte-equal")
        expect(read_bytes(os.path.join(out_root, *MARKETPLACE_FILE.split("/"))) == marketplace, "disk-marketplace-written")
        write_bytes(os.path.join(out_root, PAYLOAD_DIR, "knowledge", "extra.md"), b"x\n")
        write_bytes(os.path.join(out_root, PAYLOAD_DIR, "knowledge", "__pycache__", "a.pyc"), b"\x00")
        write_bytes(os.path.join(out_root, PAYLOAD_DIR, "knowledge", "README.md"), b"changed\n")
        os.remove(os.path.join(out_root, PAYLOAD_DIR, "templates", "covenant", "v1", "block.md"))
        actual, _ = disk_tree(os.path.join(out_root, PAYLOAD_DIR))
        drift = compare_trees(payload, actual)
        expect(drift == {"missing": ["templates/covenant/v1/block.md"], "extra": ["knowledge/extra.md"], "differs": ["knowledge/README.md"]}, "drift-detection %r" % (drift,))
        write_payload(out_root, payload, marketplace)
        actual, _ = disk_tree(os.path.join(out_root, PAYLOAD_DIR))
        expect(compare_trees(payload, actual) == {"missing": [], "extra": [], "differs": []}, "rebuild-wipes-stale-files")
        os.makedirs(os.path.join(out_root, PAYLOAD_DIR, ".git"))
        expect_raises(lambda: write_payload(out_root, payload, marketplace), "refuse-wipe-git-dir")
        shutil.rmtree(os.path.join(out_root, PAYLOAD_DIR, ".git"))
        write_bytes(os.path.join(out_root, PAYLOAD_DIR, ".git"), b"gitdir: elsewhere\n")
        expect_raises(lambda: write_payload(out_root, payload, marketplace), "refuse-wipe-gitlink-file")
        try:
            _force_writable(os.path.islink, out_root, (OSError, OSError("not a permission problem"), None))
        except OSError:
            expect(True, "rmtree-handler-reraises-non-permission-errors")
        else:
            expect(False, "rmtree-handler-reraises-non-permission-errors")
        link_root = os.path.join(tmp, "linked")
        link_target = os.path.join(tmp, "link-target")
        os.makedirs(link_target)
        os.makedirs(link_root)
        try:
            os.symlink(link_target, os.path.join(link_root, PAYLOAD_DIR), target_is_directory=True)
        except (OSError, NotImplementedError):
            pass
        else:
            expect_raises(lambda: write_payload(link_root, payload, marketplace), "refuse-wipe-linked-payload-dir")
        write_bytes(os.path.join(out_root, PAYLOAD_DIR, "knowledge", "__pycache__", "stray.txt"), b"x\n")
        actual, _ = disk_tree(os.path.join(out_root, PAYLOAD_DIR))
        expect("knowledge/__pycache__/stray.txt" in actual, "pycache-non-bytecode-file-is-visible")

        # build fails closed: a payload that fails the audit is never written
        dirty = os.path.join(tmp, "dirty")
        dirty_entries = _synthetic_source(dirty)
        write_bytes(os.path.join(dirty, "knowledge", "leak.pem"), b"x\n")
        dirty_entries.append(("100644", "knowledge/leak.pem"))
        result = perform_build(dirty, "0.1.0", entries=dirty_entries, docs_exists=docs_exists_in(dirty))
        expect(result["pass"] is False and result["wrote"] == [] and not os.path.exists(os.path.join(dirty, PAYLOAD_DIR)), "build-fails-closed")
        clean = perform_build(src, "0.1.0", entries=entries, docs_exists=docs_exists)
        expect(clean["pass"] is True and clean["wrote"] == [PAYLOAD_DIR + "/", MARKETPLACE_FILE] and os.path.isfile(os.path.join(src, PAYLOAD_DIR, "README.md")), "build-writes-when-clean")

    return {"command": "self-test", "pass": not failures, "checks": passed, "failures": failures}


def main(argv):
    parser = argparse.ArgumentParser(prog="package_plugin.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("build", "verify", "self-test"))
    args = parser.parse_args(argv)
    root = repo_root()
    try:
        if args.command == "build":
            result = command_build(root)
        elif args.command == "verify":
            result = command_verify(root)
        else:
            result = command_self_test()
    except PackagingError as exc:
        result = {"command": args.command, "pass": False, "error": str(exc)}
    except subprocess.CalledProcessError as exc:
        result = {"command": args.command, "pass": False, "error": "git failed: %s" % exc.stderr.decode("utf-8", "replace").strip()}
    except OSError as exc:
        result = {"command": args.command, "pass": False, "error": "%s: %s" % (type(exc).__name__, exc)}
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
