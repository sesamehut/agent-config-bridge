#!/usr/bin/env python3
"""Offline preflight for the Agent Config Bridge plugin payload.

Usage:
  python <plugin-root>/scripts/bridge_doctor.py [--json]

Checks, without writing anything and without network access:
  - the Python interpreter is 3.9 or newer;
  - `git` is on PATH;
  - the plugin layout is intact (both manifests, both skills, the sentinel
    mechanics script, the covenant templates, the knowledge base);
  - both manifests agree on plugin name and version;
  - the sentinel mechanics self-test passes.

Exit 0 when every check passes, 1 when any check fails, 2 on usage error.
It writes nothing inside the plugin tree or the project: bytecode caching is
disabled and the sentinel self-test manages only its own OS temporary
directory. It is a manual troubleshooting aid; the skills carry their own
preflight.
Python 3.9+ standard library only. This file is copied verbatim into the
payload by scripts/package_plugin.py; the upstream copy is the source.
"""

import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True

MIN_PYTHON = (3, 9)
REQUIRED_FILES = (
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "README.md",
    "skills/bridge-sentinel/SKILL.md",
    "skills/bridge-sentinel/agents/openai.yaml",
    "skills/bridge-sentinel/scripts/sentinel_mechanics.py",
    "skills/bridge-sentinel/references/report-spec.md",
    "skills/bridge-sentinel/references/source-tree-spec.md",
    "skills/bridge-sync/SKILL.md",
    "skills/bridge-sync/agents/openai.yaml",
    "skills/bridge-sync/references/reconciliation-spec.md",
    "skills/bridge-sync/references/sync-plan-spec.md",
    "skills/bridge-sync/references/canonical-plan-cases.md",
    "templates/covenant/README.md",
    "templates/covenant/agents-md-covenant-block.md",
    "templates/covenant/claude-rules-bridge.md",
    "templates/covenant/v1/agents-md-covenant-block.md",
    "templates/covenant/v1/claude-rules-bridge.md",
    "templates/covenant/v2/agents-md-covenant-block.md",
    "templates/covenant/v2/claude-rules-bridge.md",
    "templates/hook-intents.example.md",
    "knowledge/README.md",
    "knowledge/entry-and-rules.md",
    "knowledge/execution-semantics.md",
    "knowledge/hooks.md",
    "knowledge/skills.md",
)


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_python():
    version = sys.version_info[:3]
    ok = version >= MIN_PYTHON
    detail = "%d.%d.%d at %s" % (version[0], version[1], version[2], sys.executable)
    hint = "" if ok else "Install Python %d.%d or newer and rerun with it." % MIN_PYTHON
    return {"check": "python", "ok": ok, "detail": detail, "hint": hint}


def check_git():
    try:
        out = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, check=False
        )
    except OSError as exc:
        return {
            "check": "git",
            "ok": False,
            "detail": str(exc),
            "hint": "Install Git and make sure `git` is on PATH.",
        }
    ok = out.returncode == 0
    detail = (out.stdout or out.stderr).strip()
    hint = "" if ok else "Install Git and make sure `git` is on PATH."
    return {"check": "git", "ok": ok, "detail": detail, "hint": hint}


def read_json(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def check_layout(root):
    missing = [rel for rel in REQUIRED_FILES if not os.path.isfile(os.path.join(root, rel))]
    ok = not missing
    return {
        "check": "layout",
        "ok": ok,
        "detail": "all %d required files present" % len(REQUIRED_FILES)
        if ok
        else "missing: " + ", ".join(missing),
        "hint": "" if ok else "Reinstall the plugin; the payload is incomplete.",
    }


def check_manifests(root):
    try:
        claude = read_json(os.path.join(root, ".claude-plugin", "plugin.json"))
        codex = read_json(os.path.join(root, ".codex-plugin", "plugin.json"))
    except (OSError, ValueError) as exc:
        return {
            "check": "manifests",
            "ok": False,
            "detail": "unreadable manifest: %s" % exc,
            "hint": "Reinstall the plugin; a manifest is missing or invalid.",
        }
    problems = []
    if claude.get("name") != codex.get("name"):
        problems.append("name differs: %r vs %r" % (claude.get("name"), codex.get("name")))
    if claude.get("version") != codex.get("version"):
        problems.append(
            "version differs: %r vs %r" % (claude.get("version"), codex.get("version"))
        )
    if not claude.get("name") or not claude.get("version"):
        problems.append("name or version missing")
    ok = not problems
    return {
        "check": "manifests",
        "ok": ok,
        "detail": "%s %s" % (claude.get("name"), claude.get("version"))
        if ok
        else "; ".join(problems),
        "hint": "" if ok else "Reinstall the plugin; the manifests disagree.",
    }


def check_sentinel_self_test(root):
    script = os.path.join(root, "skills", "bridge-sentinel", "scripts", "sentinel_mechanics.py")
    try:
        out = subprocess.run(
            [sys.executable, "-B", script, "self-test"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {
            "check": "sentinel-self-test",
            "ok": False,
            "detail": str(exc),
            "hint": "The sentinel mechanics script could not be started.",
        }
    ok = out.returncode == 0
    checks = None
    if ok:
        try:
            parsed = json.loads(out.stdout)
            checks = parsed.get("checks")
            if isinstance(checks, list):
                checks = len(checks)
            ok = bool(parsed.get("pass", False))
        except ValueError:
            ok = False
    detail = (
        "%s checks passed" % checks
        if ok
        else (out.stderr.strip() or out.stdout.strip() or "exit %d" % out.returncode)[-800:]
    )
    hint = "" if ok else "The bundled mechanics failed under this interpreter; check the Python version."
    return {"check": "sentinel-self-test", "ok": ok, "detail": detail, "hint": hint}


def run():
    root = plugin_root()
    results = [check_python(), check_git(), check_layout(root)]
    results.append(check_manifests(root))
    if results[0]["ok"] and results[2]["ok"]:
        results.append(check_sentinel_self_test(root))
    else:
        results.append(
            {
                "check": "sentinel-self-test",
                "ok": False,
                "detail": "skipped: interpreter or layout check failed",
                "hint": "Fix the earlier failures first.",
            }
        )
    return root, results


def main(argv):
    if len(argv) > 1 or (argv and argv[0] not in ("--json", "--help", "-h")):
        sys.stderr.write("usage: bridge_doctor.py [--json]\n")
        return 2
    if argv and argv[0] in ("--help", "-h"):
        sys.stdout.write(__doc__)
        return 0
    root, results = run()
    ok = all(item["ok"] for item in results)
    if argv == ["--json"]:
        sys.stdout.write(
            json.dumps({"plugin_root": root, "pass": ok, "checks": results}, indent=2) + "\n"
        )
    else:
        sys.stdout.write("Agent Config Bridge doctor\n")
        sys.stdout.write("plugin root: %s\n" % root)
        for item in results:
            mark = "ok  " if item["ok"] else "FAIL"
            sys.stdout.write("  [%s] %-20s %s\n" % (mark, item["check"], item["detail"]))
            if item["hint"]:
                sys.stdout.write("         %s\n" % item["hint"])
        sys.stdout.write("result: %s\n" % ("pass" if ok else "fail"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
