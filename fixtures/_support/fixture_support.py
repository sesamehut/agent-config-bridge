#!/usr/bin/env python3
"""Safe, product-neutral mechanics for Bridge mutation fixtures.

This module knows fixture trees, disposable Git repositories, exact post-tree
comparison, and structural Markdown plan comparison. It deliberately contains
no Bridge ownership, direction, adoption, or reconciliation decisions.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


TREE_SPEC = "bridge-fixture-tree/v1"
TREE_SET_SPEC = "bridge-fixture-tree-set/v1"
MARKER_SPEC = "bridge-fixture-marker/v1"
MARKER_NAME = "bridge-fixture.json"
REGULAR_MODES = {"100644", "100755"}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
NONCE_PATTERN = re.compile(r"[A-Za-z0-9_-]{8,64}")
HASH_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


class FixtureError(RuntimeError):
    """A deterministic fixture contract or isolation violation."""


Entry = Dict[str, Any]
Tree = Dict[str, Entry]


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FixtureError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise FixtureError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def normalize_n(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    lines = [line.rstrip(b" \t") for line in normalized.split(b"\n")]
    while lines and lines[-1] == b"":
        lines.pop()
    return b"" if not lines else b"\n".join(lines) + b"\n"


def safe_token(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or TOKEN_PATTERN.fullmatch(value) is None:
        raise FixtureError(f"{field} must be a lowercase hyphenated token")
    return value


def safe_relative(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise FixtureError(f"{field} must be a non-empty string")
    if "\\" in value:
        raise FixtureError(f"{field} must use POSIX separators: {value!r}")
    path = PurePosixPath(value)
    canonical = path.as_posix()
    if path.is_absolute() or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise FixtureError(
            f"{field} is not a safe project-relative path: {value!r}"
        )
    if value != canonical:
        raise FixtureError(
            f"{field} must already be canonical POSIX syntax: {value!r}"
        )
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        "conin$",
        "conout$",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
        *(f"com{index}" for index in "¹²³"),
        *(f"lpt{index}" for index in "¹²³"),
    }
    for part in path.parts:
        stem = part.split(".", 1)[0].casefold()
        if (
            any(character in '<>:"|?*' for character in part)
            or any(ord(character) < 32 for character in part)
            or part.endswith((".", " "))
            or stem in reserved
        ):
            raise FixtureError(
                f"{field} uses a Windows-unsafe path component: {value!r}"
            )
    if path.parts[0].casefold() == ".git":
        raise FixtureError(f"{field} may not address .git: {value!r}")
    return canonical


def contained_path(base: Path, value: Any, *, field: str) -> Path:
    relative = safe_relative(value, field=field)
    candidate = (
        base / Path(*PurePosixPath(relative).parts)
    ).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as error:
        raise FixtureError(f"{field} escapes {base}: {value!r}") from error
    return candidate


def safe_regular_file(base: Path, value: Any, *, field: str) -> Path:
    """Resolve one contained regular file without traversing linked parents."""

    relative = safe_relative(value, field=field)
    resolved_base = base.resolve()
    candidate = resolved_base
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        candidate = candidate / part
        try:
            status = os.lstat(candidate)
        except OSError as error:
            raise FixtureError(
                f"{field} cannot be inspected: {value!r}: {error}"
            ) from error
        if stat.S_ISLNK(status.st_mode) or is_reparse(candidate):
            raise FixtureError(
                f"{field} may not traverse a link/reparse point: {value!r}"
            )
        if index < len(parts) - 1 and not is_directory_status(status):
            raise FixtureError(
                f"{field} has a non-directory parent: {value!r}"
            )
    try:
        candidate.resolve().relative_to(resolved_base)
    except ValueError as error:
        raise FixtureError(f"{field} escapes {base}: {value!r}") from error
    if not stat.S_ISREG(os.lstat(candidate).st_mode):
        raise FixtureError(f"{field} is not a regular file: {value!r}")
    return candidate


def manifest_path(
    scenario_dir: Path, value: Any, *, owner: Path
) -> Path:
    candidate = safe_regular_file(
        scenario_dir,
        value,
        field=f"manifest reference in {owner.name}",
    )
    return candidate


def source_path(
    scenario_dir: Path,
    value: Any,
    *,
    shared_dir: Optional[Path],
) -> Path:
    if not isinstance(value, str):
        raise FixtureError("source must be a string")
    if value.startswith("@shared/"):
        if shared_dir is None:
            raise FixtureError("@shared source used without a shared directory")
        base = shared_dir
        value = value[len("@shared/") :]
    else:
        base = scenario_dir
    return safe_regular_file(base, value, field="source")


def operation_bytes(
    scenario_dir: Path,
    operation: Mapping[str, Any],
    *,
    shared_dir: Optional[Path],
) -> bytes:
    carriers = [
        key for key in ("source", "sources", "base64") if key in operation
    ]
    if len(carriers) != 1:
        raise FixtureError(
            "write requires exactly one of source, sources, or base64"
        )
    carrier = carriers[0]
    if carrier == "source":
        return source_path(
            scenario_dir,
            operation["source"],
            shared_dir=shared_dir,
        ).read_bytes()
    if carrier == "sources":
        sources = operation["sources"]
        if not isinstance(sources, list) or not sources:
            raise FixtureError("sources must be a non-empty array")
        return b"".join(
            source_path(
                scenario_dir, item, shared_dir=shared_dir
            ).read_bytes()
            for item in sources
        )
    encoded = operation["base64"]
    if not isinstance(encoded, str):
        raise FixtureError("base64 must be a string")
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as error:
        raise FixtureError("invalid base64 fixture bytes") from error


def resolve_tree(
    scenario_dir: Path,
    manifest: Path,
    *,
    shared_dir: Optional[Path] = None,
    tree_spec: str = TREE_SPEC,
    stack: Optional[List[Path]] = None,
) -> Tree:
    """Resolve one versioned operation manifest into a complete logical tree."""

    stack = [] if stack is None else stack
    manifest = manifest.resolve()
    if manifest in stack:
        chain = " -> ".join(path.name for path in stack + [manifest])
        raise FixtureError(f"tree manifest cycle: {chain}")
    try:
        manifest.relative_to(scenario_dir.resolve())
    except ValueError as error:
        raise FixtureError(f"tree manifest escapes scenario: {manifest}") from error

    document = read_json(manifest)
    if document.get("spec") != tree_spec:
        raise FixtureError(f"{manifest}: expected spec {tree_spec}")
    tree: Tree = {}
    base = document.get("base")
    if base is not None:
        base_path = manifest_path(scenario_dir, base, owner=manifest)
        tree.update(
            resolve_tree(
                scenario_dir,
                base_path,
                shared_dir=shared_dir,
                tree_spec=tree_spec,
                stack=stack + [manifest],
            )
        )

    operations = document.get("operations")
    if not isinstance(operations, list):
        raise FixtureError(f"{manifest}: operations must be an array")
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise FixtureError(
                f"{manifest}: operation {index} must be an object"
            )
        path = safe_relative(
            operation.get("path"),
            field=f"{manifest}: operation {index} path",
        )
        kind = operation.get("op")
        if kind == "delete":
            prefix = path + "/"
            for current in list(tree):
                if current == path or current.startswith(prefix):
                    del tree[current]
            continue
        if kind == "write":
            mode = operation.get("mode")
            if mode not in REGULAR_MODES:
                raise FixtureError(
                    f"{manifest}: invalid mode for {path}: {mode!r}"
                )
            tree[path] = {
                "type": "file",
                "bytes": operation_bytes(
                    scenario_dir,
                    operation,
                    shared_dir=shared_dir,
                ),
                "mode": mode,
            }
            continue
        if kind == "symlink":
            target = operation.get("target")
            target_type = operation.get("target_type", "file")
            if (
                not isinstance(target, str)
                or not target
                or os.path.isabs(target)
            ):
                raise FixtureError(
                    f"{manifest}: symlink target must be relative and non-empty"
                )
            if target_type not in {"file", "directory"}:
                raise FixtureError(
                    f"{manifest}: invalid symlink target_type"
                )
            tree[path] = {
                "type": "symlink",
                "target": target.replace("\\", "/"),
                "target_type": target_type,
            }
            continue
        raise FixtureError(f"{manifest}: unsupported operation {kind!r}")

    for path in tree:
        prefix = path + "/"
        if any(other.startswith(prefix) for other in tree):
            raise FixtureError(
                f"{manifest}: non-directory entry has descendants: {path}"
            )
    return tree


def resolve_named_tree(
    fixture_dir: Path,
    manifest: Path,
    tree_name: str,
    *,
    shared_dir: Optional[Path] = None,
    tree_set_spec: str = TREE_SET_SPEC,
) -> Tree:
    """Resolve one tree from a versioned, reusable named-tree manifest."""

    manifest = manifest.resolve()
    try:
        manifest.relative_to(fixture_dir.resolve())
    except ValueError as error:
        raise FixtureError(f"tree-set manifest escapes fixture: {manifest}") from error
    document = read_json(manifest)
    if document.get("spec") != tree_set_spec:
        raise FixtureError(f"{manifest}: expected spec {tree_set_spec}")
    trees = document.get("trees")
    if not isinstance(trees, dict) or not trees:
        raise FixtureError(f"{manifest}: trees must be a non-empty object")
    if tree_name not in trees:
        raise FixtureError(f"{manifest}: unknown named tree {tree_name!r}")

    resolved: Dict[str, Tree] = {}
    active: List[str] = []

    def build(name: str) -> Tree:
        if name in resolved:
            return dict(resolved[name])
        if name in active:
            chain = " -> ".join(active + [name])
            raise FixtureError(f"{manifest}: named-tree cycle: {chain}")
        raw = trees.get(name)
        if not isinstance(raw, dict):
            raise FixtureError(f"{manifest}: tree {name!r} must be an object")
        extra = set(raw) - {"base", "operations"}
        if extra:
            raise FixtureError(
                f"{manifest}: tree {name!r} has unknown field {sorted(extra)[0]!r}"
            )
        tree: Tree = {}
        active.append(name)
        try:
            base = raw.get("base")
            if base is not None:
                if not isinstance(base, str) or base not in trees:
                    raise FixtureError(
                        f"{manifest}: tree {name!r} has invalid base {base!r}"
                    )
                tree.update(build(base))
            operations = raw.get("operations")
            if not isinstance(operations, list):
                raise FixtureError(
                    f"{manifest}: tree {name!r} operations must be an array"
                )
            for index, operation in enumerate(operations):
                if not isinstance(operation, dict):
                    raise FixtureError(
                        f"{manifest}: tree {name!r} operation {index} "
                        "must be an object"
                    )
                relative = safe_relative(
                    operation.get("path"),
                    field=(
                        f"{manifest}: tree {name!r} operation {index} path"
                    ),
                )
                kind = operation.get("op")
                if kind == "delete":
                    prefix = relative + "/"
                    for current in list(tree):
                        if current == relative or current.startswith(prefix):
                            del tree[current]
                    continue
                if kind == "write":
                    mode = operation.get("mode")
                    if mode not in REGULAR_MODES:
                        raise FixtureError(
                            f"{manifest}: invalid mode for {relative}: {mode!r}"
                        )
                    tree[relative] = {
                        "type": "file",
                        "bytes": operation_bytes(
                            fixture_dir,
                            operation,
                            shared_dir=shared_dir,
                        ),
                        "mode": mode,
                    }
                    continue
                if kind == "symlink":
                    target = operation.get("target")
                    target_type = operation.get("target_type", "file")
                    if (
                        not isinstance(target, str)
                        or not target
                        or os.path.isabs(target)
                    ):
                        raise FixtureError(
                            f"{manifest}: symlink target must be relative "
                            "and non-empty"
                        )
                    if target_type not in {"file", "directory"}:
                        raise FixtureError(
                            f"{manifest}: invalid symlink target_type"
                        )
                    tree[relative] = {
                        "type": "symlink",
                        "target": target.replace("\\", "/"),
                        "target_type": target_type,
                    }
                    continue
                raise FixtureError(
                    f"{manifest}: unsupported operation {kind!r}"
                )
        finally:
            active.pop()
        for relative in tree:
            prefix = relative + "/"
            if any(other.startswith(prefix) for other in tree):
                raise FixtureError(
                    f"{manifest}: non-directory entry has descendants: "
                    f"{relative}"
                )
        resolved[name] = dict(tree)
        return tree

    names = list(trees)
    if names != sorted(names):
        raise FixtureError(f"{manifest}: named trees must be byte-wise sorted")
    return build(tree_name)


def is_reparse(path: Path) -> bool:
    try:
        attributes = os.lstat(path).st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def is_directory_status(status: os.stat_result) -> bool:
    if stat.S_ISDIR(status.st_mode):
        return True
    attributes = getattr(status, "st_file_attributes", 0)
    return bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_DIRECTORY", 0)
    )


def make_writable(path: Path, status: os.stat_result) -> None:
    try:
        mode = status.st_mode | stat.S_IWUSR
        if is_directory_status(status):
            mode |= stat.S_IXUSR
        os.chmod(path, mode)
    except OSError as error:
        raise FixtureError(
            f"cannot make cleanup target writable: {path}: {error}"
        ) from error


def remove_link_no_follow(path: Path, status: os.stat_result) -> None:
    try:
        if is_directory_status(status):
            os.rmdir(path)
        else:
            path.unlink()
    except OSError as error:
        raise FixtureError(
            f"cannot remove link/reparse point: {path}: {error}"
        ) from error


def strict_remove_tree(root: Path) -> None:
    """Remove exactly one known tree without traversing links or reparses."""

    try:
        root_status = os.lstat(root)
    except FileNotFoundError:
        return
    except OSError as error:
        raise FixtureError(f"cannot inspect cleanup root {root}: {error}") from error
    if stat.S_ISLNK(root_status.st_mode) or is_reparse(root):
        raise FixtureError(
            f"cleanup root may not be a link or reparse point: {root}"
        )
    if not is_directory_status(root_status):
        raise FixtureError(f"cleanup root is not a directory: {root}")

    def remove_directory(directory: Path) -> None:
        try:
            with os.scandir(directory) as iterator:
                children = list(iterator)
        except OSError as error:
            raise FixtureError(
                f"cannot enumerate cleanup directory {directory}: {error}"
            ) from error
        for item in children:
            path = Path(item.path)
            try:
                status = item.stat(follow_symlinks=False)
            except OSError as error:
                raise FixtureError(
                    f"cannot inspect cleanup entry {path}: {error}"
                ) from error
            attributes = getattr(status, "st_file_attributes", 0)
            reparse = bool(
                attributes
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            )
            if stat.S_ISLNK(status.st_mode) or reparse:
                remove_link_no_follow(path, status)
            elif is_directory_status(status):
                remove_directory(path)
            else:
                make_writable(path, status)
                try:
                    path.unlink()
                except OSError as error:
                    raise FixtureError(
                        f"cannot remove cleanup entry {path}: {error}"
                    ) from error
        status = os.lstat(directory)
        make_writable(directory, status)
        try:
            os.rmdir(directory)
        except OSError as error:
            raise FixtureError(
                f"cannot remove cleanup directory {directory}: {error}"
            ) from error

    remove_directory(root)
    if os.path.lexists(root):
        raise FixtureError(f"cleanup target still exists after removal: {root}")


def remove_entry(path: Path) -> None:
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError as error:
        raise FixtureError(f"cannot inspect entry {path}: {error}") from error
    if stat.S_ISLNK(status.st_mode) or is_reparse(path):
        remove_link_no_follow(path, status)
    elif is_directory_status(status):
        strict_remove_tree(path)
    else:
        make_writable(path, status)
        try:
            path.unlink()
        except OSError as error:
            raise FixtureError(f"cannot remove entry {path}: {error}") from error


def walk_entries(root: Path) -> Dict[str, Path]:
    """Return all non-directory project entries, excluding the root .git."""

    result: Dict[str, Path] = {}

    def visit(directory: Path, prefix: str) -> None:
        try:
            with os.scandir(directory) as iterator:
                children = sorted(
                    iterator, key=lambda item: os.fsencode(item.name)
                )
        except OSError as error:
            raise FixtureError(f"cannot enumerate {directory}: {error}") from error
        for item in children:
            if not prefix and item.name.casefold() == ".git":
                continue
            path = Path(item.path)
            relative = f"{prefix}/{item.name}" if prefix else item.name
            relative = relative.replace("\\", "/")
            status = item.stat(follow_symlinks=False)
            attributes = getattr(status, "st_file_attributes", 0)
            reparse = bool(
                attributes
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            )
            if stat.S_ISLNK(status.st_mode) or reparse:
                result[relative] = path
            elif is_directory_status(status):
                visit(path, relative)
            elif stat.S_ISREG(status.st_mode):
                result[relative] = path
            else:
                result[relative] = path

    visit(root, "")
    return result


def safe_destination(root: Path, relative: str) -> Path:
    safe_relative(relative, field="tree path")
    destination = root.joinpath(*PurePosixPath(relative).parts)
    try:
        destination.resolve(strict=False).relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise FixtureError(
            f"tree destination escapes materialized root: {relative}"
        ) from error
    return destination


def make_link(root: Path, destination: Path, entry: Mapping[str, Any]) -> None:
    target = entry["target"]
    target_is_directory = entry["target_type"] == "directory"
    try:
        destination.symlink_to(
            target, target_is_directory=target_is_directory
        )
        return
    except OSError as first_error:
        if os.name != "nt" or not target_is_directory:
            raise FixtureError(
                f"cannot create fixture symlink {destination}: {first_error}"
            ) from first_error
    target_path = (destination.parent / target).resolve()
    try:
        target_path.relative_to(root.resolve())
    except ValueError as error:
        raise FixtureError(
            f"junction target escapes worktree: {target}"
        ) from error
    target_path.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(destination), str(target_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise FixtureError(
            "cannot create fixture junction "
            f"{destination}: {process.stderr.decode(errors='replace').strip()}"
        )


def materialize_tree(root: Path, tree: Mapping[str, Entry]) -> None:
    """Make the non-.git project tree equal to the supplied logical tree."""

    existing = walk_entries(root)
    for relative in sorted(
        set(existing) - set(tree),
        key=lambda value: (value.count("/"), value),
        reverse=True,
    ):
        remove_entry(existing[relative])

    for relative, entry in sorted(
        tree.items(),
        key=lambda item: (item[1]["type"] == "symlink", item[0]),
    ):
        destination = safe_destination(root, relative)
        if os.path.lexists(destination):
            remove_entry(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if entry["type"] == "file":
            destination.write_bytes(entry["bytes"])
            if os.name != "nt":
                os.chmod(
                    destination,
                    0o755 if entry["mode"] == "100755" else 0o644,
                )
        elif entry["type"] == "symlink":
            make_link(root, destination, entry)
        else:
            raise FixtureError(
                f"unsupported logical tree type at {relative}: {entry['type']}"
            )


def link_target_matches(
    root: Path, path: Path, expected: Mapping[str, Any]
) -> bool:
    if path.is_symlink():
        return os.readlink(path).replace("\\", "/") == expected["target"]
    if is_reparse(path) and expected["target_type"] == "directory":
        target = (path.parent / expected["target"]).resolve()
        try:
            return path.resolve() == target and target.is_relative_to(
                root.resolve()
            )
        except (OSError, ValueError):
            return False
    return False


def compare_tree(root: Path, expected: Mapping[str, Entry]) -> List[str]:
    """Compare paths, types, bytes, link targets, and observable modes."""

    errors: List[str] = []
    actual = walk_entries(root)
    actual_names = set(actual)
    expected_names = set(expected)
    for relative in sorted(expected_names - actual_names):
        errors.append(f"missing: {relative}")
    for relative in sorted(actual_names - expected_names):
        errors.append(f"extra: {relative}")
    for relative in sorted(actual_names & expected_names):
        path = actual[relative]
        entry = expected[relative]
        status = os.lstat(path)
        linked = stat.S_ISLNK(status.st_mode) or is_reparse(path)
        if entry["type"] == "symlink":
            if not linked:
                errors.append(
                    f"type: {relative} (expected symlink/reparse point)"
                )
            elif not link_target_matches(root, path, entry):
                errors.append(f"link-target: {relative}")
            continue
        if linked or not stat.S_ISREG(status.st_mode):
            errors.append(f"type: {relative} (expected regular file)")
            continue
        if path.read_bytes() != entry["bytes"]:
            errors.append(f"bytes: {relative}")
        if os.name != "nt":
            actual_mode = (
                "100755" if status.st_mode & stat.S_IXUSR else "100644"
            )
            if actual_mode != entry["mode"]:
                errors.append(
                    f"mode: {relative} "
                    f"(actual {actual_mode}, expected {entry['mode']})"
                )
    return errors


def git_run(
    root: Path, *arguments: str, allow_failure: bool = False
) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0 and not allow_failure:
        raise FixtureError(
            f"git {' '.join(arguments)} failed: "
            f"{process.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return process.stdout.decode("utf-8", errors="strict").strip()


def apply_index_modes(root: Path, tree: Mapping[str, Entry]) -> None:
    tracked_process = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if tracked_process.returncode != 0:
        raise FixtureError(
            "git ls-files failed while applying fixture modes: "
            + tracked_process.stderr.decode(errors="replace").strip()
        )
    tracked = {
        item.decode("utf-8").replace("\\", "/")
        for item in tracked_process.stdout.split(b"\0")
        if item
    }
    for relative, entry in sorted(tree.items()):
        if entry["type"] != "file" or relative not in tracked:
            continue
        flag = "+x" if entry["mode"] == "100755" else "-x"
        process = subprocess.run(
            ["git", "-C", str(root), "update-index", f"--chmod={flag}", "--", relative],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode != 0:
            raise FixtureError(
                f"cannot set fixture index mode for {relative}: "
                f"{process.stderr.decode(errors='replace').strip()}"
            )


def os_temp_root() -> Path:
    root = Path(os.path.abspath(tempfile.gettempdir()))
    status = os.lstat(root)
    if stat.S_ISLNK(status.st_mode) or is_reparse(root):
        raise FixtureError(
            f"OS temporary directory may not be linked/reparse: {root}"
        )
    if not is_directory_status(status):
        raise FixtureError(f"OS temporary path is not a directory: {root}")
    return root


def validate_temp_root(
    root: Path, *, suite: str, scenario: str
) -> Tuple[Path, str]:
    suite = safe_token(suite, field="suite")
    scenario = safe_token(scenario, field="scenario")
    absolute = Path(os.path.abspath(root))
    temp_root = os_temp_root()
    if absolute == temp_root or absolute.parent != temp_root:
        raise FixtureError(
            "fixture root must be a direct child of the OS temporary directory"
        )
    prefix = f"bridge-{suite}-{scenario}-"
    if not absolute.name.startswith(prefix):
        raise FixtureError(
            f"fixture root name must start with {prefix!r}: {absolute.name}"
        )
    nonce = absolute.name[len(prefix) :]
    if NONCE_PATTERN.fullmatch(nonce) is None:
        raise FixtureError(f"invalid fixture nonce in {absolute.name}")
    status = os.lstat(absolute)
    if stat.S_ISLNK(status.st_mode) or is_reparse(absolute):
        raise FixtureError("fixture root may not be a link/reparse point")
    if not is_directory_status(status):
        raise FixtureError("fixture root is not a directory")
    resolved = absolute.resolve()
    if resolved.parent != temp_root.resolve():
        raise FixtureError("resolved fixture root escaped OS temporary root")
    return resolved, nonce


def lease_digest(lease: str) -> str:
    return hashlib.sha256(lease.encode("ascii")).hexdigest()


def validate_marker(
    root: Path,
    *,
    suite: str,
    scenario: str,
    lease: str,
) -> Dict[str, Any]:
    root, nonce = validate_temp_root(
        root, suite=suite, scenario=scenario
    )
    git_directory = root / ".git"
    try:
        git_status = os.lstat(git_directory)
    except OSError as error:
        raise FixtureError(f"cannot inspect fixture .git directory: {error}") from error
    if (
        not is_directory_status(git_status)
        or stat.S_ISLNK(git_status.st_mode)
        or is_reparse(git_directory)
    ):
        raise FixtureError("fixture .git must be a plain directory")
    marker_path = git_directory / MARKER_NAME
    try:
        status = os.lstat(marker_path)
    except OSError as error:
        raise FixtureError(f"cannot inspect fixture marker: {error}") from error
    if (
        not stat.S_ISREG(status.st_mode)
        or is_reparse(marker_path)
        or status.st_nlink != 1
    ):
        raise FixtureError(
            "fixture marker must be a single-link plain regular file"
        )
    marker = read_json(marker_path)
    expected = {
        "spec": MARKER_SPEC,
        "suite": suite,
        "scenario": scenario,
        "nonce": nonce,
        "resolved_root": str(root),
        "lease_sha256": lease_digest(lease),
    }
    for key, value in expected.items():
        if marker.get(key) != value:
            raise FixtureError(f"fixture marker mismatch for {key}")
    baseline = marker.get("baseline_commit")
    if not isinstance(baseline, str) or HASH_PATTERN.fullmatch(baseline) is None:
        raise FixtureError("fixture marker has invalid baseline_commit")
    if git_run(root, "rev-parse", "HEAD") != baseline:
        raise FixtureError("fixture HEAD no longer equals its bound baseline")
    history_commits = marker.get("history_commits")
    if history_commits is not None:
        if (
            not isinstance(history_commits, dict)
            or not history_commits
            or any(
                not isinstance(name, str)
                or TOKEN_PATTERN.fullmatch(name) is None
                or not isinstance(commit, str)
                or HASH_PATTERN.fullmatch(commit) is None
                for name, commit in history_commits.items()
            )
        ):
            raise FixtureError("fixture marker has invalid history_commits")
        reachable = set(git_run(root, "rev-list", baseline).splitlines())
        for name, commit in history_commits.items():
            resolved_commit = git_run(
                root, "rev-parse", "--verify", f"{commit}^{{commit}}"
            )
            if resolved_commit != commit:
                raise FixtureError(
                    f"fixture history id {name!r} is not an exact commit"
                )
            if commit not in reachable:
                raise FixtureError(
                    f"fixture history id {name!r} is not reachable from HEAD"
                )
    return marker


def create_temp_git_project(
    *,
    suite: str,
    scenario: str,
    baseline: Mapping[str, Entry],
    input_tree: Mapping[str, Entry],
    history: Optional[Sequence[Mapping[str, Any]]] = None,
    history_head: Optional[str] = None,
) -> Dict[str, Any]:
    """Create one leased disposable Git project and apply its input snapshot."""

    suite = safe_token(suite, field="suite")
    scenario = safe_token(scenario, field="scenario")
    temp_root = os_temp_root()
    nonce = secrets.token_urlsafe(12).replace("-", "_")
    root = temp_root / f"bridge-{suite}-{scenario}-{nonce}"
    root.mkdir(mode=0o700)
    lease = secrets.token_urlsafe(32)
    try:
        validate_temp_root(root, suite=suite, scenario=scenario)
        git_run(root, "init", "--quiet")
        git_run(root, "config", "user.name", "Bridge Fixture")
        git_run(
            root,
            "config",
            "user.email",
            "bridge-fixture@example.invalid",
        )
        git_run(root, "config", "core.autocrlf", "false")
        history_commits: Dict[str, str] = {}
        if history is None:
            if history_head is not None:
                raise FixtureError(
                    "history_head is invalid without synthetic history"
                )
            materialize_tree(root, baseline)
            git_run(root, "add", "-A")
            apply_index_modes(root, baseline)
            git_run(
                root,
                "commit",
                "--quiet",
                "--allow-empty",
                "-m",
                "fixture baseline",
            )
            baseline_commit = git_run(root, "rev-parse", "HEAD")
        else:
            if (
                not history
                or not isinstance(history_head, str)
                or TOKEN_PATTERN.fullmatch(history_head) is None
            ):
                raise FixtureError(
                    "synthetic history needs commits and a token head"
                )
            for index, commit in enumerate(history):
                if not isinstance(commit, Mapping) or set(commit) != {
                    "id",
                    "message",
                    "parents",
                    "tree",
                }:
                    raise FixtureError(
                        "synthetic history commit fields are not closed"
                    )
                commit_id = safe_token(
                    commit["id"], field="synthetic history commit id"
                )
                if commit_id in history_commits:
                    raise FixtureError(
                        f"duplicate synthetic history id: {commit_id}"
                    )
                parents = commit["parents"]
                if (
                    not isinstance(parents, list)
                    or parents != sorted(set(parents))
                    or any(parent not in history_commits for parent in parents)
                ):
                    raise FixtureError(
                        f"{commit_id}: parents must be sorted prior ids"
                    )
                if (
                    not isinstance(commit["message"], str)
                    or not commit["message"]
                ):
                    raise FixtureError(
                        f"{commit_id}: commit message must be non-empty"
                    )
                tree = commit["tree"]
                if not isinstance(tree, Mapping):
                    raise FixtureError(
                        f"{commit_id}: resolved history tree is invalid"
                    )
                materialize_tree(root, tree)
                git_run(root, "add", "-A")
                apply_index_modes(root, tree)
                tree_id = git_run(root, "write-tree")
                arguments = ["commit-tree", tree_id]
                for parent in parents:
                    arguments.extend(["-p", history_commits[parent]])
                arguments.extend(["-m", commit["message"]])
                history_commits[commit_id] = git_run(root, *arguments)
                if index == len(history) - 1 and commit_id != history_head:
                    raise FixtureError(
                        "synthetic history head must be the final commit"
                    )
            if history_head not in history_commits:
                raise FixtureError("synthetic history head is unknown")
            baseline_commit = history_commits[history_head]
            git_run(root, "symbolic-ref", "HEAD", "refs/heads/main")
            git_run(root, "update-ref", "refs/heads/main", baseline_commit)
            if compare_tree(root, baseline):
                raise FixtureError(
                    "scenario baseline must equal synthetic history HEAD tree"
                )
        resolved = root.resolve()
        marker: Dict[str, Any] = {
            "spec": MARKER_SPEC,
            "suite": suite,
            "scenario": scenario,
            "nonce": nonce,
            "resolved_root": str(resolved),
            "lease_sha256": lease_digest(lease),
            "baseline_commit": baseline_commit,
        }
        if history_commits:
            marker["history_commits"] = history_commits
        write_json(root / ".git" / MARKER_NAME, marker)
        materialize_tree(root, input_tree)
        apply_index_modes(root, input_tree)
        result: Dict[str, Any] = {
            "worktree": str(resolved),
            "lease": lease,
            "baseline_commit": baseline_commit,
        }
        if history_commits:
            result["history_commits"] = history_commits
        return result
    except Exception as original:
        try:
            strict_remove_tree(root)
        except Exception as cleanup_error:
            raise FixtureError(
                f"fixture setup failed ({original}); exact cleanup also failed: "
                f"{cleanup_error}"
            ) from cleanup_error
        raise


def cleanup_leased_project(
    root: Path,
    *,
    suite: str,
    scenario: str,
    lease: str,
) -> None:
    """Delete one exact leased project; never enumerate the temp directory."""

    validate_marker(root, suite=suite, scenario=scenario, lease=lease)
    strict_remove_tree(root)


def normalized_markdown_lines(path: Path) -> List[str]:
    try:
        return normalize_n(path.read_bytes()).decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise FixtureError(f"cannot read Markdown {path}: {error}") from error


def markdown_header(lines: Sequence[str], key: str) -> Optional[str]:
    prefix = f"- {key}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def markdown_section(lines: Sequence[str], heading: str) -> List[str]:
    marker = f"## {heading}"
    try:
        start = list(lines).index(marker) + 1
    except ValueError as error:
        raise FixtureError(f"missing section: {marker}") from error
    result: List[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        result.append(line)
    return result


def parse_table(
    lines: Sequence[str],
    *,
    heading: str,
    expected_header: str,
    expected_separator: str,
) -> List[Tuple[str, ...]]:
    content = [line for line in markdown_section(lines, heading) if line]
    if len(content) < 2:
        raise FixtureError(f"{heading} must contain a table")
    if content[0] != expected_header or content[1] != expected_separator:
        raise FixtureError(f"{heading} header or separator is malformed")
    width = len(expected_header.split("|")[1:-1])
    rows: List[Tuple[str, ...]] = []
    for line in content[2:]:
        if not line.startswith("| ") or not line.endswith(" |"):
            raise FixtureError(f"malformed {heading} row: {line}")
        parts = line.split("|")
        if len(parts) != width + 2 or parts[0] or parts[-1]:
            raise FixtureError(f"wrong {heading} cell count: {line}")
        cells: List[str] = []
        for part in parts[1:-1]:
            if not part.startswith(" ") or not part.endswith(" "):
                raise FixtureError(
                    f"{heading} cells need exact one-space padding"
                )
            cells.append(part[1:-1])
        rows.append(tuple(cells))
    return rows


def parse_list_section(
    lines: Sequence[str], *, heading: str
) -> List[str]:
    content = [line for line in markdown_section(lines, heading) if line]
    if not content:
        raise FixtureError(f"{heading} must not be empty")
    if any(not line.startswith("- ") for line in content):
        raise FixtureError(f"{heading} contains a non-list line")
    if content == ["- (none)"]:
        return content
    if "- (none)" in content or content != sorted(content):
        raise FixtureError(
            f"{heading} must be sorted or exactly '- (none)'"
        )
    return content


def compare_plan_shape(
    expected_path: Path,
    actual_path: Path,
    *,
    scalar_keys: Sequence[str],
    table_heading: str,
    table_header: str,
    table_separator: str,
    list_heading: str,
) -> List[str]:
    """Compare a plan's registered structural fields without product decisions."""

    expected_lines = normalized_markdown_lines(expected_path)
    actual_lines = normalized_markdown_lines(actual_path)

    def normalized(lines: Sequence[str], expectation: bool) -> List[str]:
        result: List[str] = []
        for key in scalar_keys:
            source_key = (
                "expectation"
                if expectation and key == "spec"
                else key
            )
            value = markdown_header(lines, source_key)
            if value is None:
                raise FixtureError(f"missing header: {source_key}")
            result.append(f"{key}: {value}")
        rows = parse_table(
            lines,
            heading=table_heading,
            expected_header=table_header,
            expected_separator=table_separator,
        )
        result.extend(
            "| " + " | ".join(row) + " |" for row in sorted(rows)
        )
        result.extend(parse_list_section(lines, heading=list_heading))
        return result

    expected = normalized(expected_lines, True)
    actual = normalized(actual_lines, False)
    if expected == actual:
        return []
    return list(
        difflib.unified_diff(
            expected,
            actual,
            fromfile="expected-plan",
            tofile="actual-plan",
            lineterm="",
        )
    )
