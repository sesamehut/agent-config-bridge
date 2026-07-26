#!/usr/bin/env python3
"""Validate a complete Bridge live-operation journal/v2 snapshot."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import ctypes
from ctypes import wintypes
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import fixture_harness as harness


VALIDATOR_SPEC = "bridge-live-operation-journal-validator/v2"
JOURNAL_SPEC = "bridge-live-operation-journal/v2"
CANONICALIZATION = "canonical-json/v1"
CHAIN_SPEC = "sha256/canonical-json/v1"
ALLOCATION_SPEC = "bridge-operation-allocation/v2"
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
ZERO_SHA256 = "0" * 64
HEX_40 = re.compile(r"[0-9a-f]{40}")
HEX_64 = re.compile(r"[0-9a-f]{64}")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
DECIMAL = re.compile(r"0|[1-9][0-9]*")
TOP_LEVEL_FIELDS = {
    "spec",
    "canonicalization",
    "operation",
    "repository",
    "plan",
    "fixture-binding",
    "closures",
    "path-operations",
    "lifecycle",
}
FAILURE_ORDER = (
    "canonical-document",
    "journal-schema",
    "journal-version",
    "authority-identity",
    "operation-binding",
    "repository-binding",
    "head-binding",
    "plan-document",
    "plan-digest",
    "formal-plan-validation",
    "fixture-binding",
    "closure-binding",
    "path-binding",
    "write-step-binding",
    "value-binding",
    "guarded-region",
    "lifecycle-chain",
    "lifecycle-semantics",
    "worktree-binding",
    "platform-capability",
    "cleanup-eligibility",
    "cleanup-drift",
)
FAILURE_IDS = frozenset(FAILURE_ORDER)
DOCUMENT_PATHS = {
    "marker": ".git/bridge-fixture.json",
    "envelope": f".git/{harness.REPLAY_INPUT_TARGET}",
    "commitment": f".git/{harness.REPLAY_COMMITMENT_TARGET}",
    "activation-profile": f".git/{harness.ACTIVATION_PROFILE_TARGET}",
    "write-capability": f".git/{harness.WRITE_CAPABILITY_TARGET}",
    "fault-schedule": f".git/{harness.FAULT_SCHEDULE_TARGET}",
}
WINDOWS_FORBIDDEN_CHARS = frozenset('<>:"/\\|?*')
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CONIN$",
    "CONOUT$",
    *{f"COM{index}" for index in range(1, 10)},
    *{f"LPT{index}" for index in range(1, 10)},
    *{f"COM{value}" for value in "¹²³"},
    *{f"LPT{value}" for value in "¹²³"},
}
EVENT_KINDS = {
    "prepared",
    "execution-started",
    "forward-attempted",
    "forward-observed",
    "compensation-started",
    "inverse-attempted",
    "inverse-observed",
    "terminal",
    "closed",
}
FORMAL_GIT_TIMEOUT_SECONDS = 60.0


class ValidationError(ValueError):
    """One classified journal validation failure."""

    def __init__(self, failure_id: str, message: str) -> None:
        super().__init__(message)
        if failure_id not in FAILURE_IDS:
            raise ValueError(f"unknown failure id: {failure_id}")
        self.failure_id = failure_id


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_canonical_value(value: Any, *, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_canonical_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(
                    "canonical-document",
                    f"{path}: canonical JSON key is not a string",
                )
            _validate_canonical_value(key, path=f"{path}.<key>")
            _validate_canonical_value(item, path=f"{path}.{key}")
        return
    raise ValidationError(
        "canonical-document",
        f"{path}: canonical JSON forbids numeric/unknown values",
    )


def canonical_json_bytes(value: Any) -> bytes:
    _validate_canonical_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _pairs_object(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(
                "canonical-document",
                f"duplicate canonical JSON key: {key}",
            )
        result[key] = value
    return result


def parse_canonical_json(data: bytes, *, label: str) -> Dict[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValidationError(
            "canonical-document", f"{label}: UTF-8 BOM is forbidden"
        )
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValidationError(
                    "canonical-document",
                    f"{label}: non-finite number {token} is forbidden",
                )
            ),
        )
    except ValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError(
            "canonical-document", f"{label}: invalid UTF-8 JSON"
        ) from error
    if not isinstance(value, dict):
        raise ValidationError(
            "canonical-document", f"{label}: root must be an object"
        )
    _validate_canonical_value(value, path=label)
    if canonical_json_bytes(value) != data:
        raise ValidationError(
            "canonical-document",
            f"{label}: bytes are not exact {CANONICALIZATION}",
        )
    return value


def _canonical_base64(value: Any, *, field: str) -> bytes:
    if not isinstance(value, str):
        raise ValidationError("value-binding", f"{field}: base64 is not text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValidationError(
            "value-binding", f"{field}: invalid base64"
        ) from error
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValidationError(
            "value-binding", f"{field}: base64 is not canonical"
        )
    return decoded


def strict_repo_relative(value: Any, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != unicodedata.normalize("NFC", value)
        or "\\" in value
        or value.startswith("/")
        or "\x00" in value
    ):
        raise ValidationError("path-binding", f"{field}: unsafe path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValidationError("path-binding", f"{field}: unsafe segment")
    for part in parts:
        if (
            part.endswith((" ", "."))
            or any(ord(character) < 0x20 for character in part)
            or any(character in WINDOWS_FORBIDDEN_CHARS for character in part)
            or part.split(".", 1)[0].upper() in WINDOWS_RESERVED
        ):
            raise ValidationError(
                "path-binding", f"{field}: Windows-unsafe segment"
            )
    return value


def _identity_from_stat(status: os.stat_result, *, kind: str) -> Dict[str, str]:
    return {
        "device": str(status.st_dev),
        "inode": str(status.st_ino),
        "kind": kind,
        "links": str(status.st_nlink),
        "platform": "windows" if os.name == "nt" else "posix",
    }


if os.name == "nt":
    class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]


    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _CREATE_FILE = _KERNEL32.CreateFileW
    _CREATE_FILE.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _CREATE_FILE.restype = wintypes.HANDLE
    _GET_FILE_INFO = _KERNEL32.GetFileInformationByHandle
    _GET_FILE_INFO.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION),
    ]
    _GET_FILE_INFO.restype = wintypes.BOOL
    _READ_FILE = _KERNEL32.ReadFile
    _READ_FILE.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _READ_FILE.restype = wintypes.BOOL
    _CLOSE_HANDLE = _KERNEL32.CloseHandle
    _CLOSE_HANDLE.argtypes = [wintypes.HANDLE]
    _CLOSE_HANDLE.restype = wintypes.BOOL
    _INVALID_HANDLE = wintypes.HANDLE(-1).value
    _GENERIC_READ = 0x80000000
    _FILE_SHARE_READ = 0x00000001
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000


def _win_identity(handle: int, *, wanted_kind: str) -> Dict[str, str]:
    info = _BY_HANDLE_FILE_INFORMATION()
    if not _GET_FILE_INFO(handle, ctypes.byref(info)):
        raise OSError(ctypes.get_last_error(), "GetFileInformationByHandle")
    is_directory = bool(info.dwFileAttributes & _FILE_ATTRIBUTE_DIRECTORY)
    is_reparse = bool(info.dwFileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT)
    if is_reparse or is_directory != (wanted_kind == "directory"):
        raise ValidationError(
            "authority-identity", "retained Windows handle kind/reparse mismatch"
        )
    return {
        "index-high": str(info.nFileIndexHigh),
        "index-low": str(info.nFileIndexLow),
        "kind": wanted_kind,
        "links": str(info.nNumberOfLinks),
        "platform": "windows",
        "volume": str(info.dwVolumeSerialNumber),
    }


class RetainedDirectory:
    """Retain one non-reparse directory identity until snapshot verification."""

    def __init__(
        self,
        path: Path,
        *,
        parent: Optional["RetainedDirectory"] = None,
        leaf_name: Optional[str] = None,
    ) -> None:
        self.path = Path(os.path.abspath(path))
        self.parent = parent
        self.leaf_name = leaf_name
        self.handle: Optional[int] = None
        try:
            before = self._entry_stat()
        except OSError as error:
            raise ValidationError(
                "authority-identity", "cannot inspect retained directory"
            ) from error
        if (
            not stat.S_ISDIR(before.st_mode)
            or stat.S_ISLNK(before.st_mode)
            or (os.name == "nt" and harness.is_reparse(self.path))
        ):
            raise ValidationError(
                "authority-identity", "retained directory is unsafe"
            )
        if os.name == "nt":
            handle = _CREATE_FILE(
                str(self.path),
                _GENERIC_READ,
                _FILE_SHARE_READ,
                None,
                _OPEN_EXISTING,
                _FILE_FLAG_BACKUP_SEMANTICS
                | _FILE_FLAG_OPEN_REPARSE_POINT,
                None,
            )
            if handle == _INVALID_HANDLE:
                raise ValidationError(
                    "authority-identity", "cannot retain Windows directory"
                )
            self.handle = int(handle)
            self.identity = _win_identity(
                self.handle, wanted_kind="directory"
            )
        else:
            if not getattr(os, "O_NOFOLLOW", 0):
                raise ValidationError(
                    "platform-capability",
                    "POSIX lacks O_NOFOLLOW for retained directories",
                )
            flags = os.O_RDONLY
            flags |= getattr(os, "O_DIRECTORY", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            try:
                if self.parent is None:
                    self.handle = os.open(self.path, flags)
                else:
                    if (
                        self.parent.handle is None
                        or os.open not in os.supports_dir_fd
                        or self.leaf_name is None
                    ):
                        raise ValidationError(
                            "platform-capability",
                            "POSIX lacks retained parent-relative directory open",
                        )
                    self.handle = os.open(
                        self.leaf_name,
                        flags,
                        dir_fd=self.parent.handle,
                    )
            except OSError as error:
                raise ValidationError(
                    "authority-identity", "cannot retain POSIX directory"
                ) from error
            opened = os.fstat(self.handle)
            self.identity = _identity_from_stat(opened, kind="directory")
            self._initial_guard = self._directory_guard(opened)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or (before.st_dev, before.st_ino)
                != (opened.st_dev, opened.st_ino)
            ):
                self.close()
                raise ValidationError(
                    "authority-identity",
                    "directory changed during retained open",
                )

    @staticmethod
    def _directory_guard(value: os.stat_result) -> Tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            stat.S_IFMT(value.st_mode),
            value.st_size,
            value.st_nlink,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    def _entry_stat(self) -> os.stat_result:
        if os.name == "nt" or self.parent is None:
            return os.lstat(self.path)
        if (
            self.parent.handle is None
            or os.stat not in os.supports_dir_fd
            or os.stat not in os.supports_follow_symlinks
            or self.leaf_name is None
        ):
            raise ValidationError(
                "platform-capability",
                "POSIX lacks retained parent-relative directory stat",
            )
        return os.stat(
            self.leaf_name,
            dir_fd=self.parent.handle,
            follow_symlinks=False,
        )

    def entry_stat(self, leaf_name: str) -> os.stat_result:
        if self.handle is None:
            raise ValidationError(
                "authority-identity", "retained directory is closed"
            )
        if os.name == "nt":
            return os.lstat(self.path / leaf_name)
        if (
            os.stat not in os.supports_dir_fd
            or os.stat not in os.supports_follow_symlinks
        ):
            raise ValidationError(
                "platform-capability",
                "POSIX lacks retained directory-relative stat",
            )
        return os.stat(
            leaf_name,
            dir_fd=self.handle,
            follow_symlinks=False,
        )

    def verify(self) -> None:
        if self.handle is None:
            raise ValidationError(
                "authority-identity", "retained directory is closed"
            )
        current = (
            _win_identity(self.handle, wanted_kind="directory")
            if os.name == "nt"
            else _identity_from_stat(
                os.fstat(self.handle), kind="directory"
            )
        )
        try:
            visible = self._entry_stat()
        except OSError as error:
            raise ValidationError(
                "authority-identity", "retained directory path disappeared"
            ) from error
        visible_identity = _identity_from_stat(visible, kind="directory")
        if os.name == "nt":
            visible_matches = (
                str(visible.st_ino)
                == str(
                    (int(current["index-high"]) << 32)
                    | int(current["index-low"])
                )
            )
        else:
            visible_matches = visible_identity == current
        if (
            current != self.identity
            or not visible_matches
            or stat.S_ISLNK(visible.st_mode)
            or (os.name == "nt" and harness.is_reparse(self.path))
            or (
                os.name != "nt"
                and (
                    self._directory_guard(os.fstat(self.handle))
                    != self._initial_guard
                    or self._directory_guard(visible)
                    != self._initial_guard
                )
            )
        ):
            raise ValidationError(
                "authority-identity", "retained directory identity drifted"
            )
        if self.parent is not None:
            self.parent.verify()

    def list_names(self) -> List[str]:
        if os.name == "nt":
            raise ValidationError(
                "platform-capability",
                "Windows lacks proven handle-relative lease enumeration",
            )
        if self.handle is None:
            raise ValidationError(
                "authority-identity", "retained directory is closed"
            )
        return sorted(os.listdir(self.handle))

    def close(self) -> None:
        if self.handle is None:
            return
        if os.name == "nt":
            _CLOSE_HANDLE(self.handle)
        else:
            os.close(self.handle)
        self.handle = None


class RetainedFile:
    """Read and revalidate one single-link file through retained authority."""

    def __init__(
        self,
        path: Path,
        *,
        label: str,
        parent: Optional[RetainedDirectory] = None,
        leaf_name: Optional[str] = None,
    ) -> None:
        self.path = Path(os.path.abspath(path))
        self.label = label
        self.parent = parent
        self.leaf_name = leaf_name or self.path.name
        self.handle: Optional[int] = None
        try:
            before = (
                os.lstat(self.path)
                if os.name == "nt"
                else self._parent_entry_stat()
            )
        except OSError as error:
            raise ValidationError(
                "authority-identity", f"{label}: cannot inspect file"
            ) from error
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before.st_mode)
            or before.st_nlink != 1
            or (os.name == "nt" and harness.is_reparse(self.path))
        ):
            raise ValidationError(
                "authority-identity",
                f"{label}: file is linked, reparse, or non-regular",
            )
        if os.name == "nt":
            handle = _CREATE_FILE(
                str(self.path),
                _GENERIC_READ,
                _FILE_SHARE_READ,
                None,
                _OPEN_EXISTING,
                _FILE_FLAG_OPEN_REPARSE_POINT | _FILE_FLAG_SEQUENTIAL_SCAN,
                None,
            )
            if handle == _INVALID_HANDLE:
                raise ValidationError(
                    "authority-identity", f"{label}: cannot retain file"
                )
            self.handle = int(handle)
            self.identity = _win_identity(self.handle, wanted_kind="file")
            if self.identity["links"] != "1":
                self.close()
                raise ValidationError(
                    "authority-identity", f"{label}: hardlink is forbidden"
            )
            self.data = self._read_windows()
        else:
            if (
                self.parent is None
                or self.parent.handle is None
                or os.open not in os.supports_dir_fd
                or not getattr(os, "O_NOFOLLOW", 0)
            ):
                raise ValidationError(
                    "platform-capability",
                    f"{label}: POSIX retained parent-relative read unavailable",
                )
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            flags |= getattr(os, "O_BINARY", 0)
            try:
                parent_before = self._parent_guard()
                self._initial_parent_guard = parent_before
                self.handle = os.open(
                    self.leaf_name,
                    flags,
                    dir_fd=self.parent.handle,
                )
            except OSError as error:
                raise ValidationError(
                    "authority-identity", f"{label}: cannot retain file"
                ) from error
            opened = os.fstat(self.handle)
            self.identity = _identity_from_stat(opened, kind="file")
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (before.st_dev, before.st_ino)
                != (opened.st_dev, opened.st_ino)
            ):
                self.close()
                raise ValidationError(
                    "authority-identity", f"{label}: retained identity mismatch"
                )
            opened_guard = self._file_guard(opened)
            first = self._read_posix()
            middle = os.fstat(self.handle)
            second = self._read_posix()
            closed_read = os.fstat(self.handle)
            if (
                opened_guard != self._file_guard(middle)
                or opened_guard != self._file_guard(closed_read)
                or first != second
                or len(first) != opened.st_size
                or parent_before != self._parent_guard()
            ):
                self.close()
                raise ValidationError(
                    "authority-identity",
                    f"{label}: file or parent drifted during retained read",
                )
            self._initial_guard = opened_guard
            self.data = first
            self.data_sha256 = _sha256(first)
        if len(self.data) > MAX_DOCUMENT_BYTES:
            self.close()
            raise ValidationError(
                "authority-identity", f"{label}: size bound exceeded"
            )

    @staticmethod
    def _file_guard(value: os.stat_result) -> Tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            stat.S_IFMT(value.st_mode),
            value.st_size,
            value.st_nlink,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    def _parent_guard(self) -> Tuple[int, ...]:
        if self.parent is None or self.parent.handle is None:
            raise ValidationError(
                "platform-capability",
                f"{self.label}: retained parent authority unavailable",
            )
        value = os.fstat(self.parent.handle)
        return (
            value.st_dev,
            value.st_ino,
            stat.S_IFMT(value.st_mode),
            value.st_nlink,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    def _parent_entry_stat(self) -> os.stat_result:
        if self.parent is None:
            raise ValidationError(
                "platform-capability",
                f"{self.label}: retained parent authority unavailable",
            )
        return self.parent.entry_stat(self.leaf_name)

    def _read_posix(self) -> bytes:
        assert self.handle is not None
        os.lseek(self.handle, 0, os.SEEK_SET)
        chunks: List[bytes] = []
        total = 0
        while True:
            chunk = os.read(self.handle, 65536)
            if not chunk:
                return b"".join(chunks)
            total += len(chunk)
            if total > MAX_DOCUMENT_BYTES:
                raise ValidationError(
                    "authority-identity",
                    f"{self.label}: size bound exceeded",
                )
            chunks.append(chunk)

    def _read_windows(self) -> bytes:
        assert self.handle is not None
        chunks: List[bytes] = []
        total = 0
        while True:
            buffer = ctypes.create_string_buffer(65536)
            count = wintypes.DWORD()
            if not _READ_FILE(
                self.handle,
                buffer,
                len(buffer),
                ctypes.byref(count),
                None,
            ):
                raise ValidationError(
                    "authority-identity",
                    f"{self.label}: retained ReadFile failed",
                )
            if count.value == 0:
                return b"".join(chunks)
            total += count.value
            if total > MAX_DOCUMENT_BYTES:
                raise ValidationError(
                    "authority-identity",
                    f"{self.label}: size bound exceeded",
                )
            chunks.append(buffer.raw[: count.value])

    def verify(self) -> None:
        if self.handle is None:
            raise ValidationError(
                "authority-identity", f"{self.label}: retained file is closed"
            )
        if os.name != "nt":
            assert self.parent is not None
            self.parent.verify()
            parent_before = self._parent_guard()
            before = os.fstat(self.handle)
            reread = self._read_posix()
            after = os.fstat(self.handle)
            try:
                visible = self._parent_entry_stat()
            except OSError as error:
                raise ValidationError(
                    "authority-identity", f"{self.label}: path disappeared"
                ) from error
            if (
                self._file_guard(before) != self._initial_guard
                or self._file_guard(after) != self._initial_guard
                or _identity_from_stat(visible, kind="file") != self.identity
                or self._file_guard(visible) != self._initial_guard
                or before.st_nlink != 1
                or reread != self.data
                or _sha256(reread) != self.data_sha256
                or len(reread) != before.st_size
                or parent_before != self._initial_parent_guard
                or parent_before != self._parent_guard()
            ):
                raise ValidationError(
                    "authority-identity",
                    f"{self.label}: retained bytes or identity drifted",
                )
            self.parent.verify()
            return
        current = (
            _win_identity(self.handle, wanted_kind="file")
            if os.name == "nt"
            else _identity_from_stat(os.fstat(self.handle), kind="file")
        )
        try:
            visible = os.lstat(self.path)
        except OSError as error:
            raise ValidationError(
                "authority-identity", f"{self.label}: path disappeared"
            ) from error
        if os.name == "nt":
            visible_matches = (
                str(visible.st_ino)
                == str(
                    (int(current["index-high"]) << 32)
                    | int(current["index-low"])
                )
            )
        else:
            visible_matches = (
                _identity_from_stat(visible, kind="file") == current
            )
        if (
            current != self.identity
            or current.get("links") != "1"
            or not visible_matches
            or stat.S_ISLNK(visible.st_mode)
            or (os.name == "nt" and harness.is_reparse(self.path))
        ):
            raise ValidationError(
                "authority-identity",
                f"{self.label}: retained file identity drifted",
            )

    def close(self) -> None:
        if self.handle is None:
            return
        if os.name == "nt":
            _CLOSE_HANDLE(self.handle)
        else:
            os.close(self.handle)
        self.handle = None


class RetainedTree:
    """Retain one root plus all authority/worktree handles in a validation."""

    def __init__(self, root: Path) -> None:
        self.root = Path(os.path.abspath(root))
        self.directories: Dict[str, RetainedDirectory] = {
            "": RetainedDirectory(self.root)
        }
        self.files: List[RetainedFile] = []
        self.missing: List[Tuple[RetainedDirectory, str]] = []

    @property
    def identity(self) -> Dict[str, str]:
        return self.directories[""].identity

    def _retain_parents(
        self, relative: str, *, missing_ok: bool
    ) -> Tuple[Path, RetainedDirectory, bool]:
        parts = relative.split("/")
        current = self.root
        accumulated: List[str] = []
        for segment in parts[:-1]:
            parent_key = "/".join(accumulated)
            parent = self.directories[parent_key]
            accumulated.append(segment)
            key = "/".join(accumulated)
            current = current / segment
            if key not in self.directories:
                try:
                    parent.entry_stat(segment)
                except FileNotFoundError:
                    if missing_ok:
                        self.missing.append((parent, segment))
                        return self.root.joinpath(*parts), parent, True
                    raise ValidationError(
                        "authority-identity",
                        "required retained directory is missing",
                    )
                self.directories[key] = RetainedDirectory(
                    current,
                    parent=parent,
                    leaf_name=segment,
                )
        parent_key = "/".join(parts[:-1])
        return (
            self.root.joinpath(*parts),
            self.directories[parent_key],
            False,
        )

    def read(
        self,
        relative: str,
        *,
        label: str,
        missing_ok: bool = False,
    ) -> Optional[RetainedFile]:
        relative = strict_repo_relative(relative, field=label)
        path, parent, missing_parent = self._retain_parents(
            relative, missing_ok=missing_ok
        )
        if missing_parent:
            return None
        leaf_name = relative.split("/")[-1]
        try:
            parent.entry_stat(leaf_name)
        except FileNotFoundError:
            if not missing_ok:
                raise ValidationError(
                    "authority-identity", f"{label}: required file is missing"
                )
            self.missing.append((parent, leaf_name))
            return None
        retained = RetainedFile(
            path,
            label=label,
            parent=parent,
            leaf_name=leaf_name,
        )
        self.files.append(retained)
        return retained

    def verify(self) -> None:
        for retained in self.files:
            retained.verify()
        for parent, leaf_name in self.missing:
            parent.verify()
            try:
                parent.entry_stat(leaf_name)
            except FileNotFoundError:
                continue
            else:
                raise ValidationError(
                    "authority-identity", "retained missing path appeared"
                )
        for key in sorted(
            self.directories, key=lambda item: item.count("/"), reverse=True
        ):
            self.directories[key].verify()

    def close(self) -> None:
        for retained in reversed(self.files):
            retained.close()
        for directory in sorted(
            self.directories.values(),
            key=lambda item: len(str(item.path)),
            reverse=True,
        ):
            directory.close()


def _identity_id(identity: Mapping[str, str]) -> str:
    return _sha256(canonical_json_bytes(dict(identity)))


def _document_binding(
    relative: str, retained: RetainedFile
) -> Dict[str, Any]:
    return {
        "identity": copy.deepcopy(retained.identity),
        "path": relative,
        "raw-sha256": _sha256(retained.data),
    }


def _require_fields(
    value: Any,
    fields: Sequence[str] | set[str],
    *,
    failure: str,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValidationError(failure, f"{label}: fields are not closed")
    return value


def _head_from_tree(tree: RetainedTree) -> Dict[str, Optional[str]]:
    head_file = tree.read(".git/HEAD", label="repository HEAD")
    assert head_file is not None
    try:
        text = head_file.data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValidationError("head-binding", "HEAD is not ASCII") from error
    if text.endswith("\n"):
        text = text[:-1]
    if text.startswith("ref: "):
        reference = strict_repo_relative(
            text[5:], field="repository HEAD reference"
        )
        if not reference.startswith("refs/"):
            raise ValidationError("head-binding", "HEAD ref is not under refs")
        ref_file = tree.read(
            f".git/{reference}",
            label="repository HEAD ref",
            missing_ok=True,
        )
        if ref_file is None:
            return {"oid": None, "ref": reference, "state": "unborn"}
        try:
            oid = ref_file.data.decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise ValidationError(
                "head-binding", "HEAD reference is not ASCII"
            ) from error
        if HEX_40.fullmatch(oid) is None:
            raise ValidationError("head-binding", "HEAD reference is invalid")
        return {"oid": oid, "ref": reference, "state": "attached"}
    oid = text.strip()
    if HEX_40.fullmatch(oid) is None:
        raise ValidationError("head-binding", "detached HEAD is invalid")
    return {"oid": oid, "ref": None, "state": "detached"}


def _decode_value(
    value: Any, *, field: str
) -> Tuple[str, Optional[bytes], Optional[str]]:
    if not isinstance(value, dict):
        raise ValidationError("value-binding", f"{field}: value is not object")
    if value.get("kind") == "missing":
        if set(value) != {"kind"}:
            raise ValidationError(
                "value-binding", f"{field}: missing value is not closed"
            )
        return ("missing", None, None)
    if set(value) != {"base64", "kind", "mode"} or value.get("kind") != "file":
        raise ValidationError(
            "value-binding", f"{field}: file value is not closed"
        )
    mode = value.get("mode")
    if mode not in {"100644", "100755"}:
        raise ValidationError("value-binding", f"{field}: invalid mode")
    data = _canonical_base64(value.get("base64"), field=field)
    return ("file", data, mode)


def _file_value(data: bytes, mode: str) -> Dict[str, str]:
    return {
        "base64": base64.b64encode(data).decode("ascii"),
        "kind": "file",
        "mode": mode,
    }


def _expected_operations(
    plan: Mapping[str, Any], payload: Mapping[str, Any]
) -> List[Dict[str, Any]]:
    input_tree = harness._facts_tree(payload["input"]["files"])
    render: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for item in payload["render"]["operations"]:
        path = strict_repo_relative(item.get("path"), field="render path")
        operation = item.get("operation")
        if operation not in {"create", "delete", "replace"}:
            raise ValidationError(
                "fixture-binding", "render operation is invalid"
            )
        key = (path, operation)
        if key in render:
            raise ValidationError(
                "fixture-binding", "render operation is duplicated"
            )
        render[key] = item
    expected: List[Dict[str, Any]] = []
    for row in plan["write_capabilities"]:
        (
            step,
            closure,
            path,
            operation,
            protocol,
            binding,
            inverse_protocol,
            inverse_binding,
        ) = row
        path = strict_repo_relative(path, field="plan write path")
        rendered = render.get((path, operation))
        if rendered is None:
            raise ValidationError(
                "fixture-binding", "plan write has no rendered operation"
            )
        pre_value = harness._journal_value(input_tree, path)
        if operation == "delete":
            intended: Dict[str, Any] = {"kind": "missing"}
        else:
            data = _canonical_base64(
                rendered.get("bytes_base64"), field="render bytes"
            )
            mode = rendered.get("mode")
            if mode not in {"100644", "100755"}:
                raise ValidationError(
                    "fixture-binding", "render mode is invalid"
                )
            if rendered.get("sha256") != _sha256(data):
                raise ValidationError(
                    "fixture-binding", "render digest is invalid"
                )
            intended = _file_value(data, mode)
        item = {
            "binding": binding,
            "closure": closure,
            "intended-post-value": intended,
            "inverse-binding": inverse_binding,
            "inverse-protocol": inverse_protocol,
            "operation": operation,
            "path": path,
            "pre-value": pre_value,
            "protocol": protocol,
            "step": step,
        }
        if protocol == "guarded-patch/v1":
            pre = _decode_value(pre_value, field="guarded preimage")[1]
            post = _decode_value(intended, field="guarded postimage")[1]
            if pre is None or post is None:
                raise ValidationError(
                    "guarded-region", "guarded operation requires files"
                )
            region = harness._guarded_region(pre, post)
            item["guarded-region"] = {
                "byte-offset": str(region["byte-offset"]),
                "new-base64": region["new-base64"],
                "old-base64": region["old-base64"],
            }
        expected.append(item)
    paths = [item["path"] for item in expected]
    folded = [path.casefold() for path in paths]
    if (
        len(paths) != len(set(paths))
        or len(folded) != len(set(folded))
    ):
        raise ValidationError(
            "path-binding", "operation paths collide canonically"
        )
    return expected


def _expected_closures(plan: Mapping[str, Any]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for row in plan["closures"]:
        closure, members, dependencies, selection, authorization, outcome = row
        if selection != "selected":
            continue
        result.append(
            {
                "authorization": authorization,
                "depends-on": (
                    [] if dependencies == "-" else dependencies.split("; ")
                ),
                "id": closure,
                "members": members.split("; "),
                "outcome": outcome,
                "selection": selection,
            }
        )
    return result


def _validate_serialized_operations(value: Any) -> None:
    if not isinstance(value, list):
        raise ValidationError(
            "write-step-binding", "path-operations is not an array"
        )
    paths: List[str] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError(
                "write-step-binding", "path operation is not an object"
            )
        if "path" not in item:
            raise ValidationError(
                "write-step-binding", "path operation lacks path"
            )
        paths.append(
            strict_repo_relative(item["path"], field="journal operation path")
        )
        if "pre-value" in item:
            _decode_value(item["pre-value"], field="journal pre-value")
        if "intended-post-value" in item:
            _decode_value(
                item["intended-post-value"],
                field="journal intended-post-value",
            )
        if "guarded-region" in item:
            region = item["guarded-region"]
            _require_fields(
                region,
                {"byte-offset", "new-base64", "old-base64"},
                failure="guarded-region",
                label="serialized guarded region",
            )
            if DECIMAL.fullmatch(str(region["byte-offset"])) is None:
                raise ValidationError(
                    "guarded-region", "guarded offset is not canonical decimal"
                )
            old = _canonical_base64(
                region["old-base64"], field="guarded old bytes"
            )
            new = _canonical_base64(
                region["new-base64"], field="guarded new bytes"
            )
            if "pre-value" in item and "intended-post-value" in item:
                pre = _decode_value(
                    item["pre-value"], field="guarded serialized pre"
                )[1]
                post = _decode_value(
                    item["intended-post-value"],
                    field="guarded serialized post",
                )[1]
                if pre is None or post is None:
                    raise ValidationError(
                        "guarded-region", "guarded values are not files"
                    )
                try:
                    harness._validate_guarded_region(
                        {
                            "byte-offset": int(region["byte-offset"]),
                            "new-base64": base64.b64encode(new).decode("ascii"),
                            "old-base64": base64.b64encode(old).decode("ascii"),
                        },
                        preimage=pre,
                        postimage=post,
                    )
                except (ValueError, harness.FixtureError) as error:
                    raise ValidationError(
                        "guarded-region",
                        "serialized guarded proof is invalid",
                    ) from error
    folded = [path.casefold() for path in paths]
    if (
        len(paths) != len(set(paths))
        or len(folded) != len(set(folded))
    ):
        raise ValidationError(
            "path-binding", "journal operation paths collide canonically"
        )


def _parse_plan_memory(data: bytes) -> Mapping[str, Any]:
    descriptor, name = tempfile.mkstemp(
        prefix="bridge-journal-plan-", suffix=".md"
    )
    path = Path(name)
    try:
        written = 0
        while written < len(data):
            count = os.write(descriptor, data[written:])
            if count <= 0:
                raise OSError("short plan scratch write")
            written += count
        os.close(descriptor)
        descriptor = -1
        plan = harness.parse_plan(path, expectation=False)
        harness._validate_confirmed_prewrite_plan(plan)
        return plan
    except (harness.FixtureError, OSError, UnicodeError, ValueError) as error:
        raise ValidationError(
            "plan-document", "confirmed pre-write plan is invalid"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _formal_git(
    root: Path,
    *arguments: str,
    formal_environment: Mapping[str, str],
) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "-C", str(root), *arguments]
    try:
        process = subprocess.run(
            command,
            env=dict(formal_environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=FORMAL_GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise ValidationError(
            "platform-capability",
            "prepared formal-validator Git command timed out: "
            + json.dumps(
                {
                    "arguments": list(arguments),
                    "repository": str(root),
                    "timeout_seconds": FORMAL_GIT_TIMEOUT_SECONDS,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        ) from error
    except OSError as error:
        raise ValidationError(
            "platform-capability",
            "prepared formal-validator Git command could not start: "
            + json.dumps(
                {
                    "arguments": list(arguments),
                    "error": str(error),
                    "repository": str(root),
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        ) from error
    if process.returncode != 0:
        raise ValidationError(
            "platform-capability",
            "prepared formal-validator Git command failed: "
            + json.dumps(
                {
                    "arguments": list(arguments),
                    "repository": str(root),
                    "returncode": process.returncode,
                    "stderr": process.stderr[:4096].decode(
                        "utf-8", errors="backslashreplace"
                    ),
                    "stderr_truncated": len(process.stderr) > 4096,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    return process


def _formal_plan_context(
    *,
    replay_input: str,
    root: Path,
    envelope: Mapping[str, Any],
    formal_environment: Mapping[str, str],
) -> Dict[str, Any]:
    resolved_root = root.resolve()
    untracked_result = _formal_git(
        resolved_root,
        "ls-files",
        "--others",
        "--exclude-standard",
        formal_environment=formal_environment,
    )
    try:
        actual_untracked = sorted(
            line.replace("\\", "/")
            for line in untracked_result.stdout.decode(
                "utf-8", errors="strict"
            ).strip().splitlines()
            if line
        )
    except UnicodeError as error:
        raise ValidationError(
            "formal-plan-validation",
            "prepared live-untracked context is not UTF-8",
        ) from error
    temporal_context = harness._derive_plan_temporal_context(
        envelope=envelope,
        lifecycle="prepared",
        actual_untracked=actual_untracked,
    )
    return {
        "binding": envelope["payload"]["binding"],
        "lifecycle": "prepared",
        "live_untracked": actual_untracked,
        "replay_input": replay_input,
        "resolved_root": str(resolved_root),
        "temporal_context": temporal_context,
    }


def _formal_child_diagnostic(
    process: subprocess.CompletedProcess[bytes],
    *,
    diagnostic_case: str,
    replay_input: str,
    root: Path,
    scratch_directory: Path,
) -> str:
    def captured(data: bytes) -> Dict[str, Any]:
        return {
            "bytes": len(data),
            "sha256": _sha256(data),
            "text": data[:4096].decode(
                "utf-8", errors="backslashreplace"
            ),
            "truncated": len(data) > 4096,
        }

    session_root = os.environ.get(
        "BRIDGE_JOURNAL_TEST_SESSION",
        os.environ.get("TEMP", ""),
    )
    return json.dumps(
        {
            "case": diagnostic_case,
            "child_returncode": process.returncode,
            "child_stderr": captured(process.stderr),
            "child_stdout": captured(process.stdout),
            "replay_input": replay_input,
            "repository": str(root),
            "scratch": str(scratch_directory),
            "session": session_root,
            "worker_pid": os.getpid(),
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sanitized_formal_environment(
    *,
    prepared_index: Path,
) -> Dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_INDEX_FILE": str(prepared_index),
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
    )
    return environment


def _prepared_formal_context(
    *,
    replay_input: str,
    root: Path,
    envelope: Mapping[str, Any],
    scratch_index: Path,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    formal_environment = _sanitized_formal_environment(
        prepared_index=scratch_index
    )
    _formal_git(
        root,
        "read-tree",
        "HEAD",
        formal_environment=formal_environment,
    )
    present_missing_paths: List[str] = []
    for path in (
        operation["path"]
        for operation in envelope["payload"]["capability"]["facts"][
            "operations"
        ]
        if operation["operation"] == "create"
    ):
        safe_path = strict_repo_relative(
            path, field="prepared missing plan path"
        )
        if os.path.lexists(Path(root).joinpath(*safe_path.split("/"))):
            present_missing_paths.append(safe_path)
    if present_missing_paths:
        _formal_git(
            root,
            "add",
            "-N",
            "--",
            *present_missing_paths,
            formal_environment=formal_environment,
        )
    context = _formal_plan_context(
        replay_input=replay_input,
        root=root,
        envelope=envelope,
        formal_environment=formal_environment,
    )
    return formal_environment, context


def _formal_plan_cli_snapshot(
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_path: Path,
    formal_environment: Mapping[str, str],
    diagnostic_case: str,
    timeout_seconds: float = 60.0,
) -> Dict[str, Any]:
    command = [
        sys.executable,
        "-B",
        str(Path(harness.__file__).resolve()),
        "validate-plan",
        replay_input,
        str(root),
        f"--lease={lease}",
        f"--plan={plan_path}",
        "--operation-lifecycle=prepared",
    ]
    try:
        process = subprocess.run(
            command,
            env=dict(formal_environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise ValidationError(
            "formal-plan-validation",
            "formal plan CLI parity timed out: "
            + json.dumps(
                {
                    "case": diagnostic_case,
                    "session": os.environ.get(
                        "BRIDGE_JOURNAL_TEST_SESSION",
                        os.environ.get("TEMP", ""),
                    ),
                    "timeout_seconds": timeout_seconds,
                    "worker_pid": os.getpid(),
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        ) from error
    except OSError as error:
        raise ValidationError(
            "formal-plan-validation",
            "formal plan CLI parity could not start: "
            + json.dumps(
                {
                    "case": diagnostic_case,
                    "error": str(error),
                    "session": os.environ.get(
                        "BRIDGE_JOURNAL_TEST_SESSION",
                        os.environ.get("TEMP", ""),
                    ),
                    "worker_pid": os.getpid(),
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        ) from error
    try:
        result = json.loads(process.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError(
            "formal-plan-validation",
            "formal plan CLI parity did not return JSON: "
            + _formal_child_diagnostic(
                process,
                diagnostic_case=diagnostic_case,
                replay_input=replay_input,
                root=root,
                scratch_directory=plan_path.parent,
            ),
        ) from error
    if (
        not isinstance(result, dict)
        or set(result)
        != {
            "context_sha256",
            "contract",
            "failures",
            "pass",
            "plan_sha256",
        }
        or process.returncode
        != (0 if result.get("pass") is True else 1)
    ):
        raise ValidationError(
            "formal-plan-validation",
            "formal plan CLI parity returned an invalid contract: "
            + _formal_child_diagnostic(
                process,
                diagnostic_case=diagnostic_case,
                replay_input=replay_input,
                root=root,
                scratch_directory=plan_path.parent,
            ),
        )
    return result


def _formal_plan_attestation(
    *,
    plan_bytes: bytes,
    replay_input: str,
    root: Path,
    lease: str,
    envelope: Mapping[str, Any],
    diagnostic_case: str = "formal-plan-attestation",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Derive context and validate retained bytes in one prepared index."""

    expected_plan_sha = _sha256(plan_bytes)
    scratch_directory = Path(
        tempfile.mkdtemp(
            prefix="bridge-journal-formal-attestation-",
            dir=harness.os_temp_root(),
        )
    )
    scratch_path = scratch_directory / "retained-plan.md"
    scratch_index = scratch_directory / "prepared-index"
    descriptor = -1
    retained_directory: Optional[RetainedDirectory] = None
    retained_plan: Optional[RetainedFile] = None
    primary_error: Optional[BaseException] = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(scratch_path, flags, 0o600)
        written = 0
        while written < len(plan_bytes):
            count = os.write(descriptor, plan_bytes[written:])
            if count <= 0:
                raise OSError("short formal plan scratch write")
            written += count
        os.fsync(descriptor)
        scratch_stat = os.fstat(descriptor)
        if (
            not stat.S_ISREG(scratch_stat.st_mode)
            or scratch_stat.st_nlink != 1
            or scratch_stat.st_size != len(plan_bytes)
        ):
            raise ValidationError(
                "platform-capability",
                "formal plan scratch identity is not provable",
            )
        os.close(descriptor)
        descriptor = -1
        formal_environment, context = _prepared_formal_context(
            replay_input=replay_input,
            root=root,
            envelope=envelope,
            scratch_index=scratch_index,
        )
        expected_context_sha = _sha256(canonical_json_bytes(context))
        retained_directory = RetainedDirectory(scratch_directory)
        retained_plan = RetainedFile(
            scratch_path,
            label="formal plan scratch",
            parent=retained_directory,
            leaf_name=scratch_path.name,
        )
        if (
            retained_plan.data != plan_bytes
            or _sha256(retained_plan.data) != expected_plan_sha
        ):
            raise ValidationError(
                "formal-plan-validation",
                "formal plan scratch differs from retained plan bytes",
            )
        raw_result, _ = harness._validate_plan_bytes_core(
            replay_input=replay_input,
            root=root,
            lease=lease,
            plan_bytes=retained_plan.data,
            lifecycle="prepared",
            envelope=envelope,
            actual_untracked=context["live_untracked"],
        )
        retained_plan.verify()
        if (
            not isinstance(raw_result, dict)
            or set(raw_result)
            != {
                "context_sha256",
                "contract",
                "failures",
                "pass",
                "plan_sha256",
            }
            or raw_result.get("contract") != harness.PLAN_VALIDATOR_SPEC
            or raw_result.get("plan_sha256") != expected_plan_sha
            or raw_result.get("context_sha256") != expected_context_sha
            or raw_result.get("pass") is not True
            or raw_result.get("failures") != []
        ):
            raise ValidationError(
                "formal-plan-validation",
                "formal plan validator rejected or returned unbound "
                "output: "
                + json.dumps(
                    {
                        "case": diagnostic_case,
                        "core_result": raw_result,
                        "replay_input": replay_input,
                        "repository": str(root),
                        "scratch": str(scratch_directory),
                        "session": os.environ.get(
                            "BRIDGE_JOURNAL_TEST_SESSION",
                            os.environ.get("TEMP", ""),
                        ),
                        "worker_pid": os.getpid(),
                    },
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        return copy.deepcopy(context), copy.deepcopy(raw_result)
    except BaseException as error:
        primary_error = error
        raise
    finally:
        cleanup_errors: List[BaseException] = []
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as error:
                cleanup_errors.append(error)
        if retained_plan is not None:
            try:
                retained_plan.close()
            except (OSError, ValidationError) as error:
                cleanup_errors.append(error)
        if retained_directory is not None:
            try:
                retained_directory.close()
            except (OSError, ValidationError) as error:
                cleanup_errors.append(error)
        try:
            harness.strict_remove_tree(scratch_directory)
        except (harness.FixtureError, OSError) as error:
            cleanup_errors.append(error)
        if cleanup_errors:
            detail = "; ".join(str(error) for error in cleanup_errors)
            if primary_error is not None:
                primary_error.add_note(
                    "formal attestation cleanup also failed: " + detail
                )
            else:
                cleanup_error = cleanup_errors[0]
                raise ValidationError(
                    "platform-capability",
                    "formal attestation scratch cleanup could not be "
                    "proven: "
                    + detail,
                ) from cleanup_error


def _formal_plan_result(
    *,
    plan_bytes: bytes,
    replay_input: str,
    root: Path,
    lease: str,
) -> Dict[str, Any]:
    """Validate with a context derived only from the bound public replay."""

    try:
        envelope = harness._validate_blind_installed_replay_input(
            root,
            lease=lease,
            replay_id=replay_input,
            require_input_tree=False,
        )
    except (
        harness.FixtureError,
        OSError,
        UnicodeError,
        ValueError,
    ) as error:
        raise ValidationError(
            "formal-plan-validation",
            "cannot authenticate the bound public formal-plan context",
        ) from error
    _, result = _formal_plan_attestation(
        plan_bytes=plan_bytes,
        replay_input=replay_input,
        root=root,
        lease=lease,
        envelope=envelope,
        diagnostic_case="formal-plan-result",
    )
    return result


def _bundle_snapshot(
    tree: RetainedTree,
    *,
    replay_input: str,
    lease: str,
    head: Mapping[str, Any],
) -> Tuple[
    Mapping[str, Any],
    Mapping[str, Any],
    Mapping[str, Any],
    Dict[str, Any],
]:
    if (
        head.get("state") == "unborn"
        or head.get("oid") is None
    ):
        raise ValidationError(
            "head-binding",
            "fixture-bound journal requires a committed baseline",
        )
    retained: Dict[str, Optional[RetainedFile]] = {}
    for label in (
        "marker",
        "envelope",
        "commitment",
        "activation-profile",
        "write-capability",
    ):
        retained[label] = tree.read(
            DOCUMENT_PATHS[label], label=f"fixture {label}"
        )
    assert all(retained[label] is not None for label in retained)
    marker_file = retained["marker"]
    envelope_file = retained["envelope"]
    commitment_file = retained["commitment"]
    profile_file = retained["activation-profile"]
    capability_file = retained["write-capability"]
    assert marker_file and envelope_file and commitment_file
    assert profile_file and capability_file
    marker = parse_canonical_json(marker_file.data, label="fixture marker")
    envelope = parse_canonical_json(
        envelope_file.data, label="replay envelope"
    )
    commitment = parse_canonical_json(
        commitment_file.data, label="replay commitment"
    )
    profile = parse_canonical_json(
        profile_file.data, label="activation profile"
    )
    capability = parse_canonical_json(
        capability_file.data, label="write capability"
    )
    _require_fields(
        envelope,
        {"version", "commitment_sha256", "payload"},
        failure="fixture-binding",
        label="replay envelope",
    )
    if envelope["version"] != harness.REPLAY_ENVELOPE_SPEC:
        raise ValidationError(
            "fixture-binding", "replay envelope version mismatch"
        )
    payload = envelope["payload"]
    _require_fields(
        payload,
        {
            "canonicalization",
            "binding",
            "profile",
            "capability",
            "fault_schedule",
            "decision",
            "input",
            "render",
        },
        failure="fixture-binding",
        label="replay payload",
    )
    if payload["canonicalization"] != CANONICALIZATION:
        raise ValidationError(
            "fixture-binding", "payload canonicalization mismatch"
        )
    binding = _require_fields(
        payload["binding"],
        {
            "suite",
            "scenario",
            "replay_input",
            "resolved_root",
            "nonce",
            "lease_sha256",
            "baseline_commit",
            "head",
            "marker_identity_sha256",
            "input_tree_sha256",
        },
        failure="fixture-binding",
        label="payload binding",
    )
    root = str(tree.root)
    head_oid = head.get("oid")
    if (
        binding["suite"] != harness.SUITE
        or binding["replay_input"] != replay_input
        or binding["resolved_root"] != root
        or binding["lease_sha256"] != _sha256(lease.encode("ascii"))
        or binding["head"] != head_oid
        or head_oid is None
    ):
        raise ValidationError(
            "fixture-binding", "payload root/lease/HEAD mismatch"
        )
    marker_identity = harness._marker_identity(marker)
    marker_identity_sha256 = _sha256(canonical_json_bytes(marker_identity))
    if (
        binding["nonce"] != marker.get("nonce")
        or binding["baseline_commit"] != marker.get("baseline_commit")
        or binding["marker_identity_sha256"] != marker_identity_sha256
        or marker.get("replay_input") != replay_input
    ):
        raise ValidationError(
            "fixture-binding", "marker identity binding mismatch"
        )
    _require_fields(
        commitment,
        {
            "version",
            "canonicalization",
            "binding",
            "components",
            "authentication",
        },
        failure="fixture-binding",
        label="replay commitment",
    )
    if (
        commitment["version"] != harness.REPLAY_COMMITMENT_SPEC
        or commitment["canonicalization"] != CANONICALIZATION
    ):
        raise ValidationError(
            "fixture-binding", "replay commitment version mismatch"
        )
    commitment_sha = _sha256(commitment_file.data)
    if (
        envelope["commitment_sha256"] != commitment_sha
        or marker.get("commitment_sha256") != commitment_sha
    ):
        raise ValidationError(
            "fixture-binding", "outer commitment reference mismatch"
        )
    wanted_commitment_binding = {
        "baseline_commit": binding["baseline_commit"],
        "head": binding["head"],
        "lease_sha256": binding["lease_sha256"],
        "nonce": binding["nonce"],
        "replay_input": replay_input,
        "resolved_root": root,
        "scenario": binding["scenario"],
        "suite": harness.SUITE,
    }
    if commitment["binding"] != wanted_commitment_binding:
        raise ValidationError(
            "fixture-binding", "commitment binding mismatch"
        )
    components = _require_fields(
        commitment["components"],
        {
            "marker_identity",
            "marker_identity_sha256",
            "activation_profile_sha256",
            "write_capability_sha256",
            "fault_schedule_sha256",
            "fault_phase_evidence_spec",
            "replay_payload_sha256",
        },
        failure="fixture-binding",
        label="commitment components",
    )
    if (
        components["marker_identity"] != marker_identity
        or components["marker_identity_sha256"] != marker_identity_sha256
        or components["activation_profile_sha256"]
        != _sha256(profile_file.data)
        or components["write_capability_sha256"]
        != _sha256(capability_file.data)
        or components["write_capability_sha256"]
        != marker.get("write_capability_sha256")
        or components["replay_payload_sha256"]
        != _sha256(canonical_json_bytes(payload))
        or payload["profile"].get("facts") != profile
        or payload["profile"].get("sha256") != _sha256(profile_file.data)
        or payload["capability"].get("facts") != capability
        or payload["capability"].get("sha256")
        != _sha256(capability_file.data)
    ):
        raise ValidationError(
            "fixture-binding", "commitment component mismatch"
        )
    fault_sha = components["fault_schedule_sha256"]
    if fault_sha is None:
        retained["fault-schedule"] = tree.read(
            DOCUMENT_PATHS["fault-schedule"],
            label="fixture fault schedule",
            missing_ok=True,
        )
        if (
            retained["fault-schedule"] is not None
            or marker.get("fault_schedule_sha256") is not None
            or payload["fault_schedule"] is not None
        ):
            raise ValidationError(
                "fixture-binding", "stray fault schedule"
            )
    else:
        fault_file = tree.read(
            DOCUMENT_PATHS["fault-schedule"],
            label="fixture fault schedule",
        )
        assert fault_file is not None
        retained["fault-schedule"] = fault_file
        fault = parse_canonical_json(
            fault_file.data, label="fault schedule"
        )
        if (
            _sha256(fault_file.data) != fault_sha
            or marker.get("fault_schedule_sha256") != fault_sha
            or payload["fault_schedule"].get("facts") != fault
            or payload["fault_schedule"].get("sha256") != fault_sha
        ):
            raise ValidationError(
                "fixture-binding", "fault schedule component mismatch"
            )
    authentication = _require_fields(
        commitment["authentication"],
        {"algorithm", "sha256"},
        failure="fixture-binding",
        label="commitment authentication",
    )
    unsigned = {
        key: value
        for key, value in commitment.items()
        if key != "authentication"
    }
    wanted_mac = hmac.new(
        lease.encode("ascii"),
        canonical_json_bytes(unsigned),
        hashlib.sha256,
    ).hexdigest()
    if (
        authentication["algorithm"] != "hmac-sha256/v1"
        or not hmac.compare_digest(
            str(authentication["sha256"]), wanted_mac
        )
    ):
        raise ValidationError(
            "fixture-binding", "commitment authentication mismatch"
        )
    documents: Dict[str, Any] = {}
    for label, retained_file in retained.items():
        documents[label] = (
            None
            if retained_file is None
            else _document_binding(DOCUMENT_PATHS[label], retained_file)
        )
    fixture_binding = {
        "baseline-commit": binding["baseline_commit"],
        "commitment-sha256": commitment_sha,
        "documents": documents,
        "head": copy.deepcopy(dict(head)),
        "lease-sha256": binding["lease_sha256"],
        "marker-identity-sha256": marker_identity_sha256,
        "nonce": binding["nonce"],
        "payload-sha256": _sha256(canonical_json_bytes(payload)),
        "replay-input": replay_input,
        "resolved-root": root,
        "scenario": binding["scenario"],
        "suite": harness.SUITE,
    }
    return envelope, payload, commitment, fixture_binding


def _lifecycle_anchor(journal: Mapping[str, Any]) -> str:
    static = {
        key: value for key, value in journal.items() if key != "lifecycle"
    }
    return _sha256(
        canonical_json_bytes(
            {
                "domain": "bridge-live-operation-journal-anchor/v2",
                "journal": static,
            }
        )
    )


def _event_hash(event: Mapping[str, Any], *, anchor_sha256: str) -> str:
    unsigned = {
        key: value for key, value in event.items() if key != "event-sha256"
    }
    return _sha256(
        canonical_json_bytes(
            {
                "anchor-sha256": anchor_sha256,
                "domain": "bridge-live-operation-lifecycle-event/v2",
                "event": unsigned,
            }
        )
    )


def make_event(
    *,
    anchor_sha256: str,
    ordinal: int,
    event: str,
    state: str,
    step: Optional[str],
    observation: Optional[Mapping[str, Any]],
    snapshot: Optional[Sequence[Mapping[str, Any]]],
    result: Optional[str],
    reason: Optional[str],
    previous_sha256: str,
) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "event": event,
        "event-sha256": "",
        "observation": (
            None
            if observation is None
            else copy.deepcopy(dict(observation))
        ),
        "ordinal": str(ordinal),
        "previous-sha256": previous_sha256,
        "reason": reason,
        "result": result,
        "snapshot": (
            None
            if snapshot is None
            else copy.deepcopy(list(snapshot))
        ),
        "state": state,
        "step": step,
    }
    item["event-sha256"] = _event_hash(
        item, anchor_sha256=anchor_sha256
    )
    return item


def _value_snapshot(
    operations: Sequence[Mapping[str, Any]],
    values: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    return [
        {
            "step": operation["step"],
            "value": copy.deepcopy(dict(values[operation["step"]])),
        }
        for operation in operations
    ]


def _snapshot_values(
    snapshot: Any,
    operations: Sequence[Mapping[str, Any]],
) -> Dict[str, Mapping[str, Any]]:
    if not isinstance(snapshot, list) or len(snapshot) != len(operations):
        raise ValidationError(
            "lifecycle-semantics", "terminal snapshot is incomplete"
        )
    result: Dict[str, Mapping[str, Any]] = {}
    for operation, item in zip(operations, snapshot):
        _require_fields(
            item,
            {"step", "value"},
            failure="lifecycle-semantics",
            label="lifecycle snapshot item",
        )
        step = operation["step"]
        if item["step"] != step:
            raise ValidationError(
                "lifecycle-semantics", "snapshot steps are out of order"
            )
        _decode_value(item["value"], field="lifecycle snapshot value")
        result[step] = item["value"]
    return result


def _validate_lifecycle(
    lifecycle: Any,
    operations: Sequence[Mapping[str, Any]],
    journal: Mapping[str, Any],
) -> Dict[str, Any]:
    lifecycle = _require_fields(
        lifecycle,
        {
            "algorithm",
            "anchor-sha256",
            "events",
            "head-sha256",
            "state",
        },
        failure="lifecycle-semantics",
        label="lifecycle",
    )
    wanted_anchor = _lifecycle_anchor(journal)
    if (
        lifecycle["algorithm"] != CHAIN_SPEC
        or lifecycle["anchor-sha256"] != wanted_anchor
        or not isinstance(lifecycle["events"], list)
    ):
        raise ValidationError(
            "lifecycle-chain", "lifecycle chain declaration is invalid"
        )
    events = lifecycle["events"]
    if not events:
        raise ValidationError("lifecycle-semantics", "event chain is empty")
    previous = wanted_anchor
    for ordinal, event in enumerate(events, start=1):
        _require_fields(
            event,
            {
                "event",
                "event-sha256",
                "observation",
                "ordinal",
                "previous-sha256",
                "reason",
                "result",
                "snapshot",
                "state",
                "step",
            },
            failure="lifecycle-chain",
            label="lifecycle event",
        )
        if (
            event["ordinal"] != str(ordinal)
            or event["event"] not in EVENT_KINDS
            or event["previous-sha256"] != previous
            or HEX_64.fullmatch(str(event["event-sha256"])) is None
            or event["event-sha256"]
            != _event_hash(event, anchor_sha256=wanted_anchor)
        ):
            raise ValidationError(
                "lifecycle-chain", "event hash chain is invalid"
            )
        previous = event["event-sha256"]
    if lifecycle["head-sha256"] != previous:
        raise ValidationError(
            "lifecycle-chain", "declared lifecycle head is stale"
        )
    first = events[0]
    if (
        first["event"] != "prepared"
        or first["state"] != "prepared"
        or first["step"] is not None
        or first["observation"] is not None
        or first["result"] is not None
        or first["reason"] is not None
    ):
        raise ValidationError(
            "lifecycle-semantics", "prepared must be the first event"
        )
    by_step = {operation["step"]: operation for operation in operations}
    current: Dict[str, Mapping[str, Any]] = {
        operation["step"]: operation["pre-value"]
        for operation in operations
    }
    if _snapshot_values(first["snapshot"], operations) != current:
        raise ValidationError(
            "lifecycle-semantics",
            "prepared snapshot is not the complete preimage",
        )
    execution_started = False
    successful: List[str] = []
    compensated: List[str] = []
    pending_forward: Optional[str] = None
    pending_inverse: Optional[str] = None
    failure_step: Optional[str] = None
    failure_value: Optional[Mapping[str, Any]] = None
    failure_unprovable = False
    compensation_started = False
    compensation_failed_step: Optional[str] = None
    terminal_result: Optional[str] = None
    terminal_snapshot: Optional[List[Mapping[str, Any]]] = None
    closed = False
    for index, event in enumerate(events[1:], start=1):
        kind = event["event"]
        step = event["step"]
        observation = event["observation"]
        snapshot = event["snapshot"]
        result = event["result"]
        reason = event["reason"]
        if kind == "execution-started":
            if (
                execution_started
                or successful
                or step is not None
                or observation is not None
                or snapshot is not None
                or result is not None
                or reason is not None
                or event["state"] != "executing"
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "execution-started is duplicated or malformed",
                )
            execution_started = True
            continue
        if kind == "forward-attempted":
            wanted = str(len(successful) + 1)
            if (
                not execution_started
                or pending_forward is not None
                or failure_step is not None
                or step != wanted
                or observation is not None
                or snapshot is not None
                or result is not None
                or reason is not None
                or event["state"] != "executing"
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "forward attempt is not an ordered prefix",
                )
            pending_forward = step
            continue
        if kind == "forward-observed":
            if (
                step != pending_forward
                or step not in by_step
                or observation is None
                or snapshot is not None
                or result is not None
                or reason not in {None, "unprovable"}
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "forward observation lacks its exact attempt",
                )
            _decode_value(
                observation, field="forward observed value"
            )
            operation = by_step[step]
            pending_forward = None
            current[step] = observation
            if (
                observation == operation["intended-post-value"]
                and reason is None
            ):
                successful.append(step)
                wanted_state = "executing"
            else:
                failure_step = step
                failure_value = observation
                failure_unprovable = reason == "unprovable"
                wanted_state = (
                    "failed"
                    if not successful
                    and observation == operation["pre-value"]
                    and not failure_unprovable
                    else "executing"
                )
            if event["state"] != wanted_state:
                raise ValidationError(
                    "lifecycle-semantics",
                    "forward observation state is inconsistent",
                )
            continue
        if kind == "compensation-started":
            if (
                failure_step is None
                or not successful
                or compensation_started
                or pending_forward is not None
                or step is not None
                or observation is not None
                or snapshot is not None
                or result is not None
                or reason is not None
                or event["state"] != "compensating"
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "compensation-started is not justified",
                )
            if any(
                by_step[item]["inverse-protocol"] == "unavailable"
                or by_step[item]["inverse-binding"] == "-"
                for item in successful
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "compensation lacks complete inverse attestations",
                )
            compensation_started = True
            continue
        if kind == "inverse-attempted":
            wanted_index = len(successful) - len(compensated) - 1
            wanted = successful[wanted_index] if wanted_index >= 0 else None
            if (
                not compensation_started
                or pending_inverse is not None
                or compensation_failed_step is not None
                or step != wanted
                or observation is not None
                or snapshot is not None
                or result is not None
                or reason is not None
                or event["state"] != "compensating"
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "inverse attempt is not strict reverse order",
                )
            pending_inverse = step
            continue
        if kind == "inverse-observed":
            if (
                step != pending_inverse
                or step not in by_step
                or observation is None
                or snapshot is not None
                or result is not None
                or reason not in {None, "unprovable"}
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "inverse observation lacks its exact attempt",
                )
            _decode_value(observation, field="inverse observed value")
            pending_inverse = None
            current[step] = observation
            if (
                observation == by_step[step]["pre-value"]
                and reason is None
            ):
                compensated.append(step)
            else:
                compensation_failed_step = step
                failure_unprovable = reason == "unprovable"
            if event["state"] != "compensating":
                raise ValidationError(
                    "lifecycle-semantics",
                    "inverse observation state is inconsistent",
                )
            continue
        if kind == "terminal":
            if (
                terminal_result is not None
                or closed
                or pending_forward is not None
                or pending_inverse is not None
                or step is not None
                or observation is not None
                or reason is not None
                or result not in {
                    "applied",
                    "failed",
                    "compensated",
                    "partial",
                }
                or event["state"] != result
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "terminal event is malformed",
                )
            snapshot_values = _snapshot_values(snapshot, operations)
            if snapshot_values != current:
                raise ValidationError(
                    "lifecycle-semantics",
                    "terminal snapshot differs from observed state",
                )
            applied = (
                len(successful) == len(operations)
                and failure_step is None
            )
            failed = (
                failure_step == "1"
                and not successful
                and failure_value == by_step["1"]["pre-value"]
                and not failure_unprovable
            )
            compensated_complete = (
                failure_step is not None
                and failure_value
                == by_step[failure_step]["pre-value"]
                and bool(successful)
                and compensation_started
                and compensated == list(reversed(successful))
                and compensation_failed_step is None
                and not failure_unprovable
                and all(
                    current[item["step"]] == item["pre-value"]
                    for item in operations
                )
            )
            wanted_result = (
                "applied"
                if applied
                else "failed"
                if failed
                else "compensated"
                if compensated_complete
                else "partial"
            )
            if result != wanted_result:
                raise ValidationError(
                    "lifecycle-semantics",
                    "terminal result hides execution evidence",
                )
            terminal_result = result
            terminal_snapshot = copy.deepcopy(snapshot)
            if result == "partial" and index != len(events) - 1:
                raise ValidationError(
                    "lifecycle-semantics",
                    "partial is terminal and may not be closed",
                )
            continue
        if kind == "closed":
            if (
                terminal_result not in {
                    "applied",
                    "failed",
                    "compensated",
                }
                or closed
                or index != len(events) - 1
                or step is not None
                or observation is not None
                or reason is not None
                or result != terminal_result
                or event["state"] != "closed"
                or snapshot != terminal_snapshot
            ):
                raise ValidationError(
                    "lifecycle-semantics",
                    "closed does not preserve a complete terminal proof",
                )
            closed = True
            continue
        raise ValidationError(
            "lifecycle-semantics", "unexpected lifecycle event"
        )
    if lifecycle["state"] != events[-1]["state"]:
        raise ValidationError(
            "lifecycle-semantics", "declared lifecycle state is stale"
        )
    if closed:
        derived_result = terminal_result
        derived_state = "closed"
    elif terminal_result is not None:
        derived_result = terminal_result
        derived_state = terminal_result
    elif compensation_started:
        derived_result = "compensating"
        derived_state = "compensating"
    elif failure_step is not None:
        derived_result = "failed"
        derived_state = events[-1]["state"]
    elif execution_started:
        derived_result = "executing"
        derived_state = "executing"
    else:
        derived_result = "prepared"
        derived_state = "prepared"
    return {
        "chain-sha256": previous,
        "expected-live": current,
        "result": derived_result,
        "state": derived_state,
        "terminal": terminal_result is not None,
    }


def _observe_worktree(
    tree: RetainedTree,
    operation: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> Mapping[str, Any]:
    kind, data, mode = _decode_value(expected, field="expected live value")
    retained = tree.read(
        operation["path"],
        label=f"worktree {operation['path']}",
        missing_ok=True,
    )
    if kind == "missing":
        if retained is not None:
            raise ValidationError(
                "worktree-binding", "expected missing path is present"
            )
        return {"kind": "missing"}
    if retained is None or data is None or mode is None:
        raise ValidationError(
            "worktree-binding", "expected live file is missing"
        )
    if os.name == "nt":
        if mode != "100644":
            raise ValidationError(
                "platform-capability",
                "Windows fixture mode cannot prove executable-bit identity",
            )
        observed_mode = "100644"
    else:
        status = os.fstat(retained.handle)  # type: ignore[arg-type]
        observed_mode = (
            "100755" if status.st_mode & stat.S_IXUSR else "100644"
        )
    observed = _file_value(retained.data, observed_mode)
    if observed != expected:
        raise ValidationError(
            "worktree-binding", "live worktree value differs from lifecycle"
        )
    return observed


def _platform_capability() -> Dict[str, Any]:
    handle_relative = (
        os.name != "nt"
        and hasattr(os, "supports_dir_fd")
        and os.unlink in os.supports_dir_fd
    )
    return {
        "cleanup-revalidation": handle_relative,
        "handle-relative-delete": handle_relative,
        "retained-authority-read": True,
        "reason": (
            None
            if handle_relative
            else "platform lacks proven handle-relative cleanup/delete"
        ),
    }


def _validate_once(
    *,
    replay_input: str,
    root_path: Path,
    lease: str,
    plan_path: Path,
    journal_path: Path,
    cleanup_snapshot: bool,
) -> Dict[str, Any]:
    root = RetainedTree(root_path)
    plan_directory: Optional[RetainedDirectory] = None
    plan_file: Optional[RetainedFile] = None
    lease_directory: Optional[RetainedDirectory] = None
    journal_file: Optional[RetainedFile] = None
    try:
        head = _head_from_tree(root)
        envelope, payload, _, fixture_binding = _bundle_snapshot(
            root,
            replay_input=replay_input,
            lease=lease,
            head=head,
        )
        plan_absolute = Path(os.path.abspath(plan_path))
        plan_directory = RetainedDirectory(plan_absolute.parent)
        plan_file = RetainedFile(
            plan_absolute,
            label="confirmed plan",
            parent=plan_directory,
            leaf_name=plan_absolute.name,
        )
        plan_sha = _sha256(plan_file.data)
        plan = _parse_plan_memory(plan_file.data)
        expected_operations = _expected_operations(plan, payload)
        profile_rows, operation_rows = harness._capability_rows_from_envelope(
            envelope
        )
        if (
            plan["capability_profiles"] != profile_rows
            or plan["write_capabilities"] != operation_rows
        ):
            raise ValidationError(
                "formal-plan-validation",
                "plan capabilities differ from replay attestation",
            )
        decision = payload["decision"]
        if isinstance(decision, dict):
            expected_adoption = [
                (
                    item["id"],
                    item["lines"],
                    item["disposition"],
                    item["destination"],
                    item["decision"],
                )
                for item in decision.get("segments", [])
            ]
            if plan["adoption"] != expected_adoption:
                raise ValidationError(
                    "formal-plan-validation",
                    "plan adoption differs from replay decision",
                )
        journal_absolute = Path(os.path.abspath(journal_path))
        if journal_absolute.name != "journal.json":
            raise ValidationError(
                "operation-binding", "journal leaf must be journal.json"
            )
        lease_directory = RetainedDirectory(journal_absolute.parent)
        journal_file = RetainedFile(
            journal_absolute,
            label="live operation journal",
            parent=lease_directory,
            leaf_name=journal_absolute.name,
        )
        journal = parse_canonical_json(
            journal_file.data, label="live operation journal"
        )
        if set(journal) != TOP_LEVEL_FIELDS:
            raise ValidationError(
                "journal-schema", "journal top-level fields are not closed"
            )
        if (
            journal["spec"] != JOURNAL_SPEC
            or journal["canonicalization"] != CANONICALIZATION
        ):
            raise ValidationError(
                "journal-version", "journal v2 declaration mismatch"
            )
        operation = _require_fields(
            journal["operation"],
            {"allocation", "id"},
            failure="operation-binding",
            label="operation",
        )
        allocation = _require_fields(
            operation["allocation"],
            {"contract", "lease", "lease-name", "nonce"},
            failure="operation-binding",
            label="operation allocation",
        )
        lease_binding = _require_fields(
            allocation["lease"],
            {"directory", "identity"},
            failure="operation-binding",
            label="operation lease",
        )
        operation_id = operation["id"]
        if (
            allocation["contract"] != ALLOCATION_SPEC
            or not isinstance(operation_id, str)
            or not TOKEN.fullmatch(operation_id)
        ):
            raise ValidationError(
                "operation-binding", "operation allocation/id is invalid"
            )
        prefix = harness._journal_lease_prefix(operation_id)
        parent_name = journal_absolute.parent.name
        if (
            journal_absolute.parent.parent
            != harness.os_temp_root().resolve()
            or not parent_name.startswith(prefix)
        ):
            raise ValidationError(
                "operation-binding", "operation lease location is invalid"
            )
        actual_nonce = parent_name[len(prefix) :]
        if (
            not actual_nonce
            or re.fullmatch(r"[A-Za-z0-9_-]+", actual_nonce) is None
            or allocation["nonce"] != actual_nonce
            or allocation["lease-name"] != parent_name
            or lease_binding["directory"] != str(journal_absolute.parent)
            or lease_binding["identity"] != lease_directory.identity
            or str(journal_absolute.parent).startswith(str(root.root) + os.sep)
        ):
            raise ValidationError(
                "operation-binding", "operation nonce/lease identity mismatch"
            )
        repository = _require_fields(
            journal["repository"],
            {"git-directory", "head", "identity", "resolved-root"},
            failure="repository-binding",
            label="repository",
        )
        git_directory = _require_fields(
            repository["git-directory"],
            {"identity", "path"},
            failure="repository-binding",
            label="repository git directory",
        )
        if (
            repository["resolved-root"] != str(root.root)
            or repository["identity"] != root.identity
            or git_directory["path"] != ".git"
            or git_directory["identity"]
            != root.directories[".git"].identity
        ):
            raise ValidationError(
                "repository-binding", "repository root identity mismatch"
            )
        if repository["head"] != head:
            raise ValidationError("head-binding", "repository HEAD mismatch")
        plan_binding = _require_fields(
            journal["plan"],
            {
                "identity",
                "sha256",
                "validation-context",
                "validation-context-sha256",
                "validation-result",
                "validation-result-sha256",
            },
            failure="plan-digest",
            label="plan",
        )
        if (
            plan_binding["sha256"] != plan_sha
            or plan_binding["identity"] != plan_file.identity
        ):
            raise ValidationError(
                "plan-digest", "plan digest/identity mismatch"
            )
        wanted_context, wanted_formal = _formal_plan_attestation(
            plan_bytes=plan_file.data,
            replay_input=replay_input,
            root=root.root,
            lease=lease,
            envelope=envelope,
            diagnostic_case=(
                "journal-validate:"
                + str(journal["operation"]["id"])
            ),
        )
        wanted_context_sha = _sha256(
            canonical_json_bytes(wanted_context)
        )
        if (
            plan_binding["validation-context"] != wanted_context
            or plan_binding["validation-context-sha256"]
            != wanted_context_sha
            or plan_binding["validation-result"] != wanted_formal
            or plan_binding["validation-result-sha256"]
            != _sha256(canonical_json_bytes(wanted_formal))
        ):
            raise ValidationError(
                "formal-plan-validation",
                "formal validator result/context mismatch",
            )
        if journal["fixture-binding"] != fixture_binding:
            raise ValidationError(
                "fixture-binding", "complete fixture binding mismatch"
            )
        expected_closures = _expected_closures(plan)
        if journal["closures"] != expected_closures:
            raise ValidationError(
                "closure-binding", "closure members/dependencies mismatch"
            )
        _validate_serialized_operations(journal["path-operations"])
        if journal["path-operations"] != expected_operations:
            raise ValidationError(
                "write-step-binding",
                "journal operations differ from attested ordered steps",
            )
        for item in expected_operations:
            _decode_value(item["pre-value"], field="pre-value")
            _decode_value(
                item["intended-post-value"], field="intended-post-value"
            )
            if item["protocol"] == "guarded-patch/v1":
                region = item["guarded-region"]
                _require_fields(
                    region,
                    {"byte-offset", "old-base64", "new-base64"},
                    failure="guarded-region",
                    label="guarded region",
                )
                if DECIMAL.fullmatch(str(region["byte-offset"])) is None:
                    raise ValidationError(
                        "guarded-region", "guarded offset is not canonical"
                    )
                old = _canonical_base64(
                    region["old-base64"], field="guarded old bytes"
                )
                new = _canonical_base64(
                    region["new-base64"], field="guarded new bytes"
                )
                pre = _decode_value(
                    item["pre-value"], field="guarded pre"
                )[1]
                post = _decode_value(
                    item["intended-post-value"], field="guarded post"
                )[1]
                if pre is None or post is None:
                    raise ValidationError(
                        "guarded-region", "guarded values are not files"
                    )
                wanted_region = {
                    "byte-offset": int(region["byte-offset"]),
                    "old-base64": base64.b64encode(old).decode("ascii"),
                    "new-base64": base64.b64encode(new).decode("ascii"),
                }
                try:
                    harness._validate_guarded_region(
                        wanted_region, preimage=pre, postimage=post
                    )
                except harness.FixtureError as error:
                    raise ValidationError(
                        "guarded-region", "guarded proof is invalid"
                    ) from error
        lifecycle = _validate_lifecycle(
            journal["lifecycle"], expected_operations, journal
        )
        if lifecycle["terminal"]:
            for item in expected_operations:
                _observe_worktree(
                    root,
                    item,
                    lifecycle["expected-live"][item["step"]],
                )
        root.verify()
        plan_file.verify()
        plan_directory.verify()
        lease_directory.verify()
        journal_file.verify()
        if cleanup_snapshot:
            if lifecycle["state"] != "closed" or lifecycle["result"] not in {
                "applied",
                "compensated",
                "failed",
            }:
                raise ValidationError(
                    "cleanup-eligibility",
                    "only closed complete outcomes are cleanup eligible",
                )
            if lease_directory.list_names() != ["journal.json"]:
                raise ValidationError(
                    "cleanup-drift", "operation lease has siblings"
                )
            root.verify()
            plan_file.verify()
            plan_directory.verify()
            lease_directory.verify()
            journal_file.verify()
        return {
            "cleanup-eligible": (
                lifecycle["state"] == "closed"
                and lifecycle["result"]
                in {"applied", "compensated", "failed"}
            ),
            "journal-file-identity": copy.deepcopy(journal_file.identity),
            "journal-sha256": _sha256(journal_file.data),
            "lease-identity": copy.deepcopy(lease_directory.identity),
            "lifecycle": {
                "chain-sha256": lifecycle["chain-sha256"],
                "result": lifecycle["result"],
                "state": lifecycle["state"],
            },
            "plan-sha256": plan_sha,
        }
    finally:
        if journal_file is not None:
            journal_file.close()
        if lease_directory is not None:
            lease_directory.close()
        if plan_file is not None:
            plan_file.close()
        if plan_directory is not None:
            plan_directory.close()
        root.close()


def _add_failure(failures: List[str], failure_id: str) -> None:
    if failure_id not in FAILURE_IDS:
        raise ValueError(f"unknown failure id: {failure_id}")
    if failure_id not in failures:
        failures.append(failure_id)


def _ordered_failures(failures: Sequence[str]) -> List[str]:
    present = set(failures)
    return [failure for failure in FAILURE_ORDER if failure in present]


def cleanup_receipt(
    validated: Mapping[str, Any],
    revalidated: Mapping[str, Any],
) -> Dict[str, str]:
    stable_keys = (
        "journal-file-identity",
        "journal-sha256",
        "lease-identity",
        "lifecycle",
        "plan-sha256",
    )
    if any(validated[key] != revalidated[key] for key in stable_keys):
        raise ValidationError(
            "cleanup-drift", "independent cleanup snapshot drifted"
        )
    return {
        "file-id": _identity_id(revalidated["journal-file-identity"]),
        "journal-sha": revalidated["journal-sha256"],
        "lease-id": _identity_id(revalidated["lease-identity"]),
    }


def validate_journal(
    *,
    replay_input: str,
    root: Path,
    lease: str,
    plan_path: Path,
    journal_path: Path,
    request_cleanup_receipt: bool = False,
) -> Dict[str, Any]:
    failures: List[str] = []
    failure_details: List[str] = []
    snapshot: Optional[Dict[str, Any]] = None
    receipt: Optional[Dict[str, str]] = None
    capability = _platform_capability()
    try:
        snapshot = _validate_once(
            replay_input=replay_input,
            root_path=root,
            lease=lease,
            plan_path=plan_path,
            journal_path=journal_path,
            cleanup_snapshot=False,
        )
    except ValidationError as error:
        _add_failure(failures, error.failure_id)
        failure_details.append(f"{error.failure_id}: {error}")
    except (OSError, harness.FixtureError, UnicodeError, ValueError) as error:
        _add_failure(failures, "authority-identity")
        failure_details.append(f"authority-identity: {error}")
    if request_cleanup_receipt:
        if snapshot is None or not snapshot["cleanup-eligible"]:
            _add_failure(failures, "cleanup-eligibility")
        elif not capability["cleanup-revalidation"]:
            _add_failure(failures, "platform-capability")
            _add_failure(failures, "cleanup-eligibility")
        else:
            try:
                revalidated = _validate_once(
                    replay_input=replay_input,
                    root_path=root,
                    lease=lease,
                    plan_path=plan_path,
                    journal_path=journal_path,
                    cleanup_snapshot=True,
                )
                receipt = cleanup_receipt(snapshot, revalidated)
            except ValidationError as error:
                _add_failure(failures, error.failure_id)
                _add_failure(failures, "cleanup-eligibility")
                failure_details.append(f"{error.failure_id}: {error}")
            except (
                OSError,
                harness.FixtureError,
                UnicodeError,
                ValueError,
            ) as error:
                _add_failure(failures, "cleanup-drift")
                _add_failure(failures, "cleanup-eligibility")
                failure_details.append(f"cleanup-drift: {error}")
    failures = _ordered_failures(failures)
    return {
        "cleanup-receipt": receipt,
        "contract": VALIDATOR_SPEC,
        "failure-details": failure_details,
        "failures": failures,
        "journal-sha256": (
            None if snapshot is None else snapshot["journal-sha256"]
        ),
        "lifecycle": None if snapshot is None else snapshot["lifecycle"],
        "pass": not failures,
        "plan-sha256": (
            None if snapshot is None else snapshot["plan-sha256"]
        ),
        "platform-capability": capability,
    }


def command_validate_journal(arguments: argparse.Namespace) -> int:
    result = validate_journal(
        replay_input=arguments.replay_input,
        root=Path(arguments.worktree),
        lease=arguments.lease,
        plan_path=Path(arguments.plan),
        journal_path=Path(arguments.journal),
        request_cleanup_receipt=arguments.request_cleanup_receipt,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate exact Bridge live-operation journal/v2 bytes."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate-journal")
    validate_parser.add_argument("replay_input")
    validate_parser.add_argument("worktree")
    validate_parser.add_argument("--lease", required=True)
    validate_parser.add_argument("--plan", required=True)
    validate_parser.add_argument("--journal", required=True)
    validate_parser.add_argument(
        "--request-cleanup-receipt", action="store_true"
    )
    validate_parser.set_defaults(function=command_validate_journal)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return arguments.function(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
