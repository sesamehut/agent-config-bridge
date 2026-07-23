#!/usr/bin/env python3
"""Read-only byte and Git-tree mechanics for Bridge skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile

# The guard must precede every import that may someday need 3.9+, so a too-old
# interpreter exits with the documented JSON error instead of a traceback.
if sys.version_info < (3, 9):
    print(
        json.dumps(
            {
                "error": "Python %d.%d is too old; sentinel_mechanics.py"
                " requires Python 3.9 or newer" % sys.version_info[:2]
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(2)

from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Optional


REGULAR_GIT_MODES = {"100644", "100755"}
GIT_TREE_DIRECTIONS = {
    "observe",
    "source-to-projection",
    "projection-to-source",
}


def normalize_n(data: bytes) -> bytes:
    """Apply the specification's closed normalization set N."""
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    lines = [line.rstrip(b" \t") for line in normalized.split(b"\n")]
    while lines and lines[-1] == b"":
        lines.pop()
    if not lines:
        return b""
    return b"\n".join(lines) + b"\n"


def is_subsequence(left: list[bytes], right: list[bytes]) -> bool:
    iterator = iter(right)
    return all(any(candidate == item for candidate in iterator) for item in left)


def byte_lines(data: bytes) -> list[bytes]:
    """Split only at LF and retain line endings for raw-byte honesty."""
    lines: list[bytes] = []
    start = 0
    for index, value in enumerate(data):
        if value == 0x0A:
            lines.append(data[start : index + 1])
            start = index + 1
    if start < len(data):
        lines.append(data[start:])
    return lines


def diff_shape(source: bytes, projection: bytes) -> str:
    """Classify a changed byte pair by the report specification."""
    if source == projection:
        return "equal"
    source_lines = byte_lines(source)
    projection_lines = byte_lines(projection)
    if is_subsequence(source_lines, projection_lines):
        return "additions-only"
    if is_subsequence(projection_lines, source_lines):
        return "deletions-only"
    return "both"


def read_bytes(path: Path, normalized: bool) -> bytes:
    data = path.read_bytes()
    return normalize_n(data) if normalized else data


def compare_files(left: Path, right: Path, normalized: bool) -> dict[str, Any]:
    source = read_bytes(left, normalized)
    projection = read_bytes(right, normalized)
    shape = diff_shape(source, projection)
    return {
        "equal": shape == "equal",
        "shape": shape,
        "normalization": "N" if normalized else "none",
        "source": str(left),
        "projection": str(right),
    }


def inspect_tree(root: Path) -> dict[str, Any]:
    """Enumerate a tree without following links or reparse points."""
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    root_stat = root.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if root.is_symlink() or (
        reparse_flag
        and getattr(root_stat, "st_file_attributes", 0) & reparse_flag
    ):
        return {
            "safe": False,
            "root": str(root),
            "files": [],
            "special": [{"path": ".", "kind": "linked-root"}],
        }
    files: dict[str, Path] = {}
    special: list[dict[str, str]] = []
    folded: dict[str, str] = {}
    stack: list[tuple[Path, str]] = [(root, "")]

    while stack:
        directory, prefix = stack.pop()
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda item: os.fsencode(item.name))
        for entry in entries:
            relative = f"{prefix}/{entry.name}" if prefix else entry.name
            relative = relative.replace("\\", "/")
            folded_name = relative.casefold()
            prior = folded.get(folded_name)
            if prior is not None and prior != relative:
                special.append(
                    {
                        "path": relative,
                        "kind": "case-fold-collision",
                        "detail": prior,
                    }
                )
                continue
            folded[folded_name] = relative

            entry_stat = entry.stat(follow_symlinks=False)
            is_reparse = bool(
                reparse_flag
                and getattr(entry_stat, "st_file_attributes", 0) & reparse_flag
            )
            if entry.is_symlink():
                special.append({"path": relative, "kind": "symlink"})
            elif is_reparse:
                special.append({"path": relative, "kind": "reparse-point"})
            elif entry.is_dir(follow_symlinks=False):
                stack.append((Path(entry.path), relative))
            elif entry.is_file(follow_symlinks=False) and stat.S_ISREG(
                entry_stat.st_mode
            ):
                files[relative] = Path(entry.path)
            else:
                special.append({"path": relative, "kind": "special-file"})

    return {
        "safe": not special,
        "root": str(root),
        "files": sorted(files),
        "special": sorted(
            special,
            key=lambda item: (
                os.fsencode(item["path"]),
                os.fsencode(item["kind"]),
            ),
        ),
    }


def relative_files(root: Path) -> dict[str, Path]:
    inspection = inspect_tree(root)
    if not inspection["safe"]:
        raise ValueError(
            "unsafe tree entries: "
            + json.dumps(inspection["special"], ensure_ascii=False)
        )
    return {
        name: root.joinpath(*name.split("/"))
        for name in inspection["files"]
    }


def aggregate_shapes(shapes: Iterable[str]) -> str:
    changed = [shape for shape in shapes if shape != "equal"]
    if not changed:
        return "equal"
    if all(shape == "additions-only" for shape in changed):
        return "additions-only"
    if all(shape == "deletions-only" for shape in changed):
        return "deletions-only"
    return "both"


def compare_trees(master: Path, copy: Path) -> dict[str, Any]:
    """Compare only filesystem paths and bytes; Git modes are out of scope."""
    master_files = relative_files(master)
    copy_files = relative_files(copy)
    master_names = set(master_files)
    copy_names = set(copy_files)
    source_only = sorted(master_names - copy_names)
    projection_only = sorted(copy_names - master_names)
    changed: list[dict[str, str]] = []
    shapes: list[str] = []

    shapes.extend("deletions-only" for _ in source_only)
    shapes.extend("additions-only" for _ in projection_only)

    for name in sorted(master_names & copy_names):
        source = master_files[name].read_bytes()
        projection = copy_files[name].read_bytes()
        shape = diff_shape(source, projection)
        if shape != "equal":
            changed.append({"path": name, "shape": shape})
            shapes.append(shape)

    shape = aggregate_shapes(shapes)
    return {
        "comparison": "filesystem-paths-and-bytes/v1",
        "mode_checked": False,
        "equal": shape == "equal",
        "shape": shape,
        "source_only": source_only,
        "projection_only": projection_only,
        "changed": changed,
        "master": str(master),
        "copy": str(copy),
    }


def git_run(
    repo: Path, arguments: list[str], *, allow_failure: bool = False
) -> subprocess.CompletedProcess[bytes]:
    """Run a read-only Git command and retain byte-exact stdout."""
    process = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode and not allow_failure:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"git {' '.join(arguments)} failed"
            + (f": {detail}" if detail else "")
        )
    return process


def resolve_git_root(repo: Path) -> Path:
    invoked = repo.resolve()
    result = git_run(invoked, ["rev-parse", "--show-toplevel"])
    discovered = Path(
        result.stdout.decode("utf-8", errors="strict").strip()
    ).resolve()
    if os.path.normcase(str(invoked)) != os.path.normcase(str(discovered)):
        raise ValueError(
            f"repository argument is not the worktree root: {repo}"
        )
    return discovered


def normalize_unit_root(value: str) -> str:
    """Validate a repository-relative POSIX unit root."""
    if not value or "\\" in value or value.startswith("./"):
        raise ValueError(
            "unit root must be a non-empty canonical repo-relative POSIX path"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or value == "." or any(
        part in {"", ".", ".."} for part in path.parts
    ) or path.as_posix() != value:
        raise ValueError(
            "unit root must be a non-empty canonical repo-relative POSIX path"
        )
    return path.as_posix()


def normalize_entry_path(value: str) -> str:
    """Validate a canonical POSIX path relative to one unit root."""
    if not value or "\\" in value or value.startswith("./"):
        raise ValueError(
            "entry path must be a non-empty canonical unit-relative POSIX path"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or value == "." or any(
        part in {"", ".", ".."} for part in path.parts
    ) or path.as_posix() != value:
        raise ValueError(
            "entry path must be a non-empty canonical unit-relative POSIX path"
        )
    return path.as_posix()


def git_pathspec(unit_root: str) -> str:
    return f":(literal){unit_root}"


def decode_git_path(value: bytes) -> str:
    try:
        path = value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Git path is not valid UTF-8 and cannot enter the v1 manifest"
        ) from error
    if "\x00" in path:
        raise ValueError("Git path contains NUL")
    return path.replace("\\", "/")


def relative_unit_path(repo_path: str, unit_root: str) -> str:
    if repo_path == unit_root:
        return "."
    prefix = unit_root + "/"
    if not repo_path.startswith(prefix):
        raise ValueError(
            f"Git returned a path outside unit {unit_root}: {repo_path}"
        )
    relative = repo_path[len(prefix) :]
    if not relative:
        raise ValueError(f"empty relative path below unit {unit_root}")
    return relative


def parse_index_entries(repo: Path, unit_root: str) -> list[dict[str, str]]:
    result = git_run(
        repo,
        ["ls-files", "--stage", "-z", "--", git_pathspec(unit_root)],
    )
    entries: list[dict[str, str]] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError("malformed git ls-files --stage record") from error
        repo_path = decode_git_path(raw_path)
        relative_unit_path(repo_path, unit_root)
        entries.append(
            {
                "repo_path": repo_path,
                "mode": mode,
                "oid": oid,
                "stage": stage,
            }
        )
    return entries


def parse_tree_entries(
    repo: Path, unit_root: str, revision: str
) -> list[dict[str, str]]:
    result = git_run(
        repo,
        [
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            revision,
            "--",
            git_pathspec(unit_root),
        ],
    )
    entries: list[dict[str, str]] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, oid = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError("malformed git ls-tree record") from error
        repo_path = decode_git_path(raw_path)
        relative_unit_path(repo_path, unit_root)
        entries.append(
            {
                "repo_path": repo_path,
                "mode": mode,
                "oid": oid,
                "object_type": object_type,
            }
        )
    return entries


def untracked_paths(repo: Path, unit_root: str) -> list[str]:
    result = git_run(
        repo,
        [
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            git_pathspec(unit_root),
        ],
    )
    paths = [
        decode_git_path(record)
        for record in result.stdout.split(b"\0")
        if record
    ]
    for path in paths:
        relative_unit_path(path, unit_root)
    return paths


def core_filemode(repo: Path) -> bool:
    result = git_run(
        repo, ["config", "--bool", "--get", "core.filemode"], allow_failure=True
    )
    if result.returncode == 1:
        return os.name != "nt"
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            "cannot read core.filemode" + (f": {detail}" if detail else "")
        )
    value = result.stdout.decode("ascii", errors="strict").strip()
    if value not in {"true", "false"}:
        raise ValueError(f"unexpected core.filemode value: {value}")
    return value == "true"


def is_reparse(path_stat: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(
        reparse_flag
        and getattr(path_stat, "st_file_attributes", 0) & reparse_flag
    )


def classify_path(repo: Path, repo_path: str) -> tuple[str, Optional[os.stat_result]]:
    """Classify a worktree path while rejecting linked parent traversal."""
    candidate = repo
    parts = PurePosixPath(repo_path).parts
    for index, part in enumerate(parts):
        candidate = candidate / part
        try:
            candidate_stat = candidate.lstat()
        except FileNotFoundError:
            return "missing", None
        if candidate.is_symlink():
            return (
                "symlink" if index == len(parts) - 1 else "linked-parent",
                candidate_stat,
            )
        if is_reparse(candidate_stat):
            return (
                "reparse-point"
                if index == len(parts) - 1
                else "linked-parent",
                candidate_stat,
            )
        if index < len(parts) - 1 and not stat.S_ISDIR(candidate_stat.st_mode):
            return "non-directory-parent", candidate_stat

    resolved = candidate.resolve()
    try:
        common = os.path.commonpath([str(repo), str(resolved)])
    except ValueError:
        return "path-escape", candidate_stat
    if os.path.normcase(common) != os.path.normcase(str(repo)):
        return "path-escape", candidate_stat
    if stat.S_ISREG(candidate_stat.st_mode):
        return "regular", candidate_stat
    if stat.S_ISDIR(candidate_stat.st_mode):
        return "directory", candidate_stat
    return "special-file", candidate_stat


def sha256_evidence(data: bytes, source: str, **extra: Any) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "source": source,
    }
    evidence.update(extra)
    return evidence


def filesystem_git_mode(path_stat: os.stat_result) -> str:
    return "100755" if path_stat.st_mode & 0o111 else "100644"


def append_blocker(
    blockers: list[dict[str, str]], token: str, path: str, detail: str
) -> None:
    blocker = {"token": token, "path": path, "detail": detail}
    if blocker not in blockers:
        blockers.append(blocker)


def mode_for_current_file(
    *,
    path_stat: os.stat_result,
    tracked: bool,
    index_mode: Optional[str],
    head_mode: Optional[str],
    probe_reliable: bool,
    blockers: list[dict[str, str]],
    relative: str,
    require_executable: bool,
) -> tuple[str, dict[str, Any]]:
    """Resolve effective Git mode and expose each evidence layer."""
    filesystem_mode = (
        filesystem_git_mode(path_stat) if probe_reliable else None
    )
    if tracked:
        if index_mode not in REGULAR_GIT_MODES:
            raise ValueError(f"unsupported regular index mode: {index_mode}")
        effective = filesystem_mode if filesystem_mode is not None else index_mode
        if (
            require_executable
            and effective != "100755"
            and not probe_reliable
        ):
            append_blocker(
                blockers,
                "mode-limited",
                relative,
                "explicit executable intent cannot be realized because "
                "worktree mode changes are unavailable",
            )
        return effective, {
            "head": head_mode or "absent",
            "index": index_mode,
            "worktree": filesystem_mode or "unavailable",
            "effective_source": (
                "posix-filesystem-exec"
                if filesystem_mode is not None
                else "git-index"
            ),
            "staged_change": head_mode is not None and head_mode != index_mode,
            "unstaged_change": (
                filesystem_mode != index_mode
                if filesystem_mode is not None
                else "unobservable"
            ),
            "prospective": False,
            "explicit_executable_required": require_executable,
        }

    if filesystem_mode is None:
        if require_executable:
            append_blocker(
                blockers,
                "mode-limited",
                relative,
                "explicit executable intent requires 100755, but this host "
                "can establish only the prospective untracked default 100644",
            )
        return "100644", {
            "head": "absent",
            "index": "absent",
            "worktree": "unavailable",
            "effective_source": "platform-untracked-default",
            "staged_change": False,
            "unstaged_change": "unobservable",
            "prospective": True,
            "explicit_executable_required": require_executable,
        }
    return filesystem_mode, {
        "head": "absent",
        "index": "absent",
        "worktree": filesystem_mode,
        "effective_source": "posix-filesystem-exec",
        "staged_change": False,
        "unstaged_change": False,
        "prospective": True,
        "explicit_executable_required": require_executable,
    }


def detect_casefold_collisions(
    paths: Iterable[str], blockers: list[dict[str, str]]
) -> None:
    folded: dict[str, str] = {}
    for path in sorted(paths, key=lambda item: item.encode("utf-8")):
        prior = folded.get(path.casefold())
        if prior is not None and prior != path:
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                path,
                f"case-fold-collision with {prior}",
            )
        else:
            folded[path.casefold()] = path


def detect_unit_casefold_collisions(
    current_paths: Iterable[str],
    tracked_deletions: Iterable[str],
    blockers: list[dict[str, str]],
) -> None:
    """Apply the unit-wide gate to current and deleted tracked path names."""
    domain = set(current_paths)
    domain.update(tracked_deletions)
    detect_casefold_collisions(domain, blockers)


def manifest_from_revision(
    repo: Path, unit_root: str, revision: str
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    entries: list[dict[str, Any]] = []
    tree_entries = parse_tree_entries(repo, unit_root, revision)

    for item in tree_entries:
        relative = relative_unit_path(item["repo_path"], unit_root)
        mode = item["mode"]
        object_type = item["object_type"]
        if mode not in REGULAR_GIT_MODES or object_type != "blob":
            kind = (
                "git-symlink"
                if mode == "120000"
                else "gitlink"
                if mode == "160000"
                else f"git-{object_type}-{mode}"
            )
            append_blocker(
                blockers, "unsafe-tree-entry", relative, kind
            )
            entries.append(
                {
                    "path": relative,
                    "repo_path": item["repo_path"],
                    "type": kind,
                    "bytes": None,
                    "mode": mode,
                    "mode_evidence": {
                        "tree": revision,
                        "tree_mode": mode,
                        "effective_source": "git-tree",
                    },
                    "tracked": True,
                }
            )
            continue

        blob = git_run(repo, ["cat-file", "blob", item["oid"]]).stdout
        entries.append(
            {
                "path": relative,
                "repo_path": item["repo_path"],
                "type": "regular",
                "bytes": sha256_evidence(
                    blob,
                    "git-blob",
                    blob_oid=item["oid"],
                    revision=revision,
                ),
                "mode": mode,
                "mode_evidence": {
                    "tree": revision,
                    "tree_mode": mode,
                    "effective_source": "git-tree",
                },
                "tracked": True,
            }
        )

    detect_unit_casefold_collisions(
        (entry["path"] for entry in entries), (), blockers
    )
    entries.sort(key=lambda item: item["path"].encode("utf-8"))
    blockers.sort(
        key=lambda item: (
            item["path"].encode("utf-8"),
            item["token"].encode("utf-8"),
            item["detail"].encode("utf-8"),
        )
    )
    return {
        "contract": "git-tree-manifest/v1",
        "repository": str(repo),
        "unit": unit_root,
        "snapshot": "revision",
        "revision": revision,
        "include_untracked": False,
        "core_filemode": None,
        "worktree_mode_probe": "not-applicable",
        "worktree_mode_write": "not-applicable",
        "required_executable": [],
        "safe": not blockers,
        "mode_limited": any(
            blocker["token"] == "mode-limited" for blocker in blockers
        ),
        "entries": entries,
        "tracked_deletions": [],
        "blockers": blockers,
    }


def manifest_from_worktree(
    repo: Path,
    unit_root: str,
    include_untracked: bool,
    required_executable: set[str],
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    entries: list[dict[str, Any]] = []
    tracked_deletions: list[str] = []
    filemode = core_filemode(repo)
    probe_reliable = os.name != "nt" and filemode

    root_kind, _ = classify_path(repo, unit_root)
    if root_kind not in {"missing", "directory"}:
        append_blocker(
            blockers, "unsafe-tree-entry", ".", f"unit-root-{root_kind}"
        )

    index_entries = parse_index_entries(repo, unit_root)
    head_result = git_run(
        repo, ["rev-parse", "--verify", "HEAD^{tree}"], allow_failure=True
    )
    head_entries = (
        parse_tree_entries(repo, unit_root, "HEAD")
        if head_result.returncode == 0
        else []
    )
    head_modes = {
        item["repo_path"]: item["mode"] for item in head_entries
    }

    seen_index: set[str] = set()
    for item in index_entries:
        relative = relative_unit_path(item["repo_path"], unit_root)
        if item["stage"] != "0":
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                relative,
                f"unmerged-index-stage-{item['stage']}",
            )
            continue
        if item["repo_path"] in seen_index:
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                relative,
                "duplicate-index-entry",
            )
            continue
        seen_index.add(item["repo_path"])

        if item["mode"] not in REGULAR_GIT_MODES:
            kind = (
                "git-symlink"
                if item["mode"] == "120000"
                else "gitlink"
                if item["mode"] == "160000"
                else f"git-mode-{item['mode']}"
            )
            append_blocker(
                blockers, "unsafe-tree-entry", relative, kind
            )
            entries.append(
                {
                    "path": relative,
                    "repo_path": item["repo_path"],
                    "type": kind,
                    "bytes": None,
                    "mode": item["mode"],
                    "mode_evidence": {
                        "head": head_modes.get(item["repo_path"], "absent"),
                        "index": item["mode"],
                        "worktree": "not-read",
                        "effective_source": "git-index",
                    },
                    "tracked": True,
                }
            )
            continue

        path_kind, path_stat = classify_path(repo, item["repo_path"])
        if path_kind == "missing":
            tracked_deletions.append(relative)
            continue
        if path_kind != "regular" or path_stat is None:
            append_blocker(
                blockers,
                "unsafe-tree-entry",
                relative,
                f"worktree-{path_kind}",
            )
            continue

        worktree_path = repo.joinpath(*PurePosixPath(item["repo_path"]).parts)
        data = worktree_path.read_bytes()
        mode, mode_evidence = mode_for_current_file(
            path_stat=path_stat,
            tracked=True,
            index_mode=item["mode"],
            head_mode=head_modes.get(item["repo_path"]),
            probe_reliable=probe_reliable,
            blockers=blockers,
            relative=relative,
            require_executable=relative in required_executable,
        )
        entries.append(
            {
                "path": relative,
                "repo_path": item["repo_path"],
                "type": "regular",
                "bytes": sha256_evidence(
                    data,
                    "worktree",
                    index_oid=item["oid"],
                ),
                "mode": mode,
                "mode_evidence": mode_evidence,
                "tracked": True,
            }
        )

    for repo_path in head_modes:
        if repo_path not in seen_index:
            tracked_deletions.append(relative_unit_path(repo_path, unit_root))

    if include_untracked:
        for repo_path in untracked_paths(repo, unit_root):
            relative = relative_unit_path(repo_path, unit_root)
            path_kind, path_stat = classify_path(repo, repo_path)
            if path_kind != "regular" or path_stat is None:
                append_blocker(
                    blockers,
                    "unsafe-tree-entry",
                    relative,
                    f"untracked-{path_kind}",
                )
                continue
            worktree_path = repo.joinpath(*PurePosixPath(repo_path).parts)
            data = worktree_path.read_bytes()
            mode, mode_evidence = mode_for_current_file(
                path_stat=path_stat,
                tracked=False,
                index_mode=None,
                head_mode=None,
                probe_reliable=probe_reliable,
                blockers=blockers,
                relative=relative,
                require_executable=relative in required_executable,
            )
            entries.append(
                {
                    "path": relative,
                    "repo_path": repo_path,
                    "type": "regular",
                    "bytes": sha256_evidence(data, "untracked-worktree"),
                    "mode": mode,
                    "mode_evidence": mode_evidence,
                    "tracked": False,
                }
            )

    present_paths = {entry["path"] for entry in entries}
    if not probe_reliable:
        for relative in required_executable - present_paths:
            append_blocker(
                blockers,
                "mode-limited",
                relative,
                "explicit executable intent requires creating 100755, but "
                "this host can establish only the prospective default 100644",
            )

    detect_unit_casefold_collisions(
        (entry["path"] for entry in entries), tracked_deletions, blockers
    )
    entries.sort(key=lambda item: item["path"].encode("utf-8"))
    tracked_deletions.sort(key=lambda item: item.encode("utf-8"))
    blockers.sort(
        key=lambda item: (
            item["path"].encode("utf-8"),
            item["token"].encode("utf-8"),
            item["detail"].encode("utf-8"),
        )
    )
    return {
        "contract": "git-tree-manifest/v1",
        "repository": str(repo),
        "unit": unit_root,
        "snapshot": "worktree",
        "revision": None,
        "include_untracked": include_untracked,
        "core_filemode": filemode,
        "worktree_mode_probe": (
            "posix-executable-bits"
            if probe_reliable
            else "index-for-tracked; prospective-100644-for-untracked"
        ),
        "worktree_mode_write": (
            "posix-executable-bits" if probe_reliable else "unavailable"
        ),
        "required_executable": sorted(
            required_executable, key=lambda item: item.encode("utf-8")
        ),
        "safe": not blockers,
        "mode_limited": any(
            blocker["token"] == "mode-limited" for blocker in blockers
        ),
        "entries": entries,
        "tracked_deletions": tracked_deletions,
        "blockers": blockers,
    }


def git_manifest(
    repo: Path,
    unit_root_value: str,
    *,
    revision: Optional[str],
    include_untracked: bool,
    required_executable: Iterable[str] = (),
) -> dict[str, Any]:
    root = resolve_git_root(repo)
    unit_root = normalize_unit_root(unit_root_value)
    executable_paths = {
        normalize_entry_path(path) for path in required_executable
    }
    if revision is not None and include_untracked:
        raise ValueError("--include-untracked is valid only for a worktree manifest")
    if revision is not None and executable_paths:
        raise ValueError(
            "--require-executable is valid only for a worktree manifest"
        )
    if revision is not None and (
        revision.startswith("-") or "\x00" in revision
    ):
        raise ValueError("revision must not begin with '-' or contain NUL")
    if revision is not None:
        return manifest_from_revision(root, unit_root, revision)
    return manifest_from_worktree(
        root, unit_root, include_untracked, executable_paths
    )


def target_can_realize_mode(
    target_manifest: dict[str, Any],
    target_entry: Optional[dict[str, Any]],
    required_mode: str,
) -> bool:
    if target_entry is not None and target_entry.get("mode") == required_mode:
        return True
    if target_manifest.get("worktree_mode_write") == "posix-executable-bits":
        return True
    if target_entry is None:
        return required_mode == "100644"
    if (
        not target_entry.get("tracked", True)
        and target_entry.get("mode_evidence", {}).get("effective_source")
        == "platform-untracked-default"
    ):
        return required_mode == "100644"
    return False


def compare_git_manifests(
    source: dict[str, Any],
    projection: dict[str, Any],
    *,
    direction: str = "observe",
) -> dict[str, Any]:
    if direction not in GIT_TREE_DIRECTIONS:
        raise ValueError(f"unsupported Git-tree comparison direction: {direction}")
    if direction != "observe" and (
        source["snapshot"] != "worktree"
        or projection["snapshot"] != "worktree"
    ):
        raise ValueError(
            "a write direction is valid only between worktree manifests"
        )
    source_entries = {entry["path"]: entry for entry in source["entries"]}
    projection_entries = {
        entry["path"]: entry for entry in projection["entries"]
    }
    source_names = set(source_entries)
    projection_names = set(projection_entries)
    source_only = sorted(
        source_names - projection_names, key=lambda item: item.encode("utf-8")
    )
    projection_only = sorted(
        projection_names - source_names,
        key=lambda item: item.encode("utf-8"),
    )
    changed: list[dict[str, Any]] = []

    for path in sorted(
        source_names & projection_names, key=lambda item: item.encode("utf-8")
    ):
        left = source_entries[path]
        right = projection_entries[path]
        type_changed = left["type"] != right["type"]
        left_bytes = (
            left["bytes"]["sha256"] if left["bytes"] is not None else None
        )
        right_bytes = (
            right["bytes"]["sha256"] if right["bytes"] is not None else None
        )
        bytes_changed = left_bytes != right_bytes
        mode_changed = left["mode"] != right["mode"]
        if not (type_changed or bytes_changed or mode_changed):
            continue
        if type_changed:
            kind = "type"
        elif bytes_changed and mode_changed:
            kind = "bytes-and-mode"
        elif bytes_changed:
            kind = "bytes-only"
        else:
            kind = "mode-only"
        changed.append(
            {
                "path": path,
                "kind": kind,
                "source": {
                    "type": left["type"],
                    "bytes_sha256": left_bytes,
                    "mode": left["mode"],
                },
                "projection": {
                    "type": right["type"],
                    "bytes_sha256": right_bytes,
                    "mode": right["mode"],
                },
            }
        )

    blockers = [
        {"side": "source", **item} for item in source["blockers"]
    ] + [
        {"side": "projection", **item}
        for item in projection["blockers"]
    ]
    if direction != "observe":
        if direction == "source-to-projection":
            authority_entries = source_entries
            authority_manifest = source
            target_entries = projection_entries
            target_manifest = projection
            target_side = "projection"
        else:
            authority_entries = projection_entries
            authority_manifest = projection
            target_entries = source_entries
            target_manifest = source
            target_side = "source"

        executable_requirements = set(
            authority_manifest.get("required_executable", [])
        )
        for path in sorted(
            authority_entries, key=lambda item: item.encode("utf-8")
        ):
            authority_entry = authority_entries[path]
            required_mode = (
                "100755"
                if path in executable_requirements
                else authority_entry.get("mode")
            )
            if (
                authority_entry.get("type") != "regular"
                or required_mode not in REGULAR_GIT_MODES
            ):
                continue
            target_entry = target_entries.get(path)
            if target_entry is not None and target_entry.get("type") != "regular":
                continue
            if target_can_realize_mode(
                target_manifest, target_entry, required_mode
            ):
                continue
            blocker = {
                "side": target_side,
                "token": "mode-limited",
                "path": path,
                "detail": (
                    f"{direction} requires target mode {required_mode}, but "
                    "this host cannot realize that mode without changing "
                    "the Git index"
                ),
            }
            if blocker not in blockers:
                blockers.append(blocker)
    blockers.sort(
        key=lambda item: (
            item["side"].encode("utf-8"),
            item["path"].encode("utf-8"),
            item["token"].encode("utf-8"),
            item["detail"].encode("utf-8"),
        )
    )
    comparable = source["safe"] and projection["safe"] and not blockers
    equal = (
        comparable
        and not source_only
        and not projection_only
        and not changed
    )
    return {
        "contract": "git-tree-comparison/v1",
        "direction": direction,
        "identity_fields": ["path", "type", "bytes.sha256", "mode"],
        "comparable": comparable,
        "mode_limited": any(
            blocker["token"] == "mode-limited" for blocker in blockers
        ),
        "equal": equal,
        "source_only": source_only,
        "projection_only": projection_only,
        "changed": changed,
        "blockers": blockers,
        "source_manifest": source,
        "projection_manifest": projection,
    }


def compare_git_trees(
    repo: Path,
    source_unit: str,
    projection_unit: str,
    *,
    revision: Optional[str],
    include_untracked: bool,
    direction: str = "observe",
    required_executable: Iterable[str] = (),
) -> dict[str, Any]:
    source = git_manifest(
        repo,
        source_unit,
        revision=revision,
        include_untracked=include_untracked,
        required_executable=required_executable,
    )
    projection = git_manifest(
        repo,
        projection_unit,
        revision=revision,
        include_untracked=include_untracked,
        required_executable=required_executable,
    )
    return compare_git_manifests(
        source, projection, direction=direction
    )


def normalized_text(path: Path) -> list[str]:
    return normalize_n(path.read_bytes()).decode("utf-8").splitlines()


def header_value(lines: list[str], key: str) -> Optional[str]:
    prefix = f"- {key}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def section_lines(lines: list[str], heading: str) -> list[str]:
    marker = f"## {heading}"
    try:
        start = lines.index(marker) + 1
    except ValueError as error:
        raise ValueError(f"missing section: {marker}") from error
    result: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        result.append(line)
    return result


def parse_findings(lines: list[str]) -> tuple[str, list[tuple[str, ...]]]:
    content = [line for line in section_lines(lines, "Findings") if line]
    if len(content) < 2:
        raise ValueError("Findings must contain a header and separator")
    header = content[0]
    expected_separator = "|---|---|---|---|---|---|---|"
    if content[1] != expected_separator:
        raise ValueError("Findings separator is malformed")
    header_width = len(header.split("|")[1:-1])

    rows: list[tuple[str, ...]] = []
    for line in content[2:]:
        if not line.startswith("|") or not line.endswith("|"):
            raise ValueError(f"malformed Findings row: {line}")
        cells = line.split("|")[1:-1]
        if len(cells) != header_width:
            raise ValueError(f"wrong Findings cell count: {line}")
        parsed: list[str] = []
        for cell in cells:
            if cell.startswith(" "):
                cell = cell[1:]
            if cell.endswith(" "):
                cell = cell[:-1]
            parsed.append(cell)
        rows.append(tuple(parsed))
    return header, sorted(rows)


def parse_observations(lines: list[str]) -> list[str]:
    content = [
        line
        for line in section_lines(lines, "Observations")
        if line.startswith("- ")
    ]
    if not content:
        raise ValueError("Observations must contain at least '- (none)'")
    if content == ["- (none)"]:
        return []
    if "- (none)" in content:
        raise ValueError("Observations cannot mix '- (none)' with tokens")
    return sorted(content)


def compare_expectations(produced: Path, expected: Path) -> dict[str, Any]:
    actual_lines = normalized_text(produced)
    expected_lines = normalized_text(expected)
    differences: list[dict[str, Any]] = []

    scalar_pairs = (
        ("version", header_value(actual_lines, "spec"), header_value(expected_lines, "expectation")),
        (
            "scope excludes",
            header_value(actual_lines, "scope excludes"),
            header_value(expected_lines, "scope excludes"),
        ),
        (
            "onboarding",
            header_value(actual_lines, "onboarding"),
            header_value(expected_lines, "onboarding"),
        ),
    )
    for field, actual, wanted in scalar_pairs:
        if actual != wanted:
            differences.append({"field": field, "actual": actual, "expected": wanted})

    actual_header, actual_rows = parse_findings(actual_lines)
    expected_header, expected_rows = parse_findings(expected_lines)
    if actual_header != expected_header:
        differences.append(
            {
                "field": "findings header",
                "actual": actual_header,
                "expected": expected_header,
            }
        )
    if actual_rows != expected_rows:
        differences.append(
            {
                "field": "findings rows",
                "actual": actual_rows,
                "expected": expected_rows,
            }
        )

    actual_observations = parse_observations(actual_lines)
    expected_observations = parse_observations(expected_lines)
    actual_observations = [
        line
        for line in actual_observations
        if not line.startswith("- mode-limited:")
    ]
    expected_observations = [
        line
        for line in expected_observations
        if not line.startswith("- mode-limited:")
    ]
    if actual_observations != expected_observations:
        differences.append(
            {
                "field": "observations",
                "actual": actual_observations,
                "expected": expected_observations,
            }
        )

    return {
        "pass": not differences,
        "produced": str(produced),
        "expected": str(expected),
        "differences": differences,
    }


def run_self_test() -> dict[str, Any]:
    checks: list[str] = []
    assert normalize_n(b"a  \r\nb\t\r\n\r\n") == b"a\nb\n"
    checks.append("normalize-n")
    assert diff_shape(b"a\n", b"a\nb\n") == "additions-only"
    assert diff_shape(b"a\nb\n", b"a\n") == "deletions-only"
    assert diff_shape(b"a\n", b"b\n") == "both"
    checks.append("diff-shape")

    with tempfile.TemporaryDirectory(prefix="bridge-sentinel-") as temp:
        root = Path(temp)
        master = root / "master"
        copy = root / "copy"
        master.mkdir()
        copy.mkdir()
        (master / "same").write_bytes(b"same\n")
        (copy / "same").write_bytes(b"same\n")
        byte_comparison = compare_trees(master, copy)
        assert byte_comparison["equal"]
        assert byte_comparison["mode_checked"] is False
        (copy / "extra").write_bytes(b"extra\n")
        assert compare_trees(master, copy)["shape"] == "additions-only"
        produced = root / "produced.md"
        expected = root / "expected.md"
        table = (
            "## Findings\n\n"
            "| surface | unit | host | state | suggested action | tier | annotations |\n"
            "|---|---|---|---|---|---|---|\n"
            "| skills | demo | codex | in-sync | - | native | - |\n\n"
            "## Observations\n\n- (none)\n"
        )
        produced.write_text(
            "- spec: report/v3\n"
            "- scope excludes: (none)\n"
            "- onboarding: onboarded\n\n"
            + table.replace(
                "- (none)",
                "- mode-limited: .claude/skills/demo/tool "
                "(worktree-mode-unobservable)",
            ),
            encoding="utf-8",
        )
        expected.write_text(
            "- expectation: report/v3\n"
            "- scope excludes: (none)\n"
            "- onboarding: onboarded\n\n"
            + table,
            encoding="utf-8",
        )
        assert compare_expectations(produced, expected)["pass"]
        assert inspect_tree(master)["safe"]

        repository = root / "git-tree"
        repository.mkdir()
        git_run(repository, ["init", "--quiet"])
        git_run(repository, ["config", "core.filemode", "false"])
        git_run(repository, ["config", "user.name", "Bridge Self Test"])
        git_run(
            repository,
            ["config", "user.email", "bridge-self-test@example.invalid"],
        )
        source_unit = repository / "source"
        projection_unit = repository / "projection"
        deletion_unit = repository / "normal-deletion"
        source_unit.mkdir()
        projection_unit.mkdir()
        deletion_unit.mkdir()
        (source_unit / "tool").write_bytes(b"same\n")
        (projection_unit / "tool").write_bytes(b"same\n")
        (deletion_unit / "file").write_bytes(b"tracked\n")
        git_run(
            repository,
            [
                "add",
                "--",
                "source/tool",
                "projection/tool",
                "normal-deletion/file",
            ],
        )
        git_run(
            repository, ["update-index", "--chmod=+x", "--", "source/tool"]
        )
        git_run(
            repository,
            ["update-index", "--chmod=-x", "--", "projection/tool"],
        )
        mode_comparison = compare_git_trees(
            repository,
            "source",
            "projection",
            revision=None,
            include_untracked=False,
        )
        assert not mode_comparison["equal"]
        assert mode_comparison["comparable"]
        assert not mode_comparison["blockers"]
        assert mode_comparison["changed"][0]["kind"] == "mode-only"

        untracked_unit = repository / "untracked"
        untracked_unit.mkdir()
        (untracked_unit / "tool").write_bytes(b"untracked\n")
        ordinary_manifest = git_manifest(
            repository,
            "untracked",
            revision=None,
            include_untracked=True,
        )
        assert ordinary_manifest["safe"]
        assert not ordinary_manifest["mode_limited"]
        assert ordinary_manifest["entries"][0]["mode"] == "100644"
        assert (
            ordinary_manifest["entries"][0]["mode_evidence"][
                "effective_source"
            ]
            == "platform-untracked-default"
        )

        explicit_manifest = git_manifest(
            repository,
            "untracked",
            revision=None,
            include_untracked=True,
            required_executable=["tool"],
        )
        assert explicit_manifest["mode_limited"]
        assert any(
            blocker["token"] == "mode-limited"
            for blocker in explicit_manifest["blockers"]
        )

        prospective_unit = repository / "prospective"
        prospective_unit.mkdir()
        (prospective_unit / "tool").write_bytes(b"same\n")
        observe_comparison = compare_git_trees(
            repository,
            "source",
            "prospective",
            revision=None,
            include_untracked=True,
        )
        assert observe_comparison["comparable"]
        assert not observe_comparison["blockers"]
        directed_comparison = compare_git_trees(
            repository,
            "source",
            "prospective",
            revision=None,
            include_untracked=True,
            direction="source-to-projection",
        )
        assert not directed_comparison["comparable"]
        assert directed_comparison["mode_limited"]
        assert any(
            blocker["token"] == "mode-limited"
            and blocker["side"] == "projection"
            for blocker in directed_comparison["blockers"]
        )

        git_run(repository, ["commit", "--quiet", "-m", "baseline"])
        revision_manifest = git_manifest(
            repository,
            "projection",
            revision="HEAD",
            include_untracked=False,
        )
        (projection_unit / "tool").write_bytes(b"worktree\n")
        worktree_manifest = git_manifest(
            repository,
            "projection",
            revision=None,
            include_untracked=False,
        )
        snapshot_comparison = compare_git_manifests(
            revision_manifest, worktree_manifest
        )
        assert not snapshot_comparison["equal"]
        assert snapshot_comparison["changed"][0]["kind"] == "bytes-only"

        (deletion_unit / "file").unlink()
        deletion_manifest = git_manifest(
            repository,
            "normal-deletion",
            revision=None,
            include_untracked=True,
        )
        assert deletion_manifest["safe"]
        assert deletion_manifest["tracked_deletions"] == ["file"]

        collision_blockers: list[dict[str, str]] = []
        detect_unit_casefold_collisions(
            ["foo", "foo"], ["Foo", "Foo"], collision_blockers
        )
        collision_safe = not collision_blockers
        assert not collision_safe
        assert len(collision_blockers) == 1
        assert collision_blockers[0]["token"] == "unsafe-tree-entry"
        assert collision_blockers[0]["detail"].startswith(
            "case-fold-collision"
        )
        no_false_positive: list[dict[str, str]] = []
        detect_unit_casefold_collisions(
            ["same"], ["same"], no_false_positive
        )
        assert not no_false_positive

        if os.name != "nt":
            git_run(repository, ["config", "core.filemode", "true"])
            posix_unit = repository / "posix-untracked"
            posix_unit.mkdir()
            (posix_unit / "tool").write_bytes(b"executable\n")
            os.chmod(posix_unit / "tool", 0o755)
            posix_manifest = git_manifest(
                repository,
                "posix-untracked",
                revision=None,
                include_untracked=True,
            )
            assert posix_manifest["safe"]
            assert posix_manifest["entries"][0]["mode"] == "100755"
            assert (
                posix_manifest["entries"][0]["mode_evidence"][
                    "effective_source"
                ]
                == "posix-filesystem-exec"
            )
            checks.append("posix-untracked-exec")
        else:
            checks.append("posix-untracked-exec-skipped")
    checks.append("compare-trees")
    checks.append("inspect-tree")
    checks.append("git-tree-mode-only")
    checks.append("ordinary-untracked-100644")
    checks.append("explicit-exec-mode-limited")
    checks.append("directional-mode-limited")
    checks.append("observe-mode-nonblocking")
    checks.append("revision-vs-worktree")
    checks.append("tracked-deletion-preserved")
    checks.append("deleted-current-casefold-collision")
    checks.append("compare-expectation")
    return {"pass": True, "checks": checks}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only byte and Git-tree mechanics for Bridge skills."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    files = subparsers.add_parser("compare-files")
    files.add_argument("source", type=Path)
    files.add_argument("projection", type=Path)
    files.add_argument("--normalize-n", action="store_true")

    trees = subparsers.add_parser("compare-trees")
    trees.add_argument("master", type=Path)
    trees.add_argument("copy", type=Path)

    manifest = subparsers.add_parser("git-manifest")
    manifest.add_argument("repository", type=Path)
    manifest.add_argument("unit")
    manifest.add_argument("--revision")
    manifest.add_argument("--include-untracked", action="store_true")
    manifest.add_argument("--require-executable", action="append", default=[])

    git_trees = subparsers.add_parser("compare-git-trees")
    git_trees.add_argument("repository", type=Path)
    git_trees.add_argument("source_unit")
    git_trees.add_argument("projection_unit")
    git_trees.add_argument("--revision")
    git_trees.add_argument("--include-untracked", action="store_true")
    git_trees.add_argument(
        "--direction",
        choices=sorted(GIT_TREE_DIRECTIONS),
        default="observe",
    )
    git_trees.add_argument(
        "--require-executable", action="append", default=[]
    )

    expectation = subparsers.add_parser("compare-expectation")
    expectation.add_argument("produced", type=Path)
    expectation.add_argument("expected", type=Path)

    inspect = subparsers.add_parser("inspect-tree")
    inspect.add_argument("root", type=Path)

    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "compare-files":
            result = compare_files(args.source, args.projection, args.normalize_n)
            success = result["equal"]
        elif args.command == "compare-trees":
            result = compare_trees(args.master, args.copy)
            success = result["equal"]
        elif args.command == "git-manifest":
            result = git_manifest(
                args.repository,
                args.unit,
                revision=args.revision,
                include_untracked=args.include_untracked,
                required_executable=args.require_executable,
            )
            success = result["safe"]
        elif args.command == "compare-git-trees":
            result = compare_git_trees(
                args.repository,
                args.source_unit,
                args.projection_unit,
                revision=args.revision,
                include_untracked=args.include_untracked,
                direction=args.direction,
                required_executable=args.require_executable,
            )
            success = result["equal"]
        elif args.command == "compare-expectation":
            result = compare_expectations(args.produced, args.expected)
            success = result["pass"]
        elif args.command == "inspect-tree":
            result = inspect_tree(args.root)
            success = result["safe"]
        else:
            result = run_self_test()
            success = result["pass"]
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
