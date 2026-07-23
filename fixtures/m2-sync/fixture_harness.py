#!/usr/bin/env python3
"""Materialize and compare isolated M2 mutation fixtures.

This helper knows only fixture manifests, filesystem types, bytes, modes, and
disposable git setup. It deliberately contains no Bridge direction,
arbitration, adoption, or projection logic.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parent
SCENARIOS = ROOT / "scenarios"
REPO_ROOT = ROOT.parents[1]
SCENARIO_SPEC = "bridge-sync-scenario/v1"
TREE_SPEC = "bridge-sync-tree/v1"
PLAN_SPEC = "sync-plan/v1"
MARKER_SPEC = "bridge-sync-fixture-marker/v1"
SAFEGUARDS_SPEC = "bridge-sync-safeguards/v1"
MARKER_NAME = "bridge-sync-fixture.json"
SAFEGUARDS_PATH = ROOT / "verification-safeguards.json"
TEXT_SUFFIXES = {".json", ".md", ".py", ".sh", ".txt", ".yaml", ".yml"}
INERT_POLICY = b"policy:\n  allow_implicit_invocation: false\n"
PLAN_CONTRACTS = "covenant/v1, source-tree/v3, report/v3, reconciliation/v1"
PLAN_HEADER = (
    "| unit | baseline | state | action | direction | outcome | tier | annotations |"
)
PLAN_SEPARATOR = "|---|---|---|---|---|---|---|---|"
PLAN_STATES = {
    "unchanged",
    "source-only",
    "projection-only",
    "both-changed",
    "no-baseline",
    "contract-migration",
    "offboarding",
    "blocked",
}
PLAN_ACTIONS = {
    "create",
    "repair",
    "restore",
    "update",
    "reproject",
    "adopt",
    "conflict",
    "delete",
    "rename",
    "annex-or-keep",
    "annex",
    "keep",
    "migrate",
    "offboard",
    "resolve-blocker",
    "unchanged",
}
PLAN_DIRECTIONS = {
    "-",
    "source-to-projection",
    "projection-to-source",
    "user-decision",
}
PLAN_OUTCOMES = {
    "planned",
    "applied",
    "unchanged",
    "deferred",
    "blocked",
    "failed",
    "compensated",
    "partial",
    "not-attempted",
    "rolled-back",
}
PLAN_ANNOTATIONS = {
    "behavior-degraded",
    "decision-required",
    "intent-required",
    "live-activation-unknown",
    "restart-may-be-required",
}
PLAN_WARNINGS = {
    "ignored-files-excluded",
    "mode-limited",
    "sensitive-or-generated-blocked",
    "unrelated-dirty-preserved",
    "unsafe-tree-entry",
    "untracked-files-included",
    "validator-profile-mismatch",
}
REPLAY_MODES = {"agent", "declarative-only"}
REQUIRED_SAFEGUARD_IDS = {
    "case-fold-collision-blocked",
    "covenant-malformed",
    "covenant-untracked",
    "covenant-version-mismatch",
    "delete-projection-to-source",
    "delete-source-to-projection",
    "gitlink-blocked",
    "ignored-required-input-blocked",
    "intent-is-not-ownership",
    "keep-remains-unresolved",
    "migrate-explicit",
    "offboard-explicit",
    "rename-atomic",
    "rename-destination-occupied",
    "rename-mid-compensated",
    "rename-mid-failure",
    "rollback-preserves-preexisting-dirty",
    "secret-generated-blocked",
    "special-file-blocked",
    "tracked-deletion-participates",
    "unreachable-refs-excluded",
    "untracked-covenant-old-tuple-repair-before-migrate",
}
REQUIRED_SAFEGUARD_CLASSIFICATIONS = {
    "covenant-malformed": (
        "blocked",
        "repair",
        "user-decision",
        "planned",
        "required",
    ),
    "covenant-untracked": (
        "blocked",
        "repair",
        "user-decision",
        "planned",
        "required",
    ),
    "covenant-version-mismatch": (
        "blocked",
        "repair",
        "user-decision",
        "planned",
        "required",
    ),
    "migrate-explicit": (
        "contract-migration",
        "migrate",
        "user-decision",
        "planned",
        "required",
    ),
    "rename-mid-compensated": (
        "source-only",
        "rename",
        "source-to-projection",
        "compensated",
        "confirmed",
    ),
    "rename-mid-failure": (
        "source-only",
        "rename",
        "source-to-projection",
        "partial",
        "confirmed",
    ),
    "untracked-covenant-old-tuple-repair-before-migrate": (
        "blocked",
        "repair",
        "user-decision",
        "planned",
        "required",
    ),
}
HASH_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
NONCE_PATTERN = re.compile(r"[A-Za-z0-9_-]{6,64}")
TOKEN_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CREATED_TEMP_ROOTS: set[Path] = set()


class FixtureError(RuntimeError):
    """A deterministic fixture contract violation."""


Entry = Dict[str, Any]
Tree = Dict[str, Entry]


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FixtureError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FixtureError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _scenario_dir(name: str) -> Path:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise FixtureError(f"invalid scenario name: {name!r}")
    result = SCENARIOS / name
    if not result.is_dir():
        raise FixtureError(f"unknown scenario: {name}")
    return result


def _load_scenario(name: str) -> Tuple[Path, Dict[str, Any]]:
    directory = _scenario_dir(name)
    scenario = _read_json(directory / "scenario.json")
    if scenario.get("spec") != SCENARIO_SPEC:
        raise FixtureError(f"{name}: expected spec {SCENARIO_SPEC}")
    if scenario.get("name") != name:
        raise FixtureError(f"{name}: scenario name does not match directory")
    return directory, scenario


def _safe_relative(raw: Any, *, field: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise FixtureError(f"{field} must be a non-empty string")
    if "\\" in raw:
        raise FixtureError(f"{field} must use POSIX separators: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise FixtureError(f"{field} is not a safe project-relative path: {raw!r}")
    if path.parts[0].casefold() == ".git":
        raise FixtureError(f"{field} may not address .git: {raw!r}")
    return path.as_posix()


def _safe_source(directory: Path, raw: Any) -> Path:
    relative = _safe_relative(raw, field="source")
    if relative.startswith("@shared/"):
        relative = relative[len("@shared/") :]
        base = ROOT / "shared"
    else:
        base = directory
    candidate = (base / Path(*PurePosixPath(relative).parts)).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise FixtureError(f"source escapes scenario: {raw!r}") from exc
    if not candidate.is_file():
        raise FixtureError(f"source is not a file: {raw!r}")
    return candidate


def _manifest_path(directory: Path, raw: Any, *, owner: Path) -> Path:
    relative = _safe_relative(raw, field=f"manifest reference in {owner.name}")
    candidate = (directory / Path(*PurePosixPath(relative).parts)).resolve()
    try:
        candidate.relative_to(directory.resolve())
    except ValueError as exc:
        raise FixtureError(f"manifest escapes scenario: {raw!r}") from exc
    return candidate


def _entry_bytes(directory: Path, operation: Mapping[str, Any]) -> bytes:
    carriers = [key for key in ("source", "sources", "base64") if key in operation]
    if len(carriers) != 1:
        raise FixtureError("write requires exactly one of source, sources, or base64")
    if carriers[0] == "source":
        return _safe_source(directory, operation["source"]).read_bytes()
    if carriers[0] == "sources":
        sources = operation["sources"]
        if not isinstance(sources, list) or not sources:
            raise FixtureError("sources must be a non-empty array")
        return b"".join(_safe_source(directory, source).read_bytes() for source in sources)
    encoded = operation["base64"]
    if not isinstance(encoded, str):
        raise FixtureError("base64 must be a string")
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise FixtureError("invalid base64 fixture bytes") from exc


def _resolve_tree(
    directory: Path,
    manifest_path: Path,
    *,
    stack: Optional[List[Path]] = None,
) -> Tree:
    stack = [] if stack is None else stack
    manifest_path = manifest_path.resolve()
    if manifest_path in stack:
        chain = " -> ".join(path.name for path in stack + [manifest_path])
        raise FixtureError(f"tree manifest cycle: {chain}")
    try:
        manifest_path.relative_to(directory.resolve())
    except ValueError as exc:
        raise FixtureError(f"tree manifest escapes scenario: {manifest_path}") from exc

    manifest = _read_json(manifest_path)
    if manifest.get("spec") != TREE_SPEC:
        raise FixtureError(f"{manifest_path}: expected spec {TREE_SPEC}")
    tree: Tree = {}
    base = manifest.get("base")
    if base is not None:
        base_path = _manifest_path(directory, base, owner=manifest_path)
        tree.update(_resolve_tree(directory, base_path, stack=stack + [manifest_path]))

    operations = manifest.get("operations")
    if not isinstance(operations, list):
        raise FixtureError(f"{manifest_path}: operations must be an array")
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise FixtureError(f"{manifest_path}: operation {index} must be an object")
        kind = operation.get("op")
        path = _safe_relative(operation.get("path"), field=f"{manifest_path}: path")
        if kind == "delete":
            prefix = path + "/"
            for existing in list(tree):
                if existing == path or existing.startswith(prefix):
                    del tree[existing]
            continue
        if kind == "write":
            mode = operation.get("mode")
            if mode not in {"100644", "100755"}:
                raise FixtureError(f"{manifest_path}: invalid mode for {path}: {mode!r}")
            tree[path] = {
                "type": "file",
                "bytes": _entry_bytes(directory, operation),
                "mode": mode,
            }
            continue
        if kind == "symlink":
            target = operation.get("target")
            target_type = operation.get("target_type", "file")
            if not isinstance(target, str) or not target:
                raise FixtureError(f"{manifest_path}: symlink target must be non-empty")
            if os.path.isabs(target):
                raise FixtureError(f"{manifest_path}: symlink target must be relative")
            if target_type not in {"file", "directory"}:
                raise FixtureError(f"{manifest_path}: invalid symlink target_type")
            tree[path] = {
                "type": "symlink",
                "target": target.replace("\\", "/"),
                "target_type": target_type,
            }
            continue
        raise FixtureError(f"{manifest_path}: unsupported operation {kind!r}")

    for path in tree:
        prefix = path + "/"
        if any(other.startswith(prefix) for other in tree):
            raise FixtureError(f"{manifest_path}: non-directory entry has descendants: {path}")
    return tree


def _tree_for(directory: Path, scenario: Mapping[str, Any], key: str) -> Tree:
    raw = scenario.get(key)
    if not isinstance(raw, str):
        raise FixtureError(f"{scenario.get('name')}: {key} must name a tree manifest")
    return _resolve_tree(directory, _manifest_path(directory, raw, owner=directory / "scenario.json"))


def _is_reparse(path: Path) -> bool:
    try:
        attributes = os.lstat(path).st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _is_link(path: Path) -> bool:
    return path.is_symlink() or _is_reparse(path)


def _is_directory_status(status: os.stat_result) -> bool:
    if stat.S_ISDIR(status.st_mode):
        return True
    attributes = getattr(status, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_DIRECTORY", 0))


def _make_writable(path: Path, status: os.stat_result) -> None:
    try:
        mode = status.st_mode | stat.S_IWUSR
        if _is_directory_status(status):
            mode |= stat.S_IXUSR
        os.chmod(path, mode)
    except OSError as exc:
        raise FixtureError(f"cannot make cleanup target writable: {path}: {exc}") from exc


def _remove_link_no_follow(path: Path, status: os.stat_result) -> None:
    try:
        if _is_directory_status(status):
            os.rmdir(path)
        else:
            path.unlink()
    except OSError as exc:
        raise FixtureError(f"cannot remove link/reparse point: {path}: {exc}") from exc


def _strict_remove_tree(root: Path) -> None:
    """Remove one known tree without traversing any link or reparse point."""

    try:
        root_status = os.lstat(root)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise FixtureError(f"cannot inspect cleanup root {root}: {exc}") from exc
    if stat.S_ISLNK(root_status.st_mode) or _is_reparse(root):
        raise FixtureError(f"cleanup root may not be a link or reparse point: {root}")
    if not _is_directory_status(root_status):
        raise FixtureError(f"cleanup root is not a directory: {root}")

    def remove_directory(directory: Path) -> None:
        try:
            with os.scandir(directory) as iterator:
                children = list(iterator)
        except OSError as exc:
            raise FixtureError(f"cannot enumerate cleanup directory {directory}: {exc}") from exc
        for item in children:
            path = Path(item.path)
            try:
                status = item.stat(follow_symlinks=False)
            except OSError as exc:
                raise FixtureError(f"cannot inspect cleanup entry {path}: {exc}") from exc
            attributes = getattr(status, "st_file_attributes", 0)
            is_reparse = bool(
                attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            )
            if stat.S_ISLNK(status.st_mode) or is_reparse:
                _remove_link_no_follow(path, status)
                continue
            if _is_directory_status(status):
                remove_directory(path)
                continue
            _make_writable(path, status)
            try:
                path.unlink()
            except OSError as exc:
                raise FixtureError(f"cannot remove cleanup entry {path}: {exc}") from exc
        try:
            status = os.lstat(directory)
        except OSError as exc:
            raise FixtureError(f"cannot re-inspect cleanup directory {directory}: {exc}") from exc
        _make_writable(directory, status)
        try:
            os.rmdir(directory)
        except OSError as exc:
            raise FixtureError(f"cannot remove cleanup directory {directory}: {exc}") from exc

    remove_directory(root)
    if os.path.lexists(root):
        raise FixtureError(f"cleanup target still exists after removal: {root}")


def _remove_entry(path: Path) -> None:
    if _is_link(path):
        try:
            status = os.lstat(path)
        except OSError as exc:
            raise FixtureError(f"cannot inspect entry for removal {path}: {exc}") from exc
        _remove_link_no_follow(path, status)
    elif path.is_dir():
        _strict_remove_tree(path)
    else:
        try:
            status = os.lstat(path)
        except OSError as exc:
            raise FixtureError(f"cannot inspect entry for removal {path}: {exc}") from exc
        _make_writable(path, status)
        try:
            path.unlink()
        except OSError as exc:
            raise FixtureError(f"cannot remove entry {path}: {exc}") from exc


def _walk_entries(root: Path) -> Dict[str, Path]:
    result: Dict[str, Path] = {}

    def visit(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            for item in iterator:
                if directory == root and item.name == ".git":
                    continue
                path = Path(item.path)
                relative = path.relative_to(root).as_posix()
                if item.is_symlink() or _is_reparse(path):
                    result[relative] = path
                elif item.is_dir(follow_symlinks=False):
                    visit(path)
                else:
                    result[relative] = path

    visit(root)
    return result


def _safe_destination(root: Path, relative: str) -> Path:
    path = root.joinpath(*PurePosixPath(relative).parts)
    parent = path.parent
    while parent != root:
        if parent.exists() and _is_link(parent):
            raise FixtureError(f"refusing to traverse link while writing {relative}")
        parent = parent.parent
    return path


def _make_link(root: Path, path: Path, entry: Mapping[str, Any]) -> None:
    target = str(entry["target"])
    target_is_directory = entry["target_type"] == "directory"
    try:
        path.symlink_to(target, target_is_directory=target_is_directory)
        return
    except OSError as first_error:
        if os.name != "nt" or not target_is_directory:
            raise FixtureError(f"cannot create fixture symlink {path}: {first_error}") from first_error

    target_path = (path.parent / target).resolve()
    try:
        target_path.relative_to(root.resolve())
    except ValueError as exc:
        raise FixtureError(f"junction target escapes worktree: {target}") from exc
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(path), str(target_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        raise FixtureError(
            f"cannot create fixture junction {path}: {completed.stdout.strip()}"
        )


def _materialize_tree(root: Path, tree: Mapping[str, Entry]) -> None:
    existing = _walk_entries(root) if root.exists() else {}
    for relative in sorted(set(existing) - set(tree), reverse=True):
        _remove_entry(existing[relative])

    ordered_entries = sorted(
        tree.items(),
        key=lambda item: (item[1]["type"] == "symlink", item[0]),
    )
    for relative, entry in ordered_entries:
        destination = _safe_destination(root, relative)
        if destination.exists() or _is_link(destination):
            _remove_entry(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if entry["type"] == "file":
            destination.write_bytes(entry["bytes"])
            if os.name != "nt":
                destination.chmod(0o755 if entry["mode"] == "100755" else 0o644)
        else:
            _make_link(root, destination, entry)


def _run_git(root: Path, *arguments: str) -> str:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_EMAIL": "bridge-fixture.invalid@example.invalid",
            "GIT_AUTHOR_NAME": "Bridge Fixture",
            "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+00:00",
            "GIT_COMMITTER_EMAIL": "bridge-fixture.invalid@example.invalid",
            "GIT_COMMITTER_NAME": "Bridge Fixture",
            "GIT_COMMITTER_DATE": "2001-01-01T00:00:00+00:00",
            "GIT_DEFAULT_HASH": "sha1",
        }
    )
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise FixtureError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def _is_within_or_equal(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _os_temp_root() -> Path:
    raw = Path(tempfile.gettempdir())
    try:
        status = os.lstat(raw)
    except OSError as exc:
        raise FixtureError(f"cannot inspect OS temporary directory {raw}: {exc}") from exc
    if stat.S_ISLNK(status.st_mode) or _is_reparse(raw):
        raise FixtureError(f"OS temporary directory may not be a link/reparse point: {raw}")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise FixtureError(f"cannot resolve OS temporary directory {raw}: {exc}") from exc
    if not resolved.is_dir():
        raise FixtureError(f"OS temporary path is not a directory: {resolved}")
    repository = REPO_ROOT.resolve()
    fixture_source = (REPO_ROOT / "fixtures").resolve()
    if _is_within_or_equal(resolved, repository):
        raise FixtureError(
            f"OS temporary directory may not be inside the repository: {resolved}"
        )
    if _is_within_or_equal(resolved, fixture_source):
        raise FixtureError(
            f"OS temporary directory may not be inside fixture source: {resolved}"
        )
    return resolved


def _scenario_temp_identity(name: str) -> Optional[Tuple[str, str]]:
    for scenario in sorted(
        (path.name for path in SCENARIOS.iterdir() if path.is_dir()),
        key=len,
        reverse=True,
    ):
        prefix = f"bridge-sync-{scenario}-"
        if name.startswith(prefix):
            nonce = name[len(prefix) :]
            if NONCE_PATTERN.fullmatch(nonce):
                return scenario, nonce
    return None


def _validate_temp_location(
    path: Path,
    *,
    expected_scenario: Optional[str] = None,
) -> Tuple[Path, str, str]:
    os_temp = _os_temp_root()
    absolute = Path(os.path.abspath(path))
    if absolute == os_temp:
        raise FixtureError("worktree may not be the OS temporary root")
    try:
        parent = absolute.parent.resolve(strict=True)
    except OSError as exc:
        raise FixtureError(f"cannot resolve worktree parent {absolute.parent}: {exc}") from exc
    if parent != os_temp:
        raise FixtureError(
            "worktree must be a direct child of the OS temporary directory: "
            f"{absolute}"
        )
    identity = _scenario_temp_identity(absolute.name)
    if identity is None:
        raise FixtureError(f"worktree name is not a harness scenario name: {absolute.name}")
    scenario, nonce = identity
    if expected_scenario is not None and scenario != expected_scenario:
        raise FixtureError(
            f"worktree name belongs to {scenario}, expected {expected_scenario}"
        )
    try:
        status = os.lstat(absolute)
    except OSError as exc:
        raise FixtureError(f"cannot inspect worktree {absolute}: {exc}") from exc
    if stat.S_ISLNK(status.st_mode) or _is_reparse(absolute):
        raise FixtureError(f"worktree may not be a link/reparse point: {absolute}")
    if not _is_directory_status(status):
        raise FixtureError(f"worktree is not a directory: {absolute}")
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise FixtureError(f"cannot resolve worktree {absolute}: {exc}") from exc
    if resolved.parent != os_temp:
        raise FixtureError(f"resolved worktree escaped the OS temporary root: {resolved}")
    repository = REPO_ROOT.resolve()
    fixture_source = (REPO_ROOT / "fixtures").resolve()
    if _is_within_or_equal(resolved, repository) or _is_within_or_equal(
        resolved, fixture_source
    ):
        raise FixtureError(f"worktree may not be inside repository source: {resolved}")
    return resolved, scenario, nonce


def _require_plain_entry(path: Path, *, directory: bool) -> None:
    try:
        status = os.lstat(path)
    except OSError as exc:
        raise FixtureError(f"cannot inspect fixture control path {path}: {exc}") from exc
    if stat.S_ISLNK(status.st_mode) or _is_reparse(path):
        raise FixtureError(f"fixture control path may not be a link/reparse point: {path}")
    if directory != _is_directory_status(status):
        kind = "directory" if directory else "regular file"
        raise FixtureError(f"fixture control path is not a {kind}: {path}")
    if not directory and not stat.S_ISREG(status.st_mode):
        raise FixtureError(f"fixture control path is not a regular file: {path}")


def _validate_commit_map(raw: Any, *, field: str) -> Dict[str, str]:
    if not isinstance(raw, dict):
        raise FixtureError(f"fixture marker {field} must be an object")
    result: Dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key or not isinstance(value, str):
            raise FixtureError(f"fixture marker {field} has an invalid entry")
        if not HASH_PATTERN.fullmatch(value):
            raise FixtureError(f"fixture marker {field}.{key} is not a full object id")
        result[key] = value
    return result


def _fixture_root(
    path: Path,
    *,
    expected_scenario: Optional[str] = None,
) -> Tuple[Path, Dict[str, Any]]:
    root, scenario, nonce = _validate_temp_location(
        path,
        expected_scenario=expected_scenario,
    )
    git_directory = root / ".git"
    _require_plain_entry(git_directory, directory=True)
    for relative, directory in (
        ("HEAD", False),
        ("config", False),
        ("objects", True),
        (MARKER_NAME, False),
    ):
        _require_plain_entry(git_directory / relative, directory=directory)
    marker = _read_json(git_directory / MARKER_NAME)
    if marker.get("spec") != MARKER_SPEC:
        raise FixtureError(f"fixture marker must declare {MARKER_SPEC}")
    if marker.get("scenario") != scenario:
        raise FixtureError("fixture marker scenario does not match the directory name")
    if marker.get("nonce") != nonce:
        raise FixtureError("fixture marker nonce does not match the directory name")
    marker_root = marker.get("resolved_root")
    if not isinstance(marker_root, str):
        raise FixtureError("fixture marker resolved_root must be a string")
    try:
        recorded_root = Path(marker_root).resolve(strict=True)
    except OSError as exc:
        raise FixtureError(f"cannot resolve fixture marker root {marker_root}: {exc}") from exc
    if recorded_root != root:
        raise FixtureError("fixture marker resolved_root does not match the worktree")
    baseline_commit = marker.get("baseline_commit")
    if not isinstance(baseline_commit, str) or not HASH_PATTERN.fullmatch(
        baseline_commit
    ):
        raise FixtureError("fixture marker baseline_commit is not a full object id")
    _validate_commit_map(marker.get("history_commits"), field="history_commits")
    checkpoints = marker.get("checkpoints", {})
    _validate_commit_map(checkpoints, field="checkpoints")
    return root, marker


def _plain_children(directory: Path) -> List[Tuple[Path, os.stat_result]]:
    try:
        with os.scandir(directory) as iterator:
            entries = list(iterator)
    except OSError as exc:
        raise FixtureError(f"cannot enumerate cleanup candidate {directory}: {exc}") from exc
    result: List[Tuple[Path, os.stat_result]] = []
    for entry in entries:
        path = Path(entry.path)
        try:
            status = entry.stat(follow_symlinks=False)
        except OSError as exc:
            raise FixtureError(f"cannot inspect cleanup candidate entry {path}: {exc}") from exc
        attributes = getattr(status, "st_file_attributes", 0)
        if stat.S_ISLNK(status.st_mode) or bool(
            attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise FixtureError(
                f"cleanup candidate contains a link/reparse control entry: {path}"
            )
        result.append((path, status))
    return result


def _validate_legacy_marker(
    root: Path,
    *,
    scenario: str,
) -> None:
    git_directory = root / ".git"
    _require_plain_entry(git_directory, directory=True)
    for relative, directory in (
        ("HEAD", False),
        ("config", False),
        ("objects", True),
        (MARKER_NAME, False),
    ):
        _require_plain_entry(git_directory / relative, directory=directory)
    marker = _read_json(git_directory / MARKER_NAME)
    if marker.get("spec") is not None:
        raise FixtureError("cleanup candidate is not a legacy fixture marker")
    if marker.get("scenario") != scenario:
        raise FixtureError("legacy fixture marker scenario does not match directory")
    baseline = marker.get("baseline_commit")
    if not isinstance(baseline, str) or not HASH_PATTERN.fullmatch(baseline):
        raise FixtureError("legacy fixture marker baseline is invalid")
    _validate_commit_map(marker.get("history_commits"), field="history_commits")


def _validate_loose_object_residue(root: Path) -> None:
    root_children = _plain_children(root)
    if len(root_children) != 1 or root_children[0][0].name != ".git":
        raise FixtureError(
            f"legacy residue must contain only .git at its root: {root}"
        )
    if not _is_directory_status(root_children[0][1]):
        raise FixtureError(f"legacy residue .git is not a directory: {root}")
    git_directory = root / ".git"
    git_children = _plain_children(git_directory)
    if len(git_children) != 1 or git_children[0][0].name != "objects":
        raise FixtureError(
            f"legacy residue .git must contain only loose objects: {root}"
        )
    if not _is_directory_status(git_children[0][1]):
        raise FixtureError(f"legacy residue objects is not a directory: {root}")
    object_count = 0
    for fanout, fanout_status in _plain_children(git_directory / "objects"):
        if not _is_directory_status(fanout_status) or not re.fullmatch(
            r"[0-9a-f]{2}", fanout.name
        ):
            raise FixtureError(f"legacy residue has an invalid object fanout: {fanout}")
        objects = _plain_children(fanout)
        if not objects:
            raise FixtureError(f"legacy residue has an empty object fanout: {fanout}")
        for object_path, object_status in objects:
            if _is_directory_status(object_status) or not stat.S_ISREG(
                object_status.st_mode
            ):
                raise FixtureError(
                    f"legacy residue object is not a regular file: {object_path}"
                )
            if not re.fullmatch(r"[0-9a-f]{38}", object_path.name):
                raise FixtureError(
                    f"legacy residue has an invalid loose object name: {object_path}"
                )
            object_count += 1
    if object_count == 0:
        raise FixtureError(f"legacy residue has no loose Git objects: {root}")


def _cleanup_candidate(path: Path) -> Tuple[Path, str]:
    root, scenario, _ = _validate_temp_location(path)
    marker_path = root / ".git" / MARKER_NAME
    if os.path.lexists(marker_path):
        _require_plain_entry(marker_path, directory=False)
        marker = _read_json(marker_path)
        if marker.get("spec") == MARKER_SPEC:
            _fixture_root(root, expected_scenario=scenario)
            return root, "current-marked-worktree"
        _validate_legacy_marker(root, scenario=scenario)
        return root, "legacy-marked-worktree"
    _validate_loose_object_residue(root)
    return root, "legacy-loose-object-residue"


def _create_worktree(name: str) -> Tuple[Path, str]:
    directory, scenario = _load_scenario(name)
    baseline = _tree_for(directory, scenario, "baseline")
    input_tree = _tree_for(directory, scenario, "input")
    os_temp = _os_temp_root()
    root = Path(
        tempfile.mkdtemp(
            prefix=f"bridge-sync-{name}-",
            dir=os_temp,
        )
    )
    CREATED_TEMP_ROOTS.add(Path(os.path.abspath(root)))
    try:
        resolved_root, actual_scenario, nonce = _validate_temp_location(
            root,
            expected_scenario=name,
        )
        if actual_scenario != name:
            raise FixtureError(f"unexpected worktree scenario: {actual_scenario}")
        root = resolved_root
        _run_git(root, "init", "-q")
        _run_git(root, "config", "user.name", "Bridge Fixture")
        _run_git(root, "config", "user.email", "bridge-fixture.invalid@example.invalid")
        _run_git(root, "config", "core.autocrlf", "false")
        _run_git(root, "config", "core.safecrlf", "true")
        history = scenario.get("history")
        history_commits: Dict[str, str] = {}
        if history is None:
            _materialize_tree(root, baseline)
            _run_git(root, "add", "-A")
            _run_git(
                root,
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "fixture: confirmed managed synchronized baseline",
            )
            baseline_commit = _run_git(root, "rev-parse", "HEAD")
        else:
            baseline_commit, history_commits = _create_history(
                root,
                directory,
                history,
            )
        _write_json(
            root / ".git" / MARKER_NAME,
            {
                "spec": MARKER_SPEC,
                "scenario": name,
                "nonce": nonce,
                "resolved_root": str(root),
                "baseline_commit": baseline_commit,
                "history_commits": history_commits,
            },
        )
        _materialize_tree(root, input_tree)
        _apply_declared_index_modes(root, input_tree)
        return root, baseline_commit
    except Exception as original:
        try:
            _strict_remove_tree(root)
        except Exception as cleanup_error:
            raise FixtureError(
                f"worktree setup failed ({original}); strict cleanup also failed: "
                f"{cleanup_error}"
            ) from cleanup_error
        raise


def _apply_declared_index_modes(root: Path, tree: Mapping[str, Entry]) -> None:
    tracked_raw = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if tracked_raw.returncode:
        raise FixtureError(
            f"git ls-files failed: {tracked_raw.stderr.decode('utf-8', errors='replace')}"
        )
    tracked = {
        item.decode("utf-8").replace("\\", "/")
        for item in tracked_raw.stdout.split(b"\0")
        if item
    }
    for relative, entry in sorted(tree.items()):
        if entry["type"] != "file" or relative not in tracked:
            continue
        flag = "+x" if entry["mode"] == "100755" else "-x"
        _run_git(root, "update-index", f"--chmod={flag}", "--", relative)


def _create_history(
    root: Path,
    directory: Path,
    history: Any,
) -> Tuple[str, Dict[str, str]]:
    if not isinstance(history, dict):
        raise FixtureError("history must be an object")
    commits_raw = history.get("commits")
    head_id = history.get("head")
    if not isinstance(commits_raw, list) or not commits_raw:
        raise FixtureError("history.commits must be a non-empty array")
    if not isinstance(head_id, str) or not head_id:
        raise FixtureError("history.head must be a non-empty string")
    commits: Dict[str, str] = {}
    for index, item in enumerate(commits_raw):
        if not isinstance(item, dict):
            raise FixtureError(f"history commit {index} must be an object")
        commit_id = item.get("id")
        tree_raw = item.get("tree")
        parents = item.get("parents")
        if not isinstance(commit_id, str) or not commit_id or commit_id in commits:
            raise FixtureError(f"history commit {index} has an invalid id")
        if not isinstance(parents, list) or not all(
            isinstance(parent, str) and parent in commits for parent in parents
        ):
            raise FixtureError(
                f"history commit {commit_id} must name earlier declared parents"
            )
        manifest = _manifest_path(
            directory,
            tree_raw,
            owner=directory / "scenario.json",
        )
        tree = _resolve_tree(directory, manifest)
        _materialize_tree(root, tree)
        _run_git(root, "add", "-A")
        tree_id = _run_git(root, "write-tree")
        arguments = ["commit-tree", tree_id]
        for parent in parents:
            arguments.extend(["-p", commits[parent]])
        message = item.get("message", f"fixture history: {commit_id}")
        if not isinstance(message, str) or not message:
            raise FixtureError(f"history commit {commit_id} has an invalid message")
        arguments.extend(["-m", message])
        commits[commit_id] = _run_git(root, *arguments)
    if head_id not in commits:
        raise FixtureError(f"history.head does not name a commit: {head_id}")
    _run_git(root, "update-ref", "refs/heads/main", commits[head_id])
    _run_git(root, "symbolic-ref", "HEAD", "refs/heads/main")
    _run_git(root, "reset", "--hard", "-q", commits[head_id])
    return commits[head_id], commits


def _link_target_matches(root: Path, path: Path, expected: Mapping[str, Any]) -> bool:
    target = str(expected["target"])
    expected_resolved = (path.parent / target).resolve()
    try:
        actual_resolved = path.resolve()
    except OSError:
        return False
    return actual_resolved == expected_resolved


def _compare_tree(root: Path, expected: Mapping[str, Entry]) -> List[str]:
    actual = _walk_entries(root)
    errors: List[str] = []
    for relative in sorted(set(actual) - set(expected)):
        errors.append(f"extra: {relative}")
    for relative in sorted(set(expected) - set(actual)):
        errors.append(f"missing: {relative}")
    for relative in sorted(set(actual) & set(expected)):
        path = actual[relative]
        entry = expected[relative]
        if entry["type"] == "symlink":
            if not _is_link(path):
                errors.append(f"type: {relative} (expected symlink/reparse point)")
            elif not _link_target_matches(root, path, entry):
                errors.append(f"link-target: {relative}")
            continue
        if _is_link(path) or not path.is_file():
            errors.append(f"type: {relative} (expected regular file)")
            continue
        if path.read_bytes() != entry["bytes"]:
            errors.append(f"bytes: {relative}")
        if os.name != "nt":
            executable = bool(path.stat().st_mode & 0o111)
            expected_executable = entry["mode"] == "100755"
            if executable != expected_executable:
                errors.append(f"mode: {relative} (expected {entry['mode']})")
    return errors


def _expectation(
    directory: Path,
    scenario: Mapping[str, Any],
    expectation_id: str,
) -> Mapping[str, Any]:
    expectations = scenario.get("expectations")
    if not isinstance(expectations, list):
        raise FixtureError("expectations must be an array")
    matches = [
        item
        for item in expectations
        if isinstance(item, dict) and item.get("id") == expectation_id
    ]
    if len(matches) != 1:
        raise FixtureError(
            f"{scenario.get('name')}: expected one expectation {expectation_id!r}"
        )
    return matches[0]


def _expectation_tree(
    directory: Path,
    scenario: Mapping[str, Any],
    expectation_id: str,
) -> Tree:
    expectation = _expectation(directory, scenario, expectation_id)
    raw = expectation.get("post_state")
    if not isinstance(raw, str):
        raise FixtureError(f"{expectation_id}: post_state must name a tree manifest")
    manifest = _manifest_path(directory, raw, owner=directory / "scenario.json")
    return _resolve_tree(directory, manifest)


def _validate_text_files() -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        data = path.read_bytes()
        relative = path.relative_to(REPO_ROOT).as_posix()
        if data.startswith(b"\xef\xbb\xbf"):
            raise FixtureError(f"unexpected UTF-8 BOM: {relative}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FixtureError(f"invalid UTF-8 text: {relative}") from exc
        if b"\r" in data:
            raise FixtureError(f"non-LF line ending: {relative}")
        if not data.endswith(b"\n") or data.endswith(b"\n\n"):
            raise FixtureError(f"expected exactly one final newline: {relative}")
        for number, line in enumerate(text.splitlines(), 1):
            if line.endswith((" ", "\t")):
                raise FixtureError(f"trailing whitespace: {relative}:{number}")


def _skill_names(tree: Mapping[str, Entry]) -> List[str]:
    names = set()
    for relative in tree:
        parts = PurePosixPath(relative).parts
        for prefix in ((".claude", "skills"), (".agents", "skills")):
            if len(parts) >= 3 and parts[:2] == prefix:
                names.add(parts[2])
    return sorted(names)


def _validate_inert_skills(
    name: str,
    trees: Iterable[Mapping[str, Entry]],
    root_overrides: Mapping[str, Any],
) -> None:
    for tree in trees:
        skill_names = _skill_names(tree)
        if not skill_names:
            continue
        settings_entry = tree.get(".claude/settings.json")
        if not settings_entry or settings_entry["type"] != "file":
            raise FixtureError(f"{name}: tree with skills lacks .claude/settings.json")
        try:
            settings = json.loads(settings_entry["bytes"].decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise FixtureError(f"{name}: invalid materialized settings JSON") from exc
        overrides = settings.get("skillOverrides", {})
        for skill_name in skill_names:
            if not skill_name.startswith("fixture-"):
                raise FixtureError(f"{name}: non-inert skill name {skill_name}")
            if overrides.get(skill_name) != "off":
                raise FixtureError(f"{name}: project override missing for {skill_name}")
            if root_overrides.get(skill_name) != "off":
                raise FixtureError(f"{name}: root override missing for {skill_name}")
            for host_root in (".claude/skills", ".agents/skills"):
                skill_root = f"{host_root}/{skill_name}"
                skill_md = tree.get(f"{skill_root}/SKILL.md")
                if skill_md is None:
                    continue
                policy = tree.get(f"{skill_root}/agents/openai.yaml")
                if not policy or policy["type"] != "file" or policy["bytes"] != INERT_POLICY:
                    raise FixtureError(f"{name}: inert policy missing for {skill_root}")
                if b"inert" not in skill_md["bytes"].lower():
                    raise FixtureError(f"{name}: skill body is not explicitly inert: {skill_root}")


def _validate_plan_row_semantics(
    path: Path,
    *,
    phase: str,
    state: str,
    action: str,
    direction: str,
    outcome: str,
) -> None:
    actions_by_state = {
        "unchanged": {"unchanged"},
        "source-only": {"delete", "rename", "update"},
        "projection-only": {"adopt", "delete", "rename", "reproject"},
        "both-changed": {"conflict"},
        "no-baseline": {"annex", "annex-or-keep", "create", "keep"},
        "contract-migration": {"migrate"},
        "offboarding": {"offboard", "restore"},
        "blocked": {"repair", "resolve-blocker"},
    }
    if action not in actions_by_state[state]:
        raise FixtureError(
            f"{path}: action {action} is invalid for state {state}"
        )
    fixed_directions = {
        "adopt": "projection-to-source",
        "annex": "projection-to-source",
        "annex-or-keep": "user-decision",
        "conflict": "user-decision",
        "create": "source-to-projection",
        "keep": "user-decision",
        "migrate": "user-decision",
        "offboard": "user-decision",
        "repair": "user-decision",
        "reproject": "source-to-projection",
        "resolve-blocker": "-",
        "restore": "user-decision",
        "unchanged": "-",
        "update": "source-to-projection",
    }
    wanted_direction = fixed_directions.get(action)
    if wanted_direction is not None and direction != wanted_direction:
        raise FixtureError(
            f"{path}: action {action} requires direction {wanted_direction}"
        )
    if action in {"delete", "rename"} and direction not in {
        "source-to-projection",
        "projection-to-source",
    }:
        raise FixtureError(f"{path}: action {action} requires an intent direction")

    fixed_outcomes = {
        "annex-or-keep": "deferred",
        "conflict": "deferred",
        "keep": "deferred",
        "resolve-blocker": "blocked",
        "unchanged": "unchanged",
    }
    wanted_outcome = fixed_outcomes.get(action)
    if wanted_outcome is not None and outcome != wanted_outcome:
        raise FixtureError(
            f"{path}: action {action} requires outcome {wanted_outcome}"
        )
    mutating = action in {
        "adopt",
        "annex",
        "create",
        "delete",
        "migrate",
        "offboard",
        "repair",
        "rename",
        "reproject",
        "restore",
        "update",
    }
    if mutating:
        allowed = (
            {"planned"}
            if phase == "pre-write"
            else {
                "applied",
                "compensated",
                "failed",
                "not-attempted",
                "partial",
                "rolled-back",
            }
        )
        if outcome not in allowed:
            raise FixtureError(
                f"{path}: {phase} action {action} has invalid outcome {outcome}"
            )
    if phase == "pre-write" and outcome in {
        "applied",
        "compensated",
        "failed",
        "not-attempted",
        "partial",
        "rolled-back",
    }:
        raise FixtureError(f"{path}: pre-write plan has post-write outcome {outcome}")
    if phase == "post-write" and outcome == "planned":
        raise FixtureError(f"{path}: post-write plan may not retain planned outcome")


def _parse_plan(path: Path, *, expectation: bool) -> Dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise FixtureError(f"cannot read sync plan {path}: {exc}") from exc
    if not lines or lines[0] != "# Bridge Sync Plan":
        raise FixtureError(f"{path}: invalid plan title")
    headers: Dict[str, str] = {}
    for line in lines:
        if line.startswith("- ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            if key in headers:
                raise FixtureError(f"{path}: duplicate header {key}")
            headers[key] = value
        if line == "## Units":
            break
    version_key = "expectation" if expectation else "spec"
    forbidden_version_key = "spec" if expectation else "expectation"
    required = {
        version_key: PLAN_SPEC,
        "contracts": PLAN_CONTRACTS,
    }
    for key, value in required.items():
        if headers.get(key) != value:
            raise FixtureError(f"{path}: expected - {key}: {value}")
    if forbidden_version_key in headers:
        raise FixtureError(f"{path}: unexpected header {forbidden_version_key}")
    for key in ("project", "scan root"):
        if not headers.get(key):
            raise FixtureError(f"{path}: missing non-empty header {key}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", headers.get("date", "")):
        raise FixtureError(f"{path}: date must use YYYY-MM-DD")
    if headers.get("phase") not in {"pre-write", "post-write"}:
        raise FixtureError(f"{path}: invalid phase")
    if headers.get("onboarding") not in {"onboarded", "bootstrap-required", "blocked"}:
        raise FixtureError(f"{path}: invalid onboarding")
    if headers.get("authorization") not in {
        "required",
        "confirmed",
        "not-applicable",
    }:
        raise FixtureError(f"{path}: invalid authorization")
    try:
        table_index = lines.index(PLAN_HEADER)
    except ValueError as exc:
        raise FixtureError(f"{path}: missing exact Units header") from exc
    if table_index + 1 >= len(lines) or lines[table_index + 1] != PLAN_SEPARATOR:
        raise FixtureError(f"{path}: invalid Units separator")
    units: List[str] = []
    rows: List[Tuple[str, ...]] = []
    row_index = table_index + 2
    while row_index < len(lines) and lines[row_index].startswith("| "):
        row = lines[row_index]
        parts = row.split("|")
        if len(parts) != 10 or parts[0] or parts[-1]:
            raise FixtureError(f"{path}: malformed unit row {row!r}")
        cells = [part[1:-1] for part in parts[1:-1]]
        if any(not part.startswith(" ") or not part.endswith(" ") for part in parts[1:-1]):
            raise FixtureError(f"{path}: unit cells need exact one-space padding")
        unit, baseline, state, action, direction, outcome, tier, annotations = cells
        if unit != "onboarding/covenant" and not unit.startswith("skills/"):
            raise FixtureError(f"{path}: invalid unit {unit}")
        if baseline != "-" and not HASH_PATTERN.fullmatch(baseline):
            raise FixtureError(f"{path}: invalid baseline {baseline}")
        registries = (
            (state, PLAN_STATES, "state"),
            (action, PLAN_ACTIONS, "action"),
            (direction, PLAN_DIRECTIONS, "direction"),
            (outcome, PLAN_OUTCOMES, "outcome"),
            (tier, {"native", "-"}, "tier"),
        )
        for token, registry, label in registries:
            if token not in registry:
                raise FixtureError(f"{path}: invalid {label} {token}")
        if annotations != "-":
            annotation_tokens = annotations.split("; ")
            if annotation_tokens != sorted(annotation_tokens):
                raise FixtureError(f"{path}: annotations are not sorted")
            if any(token not in PLAN_ANNOTATIONS for token in annotation_tokens):
                raise FixtureError(f"{path}: invalid annotation")
        _validate_plan_row_semantics(
            path,
            phase=headers["phase"],
            state=state,
            action=action,
            direction=direction,
            outcome=outcome,
        )
        units.append(unit)
        rows.append(tuple(cells))
        row_index += 1
    if not units or units != sorted(units) or len(units) != len(set(units)):
        raise FixtureError(f"{path}: Units rows must be non-empty, unique, and sorted")
    try:
        warnings_index = lines.index("## Warnings")
    except ValueError as exc:
        raise FixtureError(f"{path}: missing Warnings section") from exc
    warning_section: List[str] = []
    for line in lines[warnings_index + 1 :]:
        if line.startswith("## "):
            break
        if line:
            warning_section.append(line)
    warning_lines = [line for line in warning_section if line.startswith("- ")]
    if len(warning_lines) != len(warning_section):
        raise FixtureError(f"{path}: Warnings contains a non-warning line")
    if not warning_lines:
        raise FixtureError(f"{path}: empty Warnings section")
    if warning_lines != ["- (none)"]:
        if "- (none)" in warning_lines or warning_lines != sorted(warning_lines):
            raise FixtureError(f"{path}: warnings must be sorted or exactly (none)")
        for line in warning_lines:
            if ": " not in line:
                raise FixtureError(f"{path}: malformed warning {line}")
            token, relative = line[2:].split(": ", 1)
            if token not in PLAN_WARNINGS:
                raise FixtureError(f"{path}: invalid warning {token}")
            if not relative:
                raise FixtureError(f"{path}: warning path/detail may not be empty")
    return {
        "headers": headers,
        "rows": rows,
        "warnings": warning_lines,
    }


def _expectation_plan(
    directory: Path,
    scenario: Mapping[str, Any],
    expectation: Mapping[str, Any],
) -> Dict[str, Any]:
    raw = expectation.get("plan")
    if not isinstance(raw, str):
        raise FixtureError(f"{scenario.get('name')}: expectation plan must be a path")
    plan_path = _manifest_path(directory, raw, owner=directory / "scenario.json")
    return _parse_plan(plan_path, expectation=True)


def _normalized_plan_lines(plan: Mapping[str, Any]) -> List[str]:
    headers = plan["headers"]
    result = [
        f"contracts: {headers['contracts']}",
        f"phase: {headers['phase']}",
        f"onboarding: {headers['onboarding']}",
        f"authorization: {headers['authorization']}",
        PLAN_HEADER,
        PLAN_SEPARATOR,
    ]
    result.extend("| " + " | ".join(row) + " |" for row in plan["rows"])
    result.append("## Warnings")
    result.extend(plan["warnings"])
    return result


def _compare_plans(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> List[str]:
    expected_lines = _normalized_plan_lines(expected)
    actual_lines = _normalized_plan_lines(actual)
    if expected_lines == actual_lines:
        return []
    return list(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile="expected-plan",
            tofile="actual-plan",
            lineterm="",
        )
    )


def _validate_coverage(
    name: str,
    scenario: Mapping[str, Any],
    expectations: Sequence[Mapping[str, Any]],
) -> None:
    coverage = scenario.get("coverage")
    if not isinstance(coverage, list) or not coverage or not all(
        isinstance(item, str) and TOKEN_PATTERN.fullmatch(item) for item in coverage
    ):
        raise FixtureError(f"{name}: coverage must be a non-empty token array")
    if len(coverage) != len(set(coverage)):
        raise FixtureError(f"{name}: coverage tokens must be unique")
    declared = set(coverage)
    assigned: set[str] = set()
    for expectation in expectations:
        expectation_id = expectation.get("id")
        covers = expectation.get("covers")
        if not isinstance(covers, list) or not covers or not all(
            isinstance(item, str) and TOKEN_PATTERN.fullmatch(item) for item in covers
        ):
            raise FixtureError(
                f"{name}/{expectation_id}: covers must be a non-empty token array"
            )
        if len(covers) != len(set(covers)):
            raise FixtureError(f"{name}/{expectation_id}: covers tokens must be unique")
        unknown = set(covers) - declared
        if unknown:
            raise FixtureError(
                f"{name}/{expectation_id}: covers undeclared token {sorted(unknown)[0]}"
            )
        assigned.update(covers)
    if assigned != declared:
        missing = sorted(declared - assigned)
        extra = sorted(assigned - declared)
        raise FixtureError(
            f"{name}: expectation coverage union mismatch; missing={missing}, extra={extra}"
        )
    replay = scenario.get("replay", "agent")
    if replay not in REPLAY_MODES:
        raise FixtureError(f"{name}: invalid replay mode {replay!r}")
    reason = scenario.get("replay_reason")
    if replay == "declarative-only":
        if not isinstance(reason, str) or not reason:
            raise FixtureError(f"{name}: declarative-only replay needs replay_reason")
        faults = scenario.get("faults")
        workflow = scenario.get("workflow")
        if not isinstance(faults, dict) or not faults:
            raise FixtureError(f"{name}: declarative-only scenario needs fault data")
        if not isinstance(workflow, list) or not workflow or not all(
            isinstance(item, str) and item for item in workflow
        ):
            raise FixtureError(f"{name}: declarative-only workflow must be documented")
        directory = _scenario_dir(name)
        for fault_name, fault in faults.items():
            if not isinstance(fault_name, str) or not TOKEN_PATTERN.fullmatch(fault_name):
                raise FixtureError(f"{name}: invalid declarative fault name")
            if not isinstance(fault, dict) or set(fault) != {
                "checkpoint",
                "operations",
            }:
                raise FixtureError(f"{name}: declarative fault has invalid fields")
            if not isinstance(fault["checkpoint"], str) or not fault["checkpoint"]:
                raise FixtureError(f"{name}: declarative fault checkpoint is empty")
            operations = fault["operations"]
            if not isinstance(operations, list) or not operations:
                raise FixtureError(f"{name}: declarative fault operations are empty")
            for index, operation in enumerate(operations):
                if not isinstance(operation, dict) or operation.get("op") != "write":
                    raise FixtureError(
                        f"{name}: declarative fault operation {index} must be a write"
                    )
                _safe_relative(
                    operation.get("path"),
                    field=f"{name} declarative fault path",
                )
                if operation.get("mode") not in {"100644", "100755"}:
                    raise FixtureError(
                        f"{name}: declarative fault operation {index} has invalid mode"
                    )
                _entry_bytes(directory, operation)
    elif reason is not None:
        raise FixtureError(f"{name}: replay_reason is only valid for declarative-only")
    elif "faults" in scenario or "workflow" in scenario:
        raise FixtureError(f"{name}: agent-replayable scenario may not declare a fake barrier")


def _validate_safeguards() -> None:
    matrix = _read_json(SAFEGUARDS_PATH)
    if matrix.get("spec") != SAFEGUARDS_SPEC:
        raise FixtureError(f"{SAFEGUARDS_PATH}: expected spec {SAFEGUARDS_SPEC}")
    if matrix.get("contracts") != {
        "reconciliation": "reconciliation/v1",
        "sync_plan": PLAN_SPEC,
    }:
        raise FixtureError(f"{SAFEGUARDS_PATH}: invalid contract tuple")
    schema = matrix.get("case_schema")
    if not isinstance(schema, dict):
        raise FixtureError(f"{SAFEGUARDS_PATH}: case_schema must be an object")
    required_case_fields = schema.get("required_case_fields")
    expected_required_fields = schema.get("expected_required_fields")
    if required_case_fields != ["id", "phase", "input", "requirement", "expected"]:
        raise FixtureError(f"{SAFEGUARDS_PATH}: invalid required_case_fields")
    if expected_required_fields != [
        "state",
        "action",
        "direction",
        "outcome",
        "authorization",
        "write_policy",
        "warnings",
        "invariants",
    ]:
        raise FixtureError(f"{SAFEGUARDS_PATH}: invalid expected_required_fields")
    if schema.get("additional_case_fields") is not False:
        raise FixtureError(f"{SAFEGUARDS_PATH}: additional case fields must be closed")
    if schema.get("additional_expected_fields") is not False:
        raise FixtureError(f"{SAFEGUARDS_PATH}: additional expected fields must be closed")
    if schema.get("case_order") != "id-bytewise":
        raise FixtureError(f"{SAFEGUARDS_PATH}: cases must declare bytewise ID order")
    if schema.get("id_pattern") != TOKEN_PATTERN.pattern:
        raise FixtureError(f"{SAFEGUARDS_PATH}: id_pattern is not the fixture token pattern")

    registries = {
        "state": schema.get("state_values"),
        "action": schema.get("action_values"),
        "direction": schema.get("direction_values"),
        "outcome": schema.get("outcome_values"),
        "authorization": schema.get("authorization_values"),
        "write_policy": schema.get("write_policy_values"),
        "phase": schema.get("phase_values"),
        "warnings": schema.get("warning_values"),
        "invariants": schema.get("invariant_values"),
    }
    for label, values in registries.items():
        if not isinstance(values, list) or not all(
            isinstance(item, str) for item in values
        ):
            raise FixtureError(f"{SAFEGUARDS_PATH}: {label} registry must be strings")
        if len(values) != len(set(values)):
            raise FixtureError(
                f"{SAFEGUARDS_PATH}: {label} registry must contain unique values"
            )
    if set(registries["action"]) != PLAN_ACTIONS:
        raise FixtureError(f"{SAFEGUARDS_PATH}: action registry drift")
    if set(registries["state"]) != PLAN_STATES:
        raise FixtureError(f"{SAFEGUARDS_PATH}: state registry drift")
    if set(registries["outcome"]) != PLAN_OUTCOMES:
        raise FixtureError(f"{SAFEGUARDS_PATH}: outcome registry drift")
    if set(registries["direction"]) != PLAN_DIRECTIONS:
        raise FixtureError(f"{SAFEGUARDS_PATH}: direction registry drift")
    if set(registries["warnings"]) != PLAN_WARNINGS:
        raise FixtureError(f"{SAFEGUARDS_PATH}: warning registry drift")

    cases = matrix.get("cases")
    required_ids = matrix.get("required_case_ids")
    if not isinstance(cases, list) or not cases:
        raise FixtureError(f"{SAFEGUARDS_PATH}: cases must be a non-empty array")
    if not isinstance(required_ids, list) or not all(
        isinstance(item, str) for item in required_ids
    ):
        raise FixtureError(f"{SAFEGUARDS_PATH}: required_case_ids must be strings")
    ids: List[str] = []
    expected_case_keys = set(required_case_fields)
    expected_result_keys = set(expected_required_fields)
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != expected_case_keys:
            raise FixtureError(f"{SAFEGUARDS_PATH}: case {index} has invalid fields")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not TOKEN_PATTERN.fullmatch(case_id):
            raise FixtureError(f"{SAFEGUARDS_PATH}: case {index} has invalid id")
        ids.append(case_id)
        for field in ("input", "requirement"):
            if not isinstance(case.get(field), str) or not case[field]:
                raise FixtureError(f"{SAFEGUARDS_PATH}: {case_id}.{field} is empty")
        if case.get("phase") not in registries["phase"]:
            raise FixtureError(f"{SAFEGUARDS_PATH}: {case_id} has invalid phase")
        expected = case.get("expected")
        if not isinstance(expected, dict) or set(expected) != expected_result_keys:
            raise FixtureError(f"{SAFEGUARDS_PATH}: {case_id}.expected has invalid fields")
        for field in (
            "state",
            "action",
            "direction",
            "outcome",
            "authorization",
            "write_policy",
        ):
            if expected.get(field) not in registries[field]:
                raise FixtureError(
                    f"{SAFEGUARDS_PATH}: {case_id}.expected.{field} is invalid"
                )
        _validate_plan_row_semantics(
            SAFEGUARDS_PATH,
            phase=(
                "post-write"
                if case["phase"] in {"post-write", "rollback"}
                else "pre-write"
            ),
            state=expected["state"],
            action=expected["action"],
            direction=expected["direction"],
            outcome=expected["outcome"],
        )
        required_classification = REQUIRED_SAFEGUARD_CLASSIFICATIONS.get(case_id)
        if required_classification is not None:
            actual_classification = (
                expected["state"],
                expected["action"],
                expected["direction"],
                expected["outcome"],
                expected["authorization"],
            )
            if actual_classification != required_classification:
                raise FixtureError(
                    f"{SAFEGUARDS_PATH}: {case_id} classification drift; "
                    f"expected {required_classification}, got {actual_classification}"
                )
        for field in ("warnings", "invariants"):
            values = expected.get(field)
            if not isinstance(values, list) or values != sorted(set(values)):
                raise FixtureError(
                    f"{SAFEGUARDS_PATH}: {case_id}.{field} must be sorted and unique"
                )
            if any(item not in registries[field] for item in values):
                raise FixtureError(f"{SAFEGUARDS_PATH}: {case_id}.{field} is invalid")
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise FixtureError(f"{SAFEGUARDS_PATH}: case ids must be unique and sorted")
    if required_ids != ids or set(required_ids) != REQUIRED_SAFEGUARD_IDS:
        raise FixtureError(
            f"{SAFEGUARDS_PATH}: required_case_ids must equal the required M2 set"
        )


def _checkpoint_commit_for_validation(name: str, expectation_id: str) -> str:
    directory, scenario = _load_scenario(name)
    expected = _expectation_tree(directory, scenario, expectation_id)
    root, _ = _create_worktree(name)
    try:
        _materialize_tree(root, expected)
        _run_git(root, "add", "-A")
        _apply_declared_index_modes(root, expected)
        _run_git(
            root,
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            f"fixture checkpoint: {name}/{expectation_id}",
        )
        return _run_git(root, "rev-parse", "HEAD")
    finally:
        _strict_remove_tree(root)


def _resolve_baseline_ref(
    name: str,
    reference: str,
    *,
    initial: str,
    history_commits: Mapping[str, str],
    checkpoint_commits: Dict[str, str],
) -> str:
    if reference == "initial":
        return initial
    if reference.startswith("history:"):
        history_id = reference[len("history:") :]
        if history_id not in history_commits:
            raise FixtureError(f"{name}: unknown baseline_ref {reference}")
        return history_commits[history_id]
    if reference.startswith("checkpoint:"):
        expectation_id = reference[len("checkpoint:") :]
        if not expectation_id:
            raise FixtureError(f"{name}: empty checkpoint baseline_ref")
        if expectation_id not in checkpoint_commits:
            checkpoint_commits[expectation_id] = _checkpoint_commit_for_validation(
                name,
                expectation_id,
            )
        return checkpoint_commits[expectation_id]
    raise FixtureError(f"{name}: invalid baseline_ref {reference!r}")


def _validate_plan_baselines(
    name: str,
    expectation: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    initial: str,
    history_commits: Mapping[str, str],
    checkpoint_commits: Dict[str, str],
) -> None:
    raw_refs = expectation.get("baseline_ref", "initial")
    if not isinstance(raw_refs, (str, dict)):
        raise FixtureError(f"{name}: baseline_ref must be a string or unit map")
    for row in plan["rows"]:
        unit, baseline = row[0], row[1]
        if baseline == "-":
            continue
        if isinstance(raw_refs, str):
            reference = raw_refs
        else:
            reference = raw_refs.get(unit)
            if not isinstance(reference, str):
                raise FixtureError(
                    f"{name}/{expectation.get('id')}: missing baseline_ref for {unit}"
                )
        actual_commit = _resolve_baseline_ref(
            name,
            reference,
            initial=initial,
            history_commits=history_commits,
            checkpoint_commits=checkpoint_commits,
        )
        if baseline != actual_commit:
            raise FixtureError(
                f"{name}/{expectation.get('id')}: plan baseline for {unit} "
                f"is {baseline}, synthetic commit is {actual_commit}"
            )


def _validate_input_warning_evidence(
    name: str,
    expectation: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    untracked: Sequence[str],
    ignored: Sequence[str],
) -> None:
    if expectation.get("baseline_ref", "initial") != "initial":
        return
    def relevant(path: str) -> bool:
        return (
            path == "AGENTS.md"
            or path == ".claude/rules/bridge-covenant.md"
            or path.startswith(".agents/skills/")
            or path.startswith(".claude/skills/")
        )

    warning_lines = plan["warnings"]
    expected_by_token = {
        "untracked-files-included": sorted(path for path in untracked if relevant(path)),
        "ignored-files-excluded": sorted(path for path in ignored if relevant(path)),
    }
    for token, expected_paths in expected_by_token.items():
        prefix = f"- {token}: "
        actual_paths = sorted(
            line[len(prefix) :]
            for line in warning_lines
            if line.startswith(prefix)
        )
        if actual_paths != expected_paths:
            raise FixtureError(
                f"{name}/{expectation.get('id')}: {token} evidence mismatch; "
                f"expected {expected_paths}, got {actual_paths}"
            )


def _validate_scenario(name: str, root_overrides: Mapping[str, Any]) -> None:
    directory, scenario = _load_scenario(name)
    baseline = _tree_for(directory, scenario, "baseline")
    input_tree = _tree_for(directory, scenario, "input")
    trees: List[Mapping[str, Entry]] = [baseline, input_tree]
    history = scenario.get("history")
    if history is not None:
        if not isinstance(history, dict) or not isinstance(history.get("commits"), list):
            raise FixtureError(f"{name}: invalid history object")
        for commit in history["commits"]:
            if not isinstance(commit, dict):
                raise FixtureError(f"{name}: invalid history commit")
            manifest = _manifest_path(
                directory,
                commit.get("tree"),
                owner=directory / "scenario.json",
            )
            trees.append(_resolve_tree(directory, manifest))
    expectations = scenario.get("expectations")
    if not isinstance(expectations, list) or not expectations:
        raise FixtureError(f"{name}: expectations must be a non-empty array")
    ids = [item.get("id") for item in expectations if isinstance(item, dict)]
    if len(ids) != len(expectations) or len(ids) != len(set(ids)):
        raise FixtureError(f"{name}: expectation ids must be unique strings")
    _validate_coverage(name, scenario, expectations)
    plans: Dict[str, Dict[str, Any]] = {}
    for expectation in expectations:
        if not isinstance(expectation.get("id"), str):
            raise FixtureError(f"{name}: invalid expectation id")
        plans[expectation["id"]] = _expectation_plan(
            directory,
            scenario,
            expectation,
        )
        trees.append(_expectation_tree(directory, scenario, expectation["id"]))
    _validate_inert_skills(name, trees, root_overrides)

    root, baseline_commit = _create_worktree(name)
    try:
        validated_root, marker = _fixture_root(root, expected_scenario=name)
        if validated_root != root or marker["baseline_commit"] != baseline_commit:
            raise FixtureError(f"{name}: fixture marker does not bind its baseline")
        errors = _compare_tree(root, input_tree)
        if errors:
            raise FixtureError(f"{name}: materialized input mismatch: {errors}")
        if not _run_git(root, "rev-parse", "--is-inside-work-tree") == "true":
            raise FixtureError(f"{name}: disposable git repository was not initialized")
        _validate_git_expectations(root, scenario)
        _, actual_untracked, actual_ignored = _git_status_paths(root)
        for expectation in expectations:
            _validate_input_warning_evidence(
                name,
                expectation,
                plans[expectation["id"]],
                untracked=actual_untracked,
                ignored=actual_ignored,
            )
        checkpoint_commits: Dict[str, str] = {}
        history_commits = _validate_commit_map(
            marker["history_commits"],
            field="history_commits",
        )
        for expectation in expectations:
            _validate_plan_baselines(
                name,
                expectation,
                plans[expectation["id"]],
                initial=baseline_commit,
                history_commits=history_commits,
                checkpoint_commits=checkpoint_commits,
            )
    finally:
        _strict_remove_tree(root)


def _git_status_paths(root: Path) -> Tuple[List[str], List[str], List[str]]:
    output = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignored",
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if output.returncode:
        raise FixtureError(
            f"git status failed: {output.stderr.decode('utf-8', errors='replace').strip()}"
        )
    changed: List[str] = []
    untracked: List[str] = []
    ignored: List[str] = []
    records = output.stdout.split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            raise FixtureError(f"unexpected porcelain record: {record!r}")
        status = record[:2].decode("ascii")
        path = record[3:].decode("utf-8").replace("\\", "/")
        if status == "??":
            untracked.append(path)
        elif status == "!!":
            ignored.append(path)
        else:
            changed.append(path)
            if "R" in status or "C" in status:
                if index >= len(records) or not records[index]:
                    raise FixtureError("rename/copy porcelain record lacks second path")
                index += 1
    return sorted(changed), sorted(untracked), sorted(ignored)


def _validate_git_expectations(root: Path, scenario: Mapping[str, Any]) -> None:
    expected = scenario.get("git_expectations")
    if expected is None:
        return
    if not isinstance(expected, dict):
        raise FixtureError("git_expectations must be an object")
    actual_changed, actual_untracked, actual_ignored = _git_status_paths(root)
    checks = (
        ("tracked_changes", actual_changed),
        ("untracked", actual_untracked),
        ("ignored", actual_ignored),
    )
    for key, actual in checks:
        wanted = expected.get(key)
        if not isinstance(wanted, list) or not all(isinstance(item, str) for item in wanted):
            raise FixtureError(f"git_expectations.{key} must be a string array")
        if sorted(wanted) != actual:
            raise FixtureError(
                f"git_expectations.{key} mismatch: expected {sorted(wanted)}, got {actual}"
            )


def _contract_self_test_body() -> None:
    _validate_text_files()
    nested_git = [path for path in ROOT.rglob(".git")]
    if nested_git:
        raise FixtureError(f"nested .git forbidden: {nested_git[0]}")
    _validate_safeguards()
    root_settings = _read_json(REPO_ROOT / ".claude" / "settings.json")
    root_overrides = root_settings.get("skillOverrides")
    if not isinstance(root_overrides, dict):
        raise FixtureError("root .claude/settings.json lacks skillOverrides")
    names = sorted(
        path.parent.name
        for path in SCENARIOS.glob("*/scenario.json")
        if path.is_file()
    )
    if not names:
        raise FixtureError("no M2 scenarios found")
    for name in names:
        _validate_scenario(name, root_overrides)

    first_name = names[0]
    directory, scenario = _load_scenario(first_name)
    expectation_id = scenario["expectations"][0]["id"]
    expected = _expectation_tree(directory, scenario, expectation_id)
    expectation = _expectation(directory, scenario, expectation_id)
    expected_plan_path = _manifest_path(
        directory,
        expectation["plan"],
        owner=directory / "scenario.json",
    )
    expected_plan = _parse_plan(expected_plan_path, expectation=True)
    scratch = Path(
        tempfile.mkdtemp(
            prefix="bridge-sync-contract-self-test-",
            dir=_os_temp_root(),
        )
    )
    CREATED_TEMP_ROOTS.add(Path(os.path.abspath(scratch)))
    try:
        _materialize_tree(scratch, expected)
        if _compare_tree(scratch, expected):
            raise FixtureError("comparator rejected an exact tree")
        actual_plan_path = scratch / "actual-plan.md"
        expected_text = expected_plan_path.read_text(encoding="utf-8")
        actual_text = expected_text.replace(
            f"- expectation: {PLAN_SPEC}",
            f"- spec: {PLAN_SPEC}",
            1,
        )
        actual_plan_path.write_text(
            actual_text,
            encoding="utf-8",
            newline="\n",
        )
        actual_plan = _parse_plan(actual_plan_path, expectation=False)
        if _compare_plans(expected_plan, actual_plan):
            raise FixtureError("plan comparator rejected an exact normalized plan")
        actual_phase = actual_plan["headers"]["phase"]
        mismatched_phase = "pre-write" if actual_phase == "post-write" else "post-write"
        mismatched_text = actual_text.replace(
            f"- phase: {actual_phase}",
            f"- phase: {mismatched_phase}",
            1,
        )
        actual_plan_path.write_text(
            mismatched_text,
            encoding="utf-8",
            newline="\n",
        )
        mismatched_plan = _parse_plan(actual_plan_path, expectation=False)
        if not _compare_plans(expected_plan, mismatched_plan):
            raise FixtureError("plan comparator did not detect contract mismatch")
        regular = next(
            (path for path, entry in expected.items() if entry["type"] == "file"),
            None,
        )
        if regular is not None:
            target = scratch.joinpath(*PurePosixPath(regular).parts)
            target.write_bytes(target.read_bytes() + b"fixture-mismatch")
            errors = _compare_tree(scratch, expected)
            if not any(error == f"bytes: {regular}" for error in errors):
                raise FixtureError("comparator did not detect byte mismatch")
    finally:
        _strict_remove_tree(scratch)


def _self_test() -> None:
    before = set(CREATED_TEMP_ROOTS)
    try:
        _contract_self_test_body()
    except Exception as original:
        leaked = sorted(
            str(path)
            for path in CREATED_TEMP_ROOTS - before
            if os.path.lexists(path)
        )
        if leaked:
            raise FixtureError(
                f"contract self-test failed ({original}) and leaked temporary paths: "
                f"{leaked}"
            ) from original
        raise
    leaked = sorted(
        str(path)
        for path in CREATED_TEMP_ROOTS - before
        if os.path.lexists(path)
    )
    if leaked:
        raise FixtureError(f"contract self-test leaked temporary paths: {leaked}")


def _cmd_list(_: argparse.Namespace) -> int:
    for path in sorted(SCENARIOS.glob("*/scenario.json")):
        scenario = _read_json(path)
        print(f"{scenario.get('name')}\t{scenario.get('summary', '')}")
    return 0


def _cmd_self_test(_: argparse.Namespace) -> int:
    _self_test()
    scenarios = [
        _read_json(path)
        for path in sorted(SCENARIOS.glob("*/scenario.json"))
    ]
    replayable = sum(1 for scenario in scenarios if scenario.get("replay", "agent") == "agent")
    declarative = len(scenarios) - replayable
    safeguards = _read_json(SAFEGUARDS_PATH)["cases"]
    print(
        "PASS: M2 contract fixture data "
        f"({len(scenarios)} definitions; {replayable} agent-replayable; "
        f"{declarative} declarative-only; {len(safeguards)} safeguards); "
        "no bridge-sync workflow executed"
    )
    return 0


def _cmd_materialize(arguments: argparse.Namespace) -> int:
    _, scenario = _load_scenario(arguments.scenario)
    if scenario.get("replay", "agent") != "agent":
        raise FixtureError(
            f"{arguments.scenario} is declarative-only and has no real workflow barrier"
        )
    root, baseline_commit = _create_worktree(arguments.scenario)
    print(
        json.dumps(
            {
                "scenario": arguments.scenario,
                "worktree": str(root.resolve()),
                "baseline_commit": baseline_commit,
                "replay": "agent",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _cmd_compare(arguments: argparse.Namespace) -> int:
    root, marker = _fixture_root(
        Path(arguments.worktree),
        expected_scenario=arguments.scenario,
    )
    directory, scenario = _load_scenario(arguments.scenario)
    if scenario.get("replay", "agent") != "agent":
        raise FixtureError(
            f"{arguments.scenario} is declarative-only; no agent replay can satisfy it"
        )
    expectations = scenario.get("expectations")
    if not isinstance(expectations, list):
        raise FixtureError(f"{arguments.scenario}: expectations must be an array")
    _validate_coverage(arguments.scenario, scenario, expectations)
    expectation = _expectation(directory, scenario, arguments.expectation)
    actual_plan_path = Path(os.path.abspath(arguments.actual_plan))
    _require_plain_entry(actual_plan_path, directory=False)
    expected_plan = _expectation_plan(directory, scenario, expectation)
    history_commits = _validate_commit_map(
        marker["history_commits"],
        field="history_commits",
    )
    checkpoint_commits = _validate_commit_map(
        marker.get("checkpoints", {}),
        field="checkpoints",
    )
    raw_baseline_refs = expectation.get("baseline_ref", "initial")
    references = (
        {raw_baseline_refs}
        if isinstance(raw_baseline_refs, str)
        else set(raw_baseline_refs.values())
        if isinstance(raw_baseline_refs, dict)
        else set()
    )
    for reference in references:
        if isinstance(reference, str) and reference.startswith("checkpoint:"):
            checkpoint_id = reference[len("checkpoint:") :]
            if checkpoint_id not in checkpoint_commits:
                raise FixtureError(
                    f"{arguments.scenario}/{arguments.expectation}: required "
                    f"checkpoint {checkpoint_id!r} is absent from the worktree marker"
                )
    _validate_plan_baselines(
        arguments.scenario,
        expectation,
        expected_plan,
        initial=marker["baseline_commit"],
        history_commits=history_commits,
        checkpoint_commits=checkpoint_commits,
    )
    bound_commits = {
        _resolve_baseline_ref(
            arguments.scenario,
            reference,
            initial=marker["baseline_commit"],
            history_commits=history_commits,
            checkpoint_commits=checkpoint_commits,
        )
        for reference in references
        if isinstance(reference, str)
    }
    if len(bound_commits) == 1:
        expected_head = next(iter(bound_commits))
        actual_head = _run_git(root, "rev-parse", "HEAD")
        if actual_head != expected_head:
            raise FixtureError(
                f"{arguments.scenario}/{arguments.expectation}: HEAD {actual_head} "
                f"does not match bound baseline {expected_head}"
            )
    actual_plan = _parse_plan(actual_plan_path, expectation=False)
    plan_errors = _compare_plans(expected_plan, actual_plan)
    expected = _expectation_tree(
        directory,
        scenario,
        arguments.expectation,
    )
    tree_errors = _compare_tree(root, expected)
    if plan_errors or tree_errors:
        if plan_errors:
            print("PLAN MISMATCH")
            for error in plan_errors:
                print(error)
        if tree_errors:
            print("POST-STATE MISMATCH")
            for error in tree_errors:
                print(error)
        return 1
    print(
        json.dumps(
            {
                "coverage": expectation["covers"],
                "expectation": arguments.expectation,
                "plan": "matched",
                "post_state": "matched",
                "scenario": arguments.scenario,
                "status": "PASS",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _cmd_checkpoint(arguments: argparse.Namespace) -> int:
    root, marker = _fixture_root(
        Path(arguments.worktree),
        expected_scenario=arguments.scenario,
    )
    directory, scenario = _load_scenario(arguments.scenario)
    marker_path = root / ".git" / MARKER_NAME
    expected = _expectation_tree(directory, scenario, arguments.expectation)
    errors = _compare_tree(root, expected)
    if errors:
        raise FixtureError(f"cannot checkpoint mismatched post-state: {errors}")
    _run_git(root, "add", "-A")
    _apply_declared_index_modes(root, expected)
    _run_git(
        root,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        f"fixture checkpoint: {arguments.scenario}/{arguments.expectation}",
    )
    commit = _run_git(root, "rev-parse", "HEAD")
    checkpoints = marker.setdefault("checkpoints", {})
    if not isinstance(checkpoints, dict):
        raise FixtureError("invalid checkpoint marker state")
    checkpoints[arguments.expectation] = commit
    _write_json(marker_path, marker)
    print(
        json.dumps(
            {
                "scenario": arguments.scenario,
                "expectation": arguments.expectation,
                "checkpoint_commit": commit,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _cmd_cleanup(arguments: argparse.Namespace) -> int:
    root, classification = _cleanup_candidate(Path(arguments.worktree))
    _strict_remove_tree(root)
    print(
        json.dumps(
            {
                "classification": classification,
                "recoverable": False,
                "removed": str(root),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _cmd_cleanup_stale(_: argparse.Namespace) -> int:
    os_temp = _os_temp_root()
    candidates: List[Tuple[Path, str]] = []
    try:
        with os.scandir(os_temp) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
    except OSError as exc:
        raise FixtureError(f"cannot enumerate OS temporary directory {os_temp}: {exc}") from exc
    for entry in entries:
        if _scenario_temp_identity(entry.name) is None:
            continue
        root, classification = _cleanup_candidate(Path(entry.path))
        if classification == "current-marked-worktree":
            continue
        candidates.append((root, classification))
    counts: Dict[str, int] = {}
    for root, classification in candidates:
        _strict_remove_tree(root)
        counts[classification] = counts.get(classification, 0) + 1
    print(
        json.dumps(
            {
                "recoverable": False,
                "removed": counts,
                "removed_count": len(candidates),
                "scope": str(os_temp),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="list scenarios")
    list_parser.set_defaults(handler=_cmd_list)
    self_test_parser = subparsers.add_parser(
        "self-test",
        help=(
            "validate contract data, materialization, cleanup, and comparator "
            "mechanics without running bridge-sync"
        ),
    )
    self_test_parser.set_defaults(handler=_cmd_self_test)
    materialize_parser = subparsers.add_parser(
        "materialize",
        help="create an isolated disposable git worktree",
    )
    materialize_parser.add_argument("scenario")
    materialize_parser.set_defaults(handler=_cmd_materialize)
    compare_parser = subparsers.add_parser(
        "compare",
        help="compare an actual sync plan and post-tree with one replay contract",
    )
    compare_parser.add_argument("scenario")
    compare_parser.add_argument("worktree")
    compare_parser.add_argument("--expectation", required=True)
    compare_parser.add_argument("--actual-plan", required=True)
    compare_parser.set_defaults(handler=_cmd_compare)
    checkpoint_parser = subparsers.add_parser(
        "checkpoint",
        help="commit one verified result as the next synthetic test baseline",
    )
    checkpoint_parser.add_argument("scenario")
    checkpoint_parser.add_argument("worktree")
    checkpoint_parser.add_argument("--expectation", required=True)
    checkpoint_parser.set_defaults(handler=_cmd_checkpoint)
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="strictly remove one validated current or legacy fixture worktree",
    )
    cleanup_parser.add_argument("worktree")
    cleanup_parser.set_defaults(handler=_cmd_cleanup)
    cleanup_stale_parser = subparsers.add_parser(
        "cleanup-stale",
        help=(
            "strictly remove all validated legacy marked worktrees and loose-object "
            "residues while preserving current marker-v1 worktrees"
        ),
    )
    cleanup_stale_parser.add_argument(
        "--legacy-only",
        action="store_true",
        required=True,
        help="required safety acknowledgement; current marker-v1 worktrees are preserved",
    )
    cleanup_stale_parser.set_defaults(handler=_cmd_cleanup_stale)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        return int(arguments.handler(arguments))
    except FixtureError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
