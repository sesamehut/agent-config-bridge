"""No-follow, retained-handle access to one regular root-child file."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from .fixture_support import FixtureError


MAX_FIXTURE_FILE_BYTES = 16 * 1024 * 1024


def _root_child_name(target: str) -> str:
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
    stem = target.split(".", 1)[0].casefold() if isinstance(target, str) else ""
    if (
        not isinstance(target, str)
        or not target
        or target in {".", ".."}
        or "/" in target
        or "\\" in target
        or "\x00" in target
        or any(character in '<>:"|?*' for character in target)
        or any(ord(character) < 32 for character in target)
        or target.endswith((".", " "))
        or stem in reserved
        or re.match(r"^[A-Za-z]:", target)
    ):
        raise FixtureError("safe adapter target must be one root-child name")
    return target


def _posix_identity(status: os.stat_result) -> Dict[str, int]:
    return {
        "device": int(status.st_dev),
        "inode": int(status.st_ino),
        "links": int(status.st_nlink),
    }


def _posix_root_identity(status: os.stat_result) -> Dict[str, int]:
    return {
        "device": int(status.st_dev),
        "inode": int(status.st_ino),
    }


def _posix_open(
    root: Path,
    target: str,
    *,
    writable: bool,
) -> Tuple[int, int, Dict[str, int], Dict[str, int], str]:
    target = _root_child_name(target)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if (
        not nofollow
        or not directory
        or os.open not in getattr(os, "supports_dir_fd", set())
    ):
        raise FixtureError(
            "safe adapter lacks required POSIX no-follow/dir-fd support"
        )
    root_flags = os.O_RDONLY | directory | nofollow
    leaf_flags = (os.O_RDWR if writable else os.O_RDONLY) | nofollow
    root_fd = -1
    leaf_fd = -1
    try:
        root_fd = os.open(root, root_flags)
        root_status = os.fstat(root_fd)
        if not stat.S_ISDIR(root_status.st_mode):
            raise FixtureError("safe adapter root handle is not a directory")
        root_identity = _posix_root_identity(root_status)
        leaf_fd = os.open(target, leaf_flags, dir_fd=root_fd)
        leaf_status = os.fstat(leaf_fd)
        if (
            not stat.S_ISREG(leaf_status.st_mode)
            or leaf_status.st_nlink != 1
        ):
            raise FixtureError(
                "safe adapter leaf must be a single-link regular file"
            )
        identity = _posix_identity(leaf_status)
        mode = (
            "100755"
            if leaf_status.st_mode & stat.S_IXUSR
            else "100644"
        )
        return root_fd, leaf_fd, root_identity, identity, mode
    except Exception:
        if leaf_fd >= 0:
            os.close(leaf_fd)
        if root_fd >= 0:
            os.close(root_fd)
        raise


def _posix_read_all(leaf_fd: int) -> bytes:
    size = os.fstat(leaf_fd).st_size
    if size < 0 or size > MAX_FIXTURE_FILE_BYTES:
        raise FixtureError("safe adapter leaf exceeds fixture size bound")
    os.lseek(leaf_fd, 0, os.SEEK_SET)
    chunks = []
    remaining = size
    while remaining:
        chunk = os.read(leaf_fd, min(65536, remaining))
        if not chunk:
            raise FixtureError("safe adapter observed a short file read")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _inspect_posix(root: Path, target: str) -> Dict[str, Any]:
    root_fd, leaf_fd, root_identity, identity, mode = _posix_open(
        root, target, writable=False
    )
    try:
        data = _posix_read_all(leaf_fd)
        if (
            _posix_root_identity(os.fstat(root_fd)) != root_identity
            or _posix_root_identity(os.stat(root, follow_symlinks=False))
            != root_identity
            or _posix_identity(os.fstat(leaf_fd)) != identity
        ):
            raise FixtureError("safe adapter leaf identity changed while read")
        return {
            "bytes": data,
            "root_identity": root_identity,
            "identity": identity,
            "mode": mode,
        }
    finally:
        os.close(leaf_fd)
        os.close(root_fd)


if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    import ntpath

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _INVALID_HANDLE = ctypes.c_void_p(-1).value
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _DELETE = 0x00010000
    _FILE_LIST_DIRECTORY = 0x0001
    _FILE_READ_ATTRIBUTES = 0x0080
    _FILE_WRITE_ATTRIBUTES = 0x0100
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _CREATE_NEW = 1
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_READONLY = 0x00000001
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_BEGIN = 0
    _FILE_RENAME_INFO_CLASS = 3

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("file_attributes", wintypes.DWORD),
            ("creation_time", wintypes.FILETIME),
            ("last_access_time", wintypes.FILETIME),
            ("last_write_time", wintypes.FILETIME),
            ("volume_serial_number", wintypes.DWORD),
            ("file_size_high", wintypes.DWORD),
            ("file_size_low", wintypes.DWORD),
            ("number_of_links", wintypes.DWORD),
            ("file_index_high", wintypes.DWORD),
            ("file_index_low", wintypes.DWORD),
        ]

    class _FileRenameInfo(ctypes.Structure):
        _fields_ = [
            ("replace_if_exists", wintypes.BOOLEAN),
            ("root_directory", wintypes.HANDLE),
            ("file_name_length", wintypes.DWORD),
            ("file_name", wintypes.WCHAR * 1),
        ]

    class _FileDispositionInfo(ctypes.Structure):
        _fields_ = [("delete_file", wintypes.BOOLEAN)]

    class _FileBasicInfo(ctypes.Structure):
        _fields_ = [
            ("creation_time", ctypes.c_longlong),
            ("last_access_time", ctypes.c_longlong),
            ("last_write_time", ctypes.c_longlong),
            ("change_time", ctypes.c_longlong),
            ("file_attributes", wintypes.DWORD),
        ]

    _kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ByHandleFileInformation),
    ]
    _kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
    _kernel32.GetFileSizeEx.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_longlong),
    ]
    _kernel32.GetFileSizeEx.restype = wintypes.BOOL
    _kernel32.ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _kernel32.ReadFile.restype = wintypes.BOOL
    _kernel32.WriteFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _kernel32.WriteFile.restype = wintypes.BOOL
    _kernel32.SetFilePointerEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    ]
    _kernel32.SetFilePointerEx.restype = wintypes.BOOL
    _kernel32.SetEndOfFile.argtypes = [wintypes.HANDLE]
    _kernel32.SetEndOfFile.restype = wintypes.BOOL
    _kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _kernel32.FlushFileBuffers.restype = wintypes.BOOL
    _kernel32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _kernel32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _kernel32.SetFileInformationByHandle.restype = wintypes.BOOL

    def _win_error(label: str) -> FixtureError:
        return FixtureError(
            f"{label}: {ctypes.WinError(ctypes.get_last_error())}"
        )

    def _win_close(handle: int) -> None:
        if handle not in {0, None, _INVALID_HANDLE}:
            _kernel32.CloseHandle(handle)

    def _win_open_path(
        path: Path,
        *,
        access: int,
        share: int,
        directory: bool,
    ) -> int:
        flags = _FILE_FLAG_OPEN_REPARSE_POINT
        if directory:
            flags |= _FILE_FLAG_BACKUP_SEMANTICS
        handle = _kernel32.CreateFileW(
            str(path),
            access,
            share,
            None,
            _OPEN_EXISTING,
            flags,
            None,
        )
        if handle == _INVALID_HANDLE:
            raise _win_error("safe adapter CreateFileW failed")
        return handle

    def _win_information(handle: int) -> _ByHandleFileInformation:
        information = _ByHandleFileInformation()
        if not _kernel32.GetFileInformationByHandle(
            handle, ctypes.byref(information)
        ):
            raise _win_error("safe adapter file information failed")
        return information

    def _win_identity(
        information: _ByHandleFileInformation,
    ) -> Dict[str, int]:
        return {
            "volume": int(information.volume_serial_number),
            "index_high": int(information.file_index_high),
            "index_low": int(information.file_index_low),
            "links": int(information.number_of_links),
        }

    def _win_root_identity(
        information: _ByHandleFileInformation,
    ) -> Dict[str, int]:
        return {
            "volume": int(information.volume_serial_number),
            "index_high": int(information.file_index_high),
            "index_low": int(information.file_index_low),
        }

    def _win_final_path(handle: int) -> str:
        size = _kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0)
        if not size:
            raise _win_error("safe adapter final-path sizing failed")
        buffer = ctypes.create_unicode_buffer(size + 1)
        written = _kernel32.GetFinalPathNameByHandleW(
            handle, buffer, len(buffer), 0
        )
        if not written or written >= len(buffer):
            raise _win_error("safe adapter final-path read failed")
        return ntpath.normcase(ntpath.normpath(buffer.value))

    def _win_seek_start(handle: int) -> None:
        if not _kernel32.SetFilePointerEx(
            handle, ctypes.c_longlong(0), None, _FILE_BEGIN
        ):
            raise _win_error("safe adapter seek failed")

    def _win_read_all(handle: int) -> bytes:
        size = ctypes.c_longlong()
        if not _kernel32.GetFileSizeEx(handle, ctypes.byref(size)):
            raise _win_error("safe adapter size read failed")
        if size.value < 0 or size.value > MAX_FIXTURE_FILE_BYTES:
            raise FixtureError("safe adapter leaf exceeds fixture size bound")
        _win_seek_start(handle)
        chunks = []
        remaining = size.value
        while remaining:
            wanted = min(65536, remaining)
            buffer = ctypes.create_string_buffer(wanted)
            count = wintypes.DWORD()
            if not _kernel32.ReadFile(
                handle,
                buffer,
                wanted,
                ctypes.byref(count),
                None,
            ):
                raise _win_error("safe adapter ReadFile failed")
            if count.value <= 0:
                raise FixtureError("safe adapter observed a short file read")
            chunks.append(buffer.raw[: count.value])
            remaining -= count.value
        return b"".join(chunks)

    def _win_clear_readonly(handle: int) -> None:
        information = _win_information(handle)
        if not (
            information.file_attributes & _FILE_ATTRIBUTE_READONLY
        ):
            return
        attributes = (
            information.file_attributes & ~_FILE_ATTRIBUTE_READONLY
        )
        if not attributes:
            attributes = _FILE_ATTRIBUTE_NORMAL
        basic = _FileBasicInfo()
        basic.file_attributes = attributes
        if not _kernel32.SetFileInformationByHandle(
            handle,
            0,
            ctypes.byref(basic),
            ctypes.sizeof(basic),
        ):
            raise _win_error(
                "cannot clear readonly attribute through retained handle"
            )

    def _win_open(
        root: Path,
        target: str,
        *,
        writable: bool,
    ) -> Tuple[int, int, Dict[str, int], Dict[str, int], str]:
        target = _root_child_name(target)
        root_handle = 0
        leaf_handle = 0
        try:
            root_handle = _win_open_path(
                root,
                access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
                share=_FILE_SHARE_READ | _FILE_SHARE_WRITE,
                directory=True,
            )
            root_info = _win_information(root_handle)
            if (
                not root_info.file_attributes & _FILE_ATTRIBUTE_DIRECTORY
                or root_info.file_attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise FixtureError(
                    "safe adapter root must be a non-reparse directory"
                )
            leaf_handle = _win_open_path(
                root / target,
                access=(
                    _GENERIC_READ
                    | (_GENERIC_WRITE if writable else 0)
                    | _FILE_READ_ATTRIBUTES
                ),
                share=_FILE_SHARE_READ,
                directory=False,
            )
            leaf_info = _win_information(leaf_handle)
            if (
                leaf_info.file_attributes & _FILE_ATTRIBUTE_DIRECTORY
                or leaf_info.file_attributes
                & _FILE_ATTRIBUTE_REPARSE_POINT
                or leaf_info.number_of_links != 1
            ):
                raise FixtureError(
                    "safe adapter leaf must be a single-link, "
                    "non-reparse regular file"
                )
            root_final = _win_final_path(root_handle)
            leaf_final = _win_final_path(leaf_handle)
            if (
                ntpath.dirname(leaf_final) != root_final
                or ntpath.basename(leaf_final).casefold()
                != target.casefold()
            ):
                raise FixtureError(
                    "safe adapter leaf is not the retained root child"
                )
            return (
                root_handle,
                leaf_handle,
                _win_root_identity(root_info),
                _win_identity(leaf_info),
                "100644",
            )
        except Exception:
            _win_close(leaf_handle)
            _win_close(root_handle)
            raise

    def _win_verify_pair(
        root_handle: int,
        leaf_handle: int,
        target: str,
        *,
        root_identity: Mapping[str, Any],
        leaf_identity: Mapping[str, Any],
    ) -> None:
        root_info = _win_information(root_handle)
        leaf_info = _win_information(leaf_handle)
        root_final = _win_final_path(root_handle)
        leaf_final = _win_final_path(leaf_handle)
        if (
            not root_info.file_attributes & _FILE_ATTRIBUTE_DIRECTORY
            or root_info.file_attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            or leaf_info.file_attributes & _FILE_ATTRIBUTE_DIRECTORY
            or leaf_info.file_attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            or leaf_info.number_of_links != 1
            or _win_root_identity(root_info) != root_identity
            or _win_identity(leaf_info) != leaf_identity
            or ntpath.dirname(leaf_final) != root_final
            or ntpath.basename(leaf_final).casefold() != target.casefold()
        ):
            raise FixtureError(
                "safe adapter retained root/leaf pair changed"
            )

    def _inspect_windows(root: Path, target: str) -> Dict[str, Any]:
        root_handle, leaf_handle, root_identity, identity, mode = _win_open(
            root, target, writable=False
        )
        try:
            data = _win_read_all(leaf_handle)
            _win_verify_pair(
                root_handle,
                leaf_handle,
                target,
                root_identity=root_identity,
                leaf_identity=identity,
            )
            return {
                "bytes": data,
                "root_identity": root_identity,
                "identity": identity,
                "mode": mode,
            }
        finally:
            _win_close(leaf_handle)
            _win_close(root_handle)

    def _replace_windows(
        root: Path,
        target: str,
        *,
        expected_root_identity: Mapping[str, Any],
        expected_identity: Mapping[str, Any],
        expected_mode: str,
        expected_bytes: bytes,
        injected_bytes: bytes,
        injected_mode: str,
    ) -> Dict[str, Any]:
        root_handle, leaf_handle, root_identity, identity, mode = _win_open(
            root, target, writable=True
        )
        try:
            if (
                expected_mode != "100644"
                or injected_mode != "100644"
                or root_identity != expected_root_identity
                or identity != expected_identity
                or mode != expected_mode
                or _win_read_all(leaf_handle) != expected_bytes
            ):
                raise FixtureError(
                    "safe adapter leaf identity/mode/preimage mismatch"
                )
            _win_verify_pair(
                root_handle,
                leaf_handle,
                target,
                root_identity=root_identity,
                leaf_identity=identity,
            )
            _win_seek_start(leaf_handle)
            written = 0
            while written < len(injected_bytes):
                chunk = injected_bytes[written : written + 65536]
                count = wintypes.DWORD()
                buffer = ctypes.create_string_buffer(chunk)
                if not _kernel32.WriteFile(
                    leaf_handle,
                    buffer,
                    len(chunk),
                    ctypes.byref(count),
                    None,
                ):
                    raise _win_error("safe adapter WriteFile failed")
                if count.value <= 0:
                    raise FixtureError(
                        "safe adapter could not write exact bytes"
                    )
                written += count.value
            if not _kernel32.SetEndOfFile(leaf_handle):
                raise _win_error("safe adapter truncate failed")
            if not _kernel32.FlushFileBuffers(leaf_handle):
                raise _win_error("safe adapter flush failed")
            _win_verify_pair(
                root_handle,
                leaf_handle,
                target,
                root_identity=root_identity,
                leaf_identity=identity,
            )
            if _win_read_all(leaf_handle) != injected_bytes:
                raise FixtureError(
                    "safe adapter leaf post-write identity/bytes mismatch"
                )
            return {
                "bytes": injected_bytes,
                "root_identity": root_identity,
                "identity": identity,
                "mode": injected_mode,
            }
        finally:
            _win_close(leaf_handle)
            _win_close(root_handle)


def inspect_root_child(root: Path, target: str) -> Dict[str, Any]:
    """Read one root-child regular file through retained no-follow handles."""

    root = Path(root)
    if os.name == "nt":
        return _inspect_windows(root, target)
    return _inspect_posix(root, target)


def root_child_capability() -> Dict[str, Any]:
    """Report the closed platform boundary for retained root-child access."""

    windows = os.name == "nt"
    return {
        "disposition": "executable" if windows else "declarative-only",
        "mode-change": False,
        "mutation-bound-name-to-leaf": windows,
        "platform": "windows" if windows else "posix",
        "retained-authority-read": True,
        "same-mode-root-child-mutation": windows,
    }


def replace_root_child(
    root: Path,
    target: str,
    *,
    expected_root_identity: Mapping[str, Any],
    expected_identity: Mapping[str, Any],
    expected_mode: str,
    expected_bytes: bytes,
    injected_bytes: bytes,
    injected_mode: str,
) -> Dict[str, Any]:
    """Replace one root-child file only with mutation-bound name authority."""

    capability = root_child_capability()
    if not capability["same-mode-root-child-mutation"]:
        raise FixtureError(
            "safe adapter root-child mutation is declarative-only on POSIX: "
            "retained leaf identity cannot atomically bind the current name "
            "to the mutation"
        )
    if injected_mode not in {"100644", "100755"}:
        raise FixtureError("safe adapter injected mode is invalid")
    return _replace_windows(
        Path(root),
        target,
        expected_root_identity=expected_root_identity,
        expected_identity=expected_identity,
        expected_mode=expected_mode,
        expected_bytes=expected_bytes,
        injected_bytes=injected_bytes,
        injected_mode=injected_mode,
    )


class RetainedRootDirectory:
    """Retain one directory while checking and publishing bound child files."""

    def __init__(self, root: Path) -> None:
        self.root = Path(os.path.abspath(root))
        self.handle: Optional[int] = None
        if os.name == "nt":
            self.handle = _win_open_path(
                self.root,
                access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
                share=_FILE_SHARE_READ | _FILE_SHARE_WRITE,
                directory=True,
            )
            information = _win_information(self.handle)
            if (
                not information.file_attributes
                & _FILE_ATTRIBUTE_DIRECTORY
                or information.file_attributes
                & _FILE_ATTRIBUTE_REPARSE_POINT
            ):
                self.close()
                raise FixtureError(
                    "retained store root must be a non-reparse directory"
                )
            self.identity = _win_root_identity(information)
            self._final_path = _win_final_path(self.handle)
            return
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        directory = getattr(os, "O_DIRECTORY", 0)
        if (
            not nofollow
            or not directory
            or os.open not in getattr(os, "supports_dir_fd", set())
            or os.stat not in getattr(os, "supports_dir_fd", set())
            or os.stat
            not in getattr(os, "supports_follow_symlinks", set())
        ):
            raise FixtureError(
                "retained store lacks POSIX no-follow/dir-fd capability"
            )
        self.handle = os.open(
            self.root, os.O_RDONLY | directory | nofollow
        )
        information = os.fstat(self.handle)
        if not stat.S_ISDIR(information.st_mode):
            self.close()
            raise FixtureError("retained store root is not a directory")
        self.identity = _posix_root_identity(information)
        self.verify()

    def __enter__(self) -> "RetainedRootDirectory":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def verify(self) -> None:
        if self.handle is None:
            raise FixtureError("retained store root is closed")
        if os.name == "nt":
            information = _win_information(self.handle)
            if (
                _win_root_identity(information) != self.identity
                or information.file_attributes
                & _FILE_ATTRIBUTE_REPARSE_POINT
                or not information.file_attributes
                & _FILE_ATTRIBUTE_DIRECTORY
                or _win_final_path(self.handle) != self._final_path
            ):
                raise FixtureError("retained store root identity changed")
            return
        retained = os.fstat(self.handle)
        visible = os.stat(self.root, follow_symlinks=False)
        if (
            _posix_root_identity(retained) != self.identity
            or _posix_root_identity(visible) != self.identity
            or not stat.S_ISDIR(retained.st_mode)
            or not stat.S_ISDIR(visible.st_mode)
            or stat.S_ISLNK(visible.st_mode)
        ):
            raise FixtureError("retained store root identity changed")

    @staticmethod
    def _evidence(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "identity": {
                key: str(value)
                for key, value in sorted(
                    snapshot["identity"].items()
                )
            },
            "mode": snapshot["mode"],
            "nlink": str(snapshot["nlink"]),
            "parent_identity": {
                key: str(value)
                for key, value in sorted(
                    snapshot["root_identity"].items()
                )
            },
            "reparse": bool(snapshot["reparse"]),
        }

    def exists(self, target: str) -> bool:
        target = _root_child_name(target)
        self.verify()
        if os.name == "nt":
            handle = _kernel32.CreateFileW(
                str(self.root / target),
                _FILE_READ_ATTRIBUTES,
                _FILE_SHARE_READ | _FILE_SHARE_WRITE,
                None,
                _OPEN_EXISTING,
                _FILE_FLAG_OPEN_REPARSE_POINT
                | _FILE_FLAG_BACKUP_SEMANTICS,
                None,
            )
            if handle == _INVALID_HANDLE:
                error = ctypes.get_last_error()
                if error in {2, 3}:
                    return False
                raise _win_error("retained store existence check failed")
            _win_close(handle)
            self.verify()
            return True
        try:
            os.stat(
                target,
                dir_fd=self.handle,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return False
        self.verify()
        return True

    def _posix_snapshot(self, leaf_fd: int, target: str) -> Dict[str, Any]:
        assert self.handle is not None
        before = os.fstat(leaf_fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
        ):
            raise FixtureError(
                "retained store child must be a single-link regular file"
            )
        first = _posix_read_all(leaf_fd)
        middle = os.fstat(leaf_fd)
        second = _posix_read_all(leaf_fd)
        after = os.fstat(leaf_fd)
        visible = os.stat(
            target,
            dir_fd=self.handle,
            follow_symlinks=False,
        )
        stable = lambda value: (
            value.st_dev,
            value.st_ino,
            stat.S_IFMT(value.st_mode),
            value.st_size,
            value.st_nlink,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )
        if (
            stable(before) != stable(middle)
            or stable(before) != stable(after)
            or stable(before) != stable(visible)
            or first != second
        ):
            raise FixtureError("retained store child drifted while read")
        self.verify()
        return {
            "bytes": first,
            "identity": _posix_identity(after),
            "mode": (
                "100755"
                if after.st_mode & stat.S_IXUSR
                else "100644"
            ),
            "nlink": int(after.st_nlink),
            "raw_sha256": hashlib.sha256(first).hexdigest(),
            "reparse": False,
            "root_identity": dict(self.identity),
        }

    def _win_snapshot(self, leaf_handle: int, target: str) -> Dict[str, Any]:
        information = _win_information(leaf_handle)
        if (
            information.file_attributes & _FILE_ATTRIBUTE_DIRECTORY
            or information.file_attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            or information.number_of_links != 1
            or ntpath.dirname(_win_final_path(leaf_handle))
            != self._final_path
            or ntpath.basename(_win_final_path(leaf_handle)).casefold()
            != target.casefold()
        ):
            raise FixtureError(
                "retained store child is unsafe or escaped its parent"
            )
        data = _win_read_all(leaf_handle)
        final = _win_information(leaf_handle)
        if _win_identity(final) != _win_identity(information):
            raise FixtureError("retained store child identity drifted")
        self.verify()
        return {
            "bytes": data,
            "identity": _win_identity(final),
            "mode": "100644",
            "nlink": int(final.number_of_links),
            "raw_sha256": hashlib.sha256(data).hexdigest(),
            "reparse": False,
            "root_identity": dict(self.identity),
        }

    def read(self, target: str) -> Dict[str, Any]:
        target = _root_child_name(target)
        self.verify()
        if os.name == "nt":
            leaf_handle = _win_open_path(
                self.root / target,
                access=_GENERIC_READ | _FILE_READ_ATTRIBUTES,
                share=_FILE_SHARE_READ,
                directory=False,
            )
            try:
                return self._win_snapshot(leaf_handle, target)
            finally:
                _win_close(leaf_handle)
        assert self.handle is not None
        leaf_fd = os.open(
            target,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=self.handle,
        )
        try:
            return self._posix_snapshot(leaf_fd, target)
        finally:
            os.close(leaf_fd)

    def create_bound(
        self,
        target: str,
        build: Callable[[Mapping[str, Any]], bytes],
    ) -> Dict[str, Any]:
        target = _root_child_name(target)
        self.verify()
        if os.name == "nt":
            leaf_handle = _kernel32.CreateFileW(
                str(self.root / target),
                _GENERIC_READ | _GENERIC_WRITE | _FILE_READ_ATTRIBUTES,
                _FILE_SHARE_READ,
                None,
                _CREATE_NEW,
                _FILE_FLAG_OPEN_REPARSE_POINT,
                None,
            )
            if leaf_handle == _INVALID_HANDLE:
                raise _win_error("retained store exclusive create failed")
            try:
                empty = self._win_snapshot(leaf_handle, target)
                data = build(self._evidence(empty))
                _win_seek_start(leaf_handle)
                written = 0
                while written < len(data):
                    chunk = data[written : written + 65536]
                    count = wintypes.DWORD()
                    buffer = ctypes.create_string_buffer(chunk)
                    if not _kernel32.WriteFile(
                        leaf_handle,
                        buffer,
                        len(chunk),
                        ctypes.byref(count),
                        None,
                    ):
                        raise _win_error(
                            "retained store child write failed"
                        )
                    if count.value <= 0:
                        raise FixtureError(
                            "retained store child write was short"
                        )
                    written += count.value
                if not _kernel32.SetEndOfFile(leaf_handle):
                    raise _win_error(
                        "retained store child truncate failed"
                    )
                if not _kernel32.FlushFileBuffers(leaf_handle):
                    raise _win_error(
                        "retained store child flush failed"
                    )
                snapshot = self._win_snapshot(leaf_handle, target)
                if snapshot["bytes"] != data:
                    raise FixtureError(
                        "retained store child postwrite mismatch"
                    )
                return snapshot
            finally:
                _win_close(leaf_handle)
        assert self.handle is not None
        leaf_fd = os.open(
            target,
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=self.handle,
        )
        try:
            empty = self._posix_snapshot(leaf_fd, target)
            data = build(self._evidence(empty))
            os.lseek(leaf_fd, 0, os.SEEK_SET)
            written = 0
            while written < len(data):
                count = os.write(leaf_fd, data[written:])
                if count <= 0:
                    raise FixtureError(
                        "retained store child write was short"
                    )
                written += count
            os.ftruncate(leaf_fd, len(data))
            os.fsync(leaf_fd)
            snapshot = self._posix_snapshot(leaf_fd, target)
            if snapshot["bytes"] != data:
                raise FixtureError(
                    "retained store child postwrite mismatch"
                )
            return snapshot
        finally:
            os.close(leaf_fd)

    def create(self, target: str, data: bytes) -> Dict[str, Any]:
        return self.create_bound(target, lambda _: data)

    def unlink(
        self,
        target: str,
        *,
        expected: Mapping[str, Any],
    ) -> None:
        target = _root_child_name(target)
        observed = self.read(target)
        for field in (
            "identity",
            "nlink",
            "raw_sha256",
            "reparse",
            "root_identity",
        ):
            if observed[field] != expected[field]:
                raise FixtureError(
                    "retained store refused to unlink a replaced child"
                )
        if os.name == "nt":
            os.unlink(self.root / target)
        else:
            assert self.handle is not None
            if os.unlink not in getattr(os, "supports_dir_fd", set()):
                raise FixtureError(
                    "retained store lacks relative unlink capability"
                )
            os.unlink(target, dir_fd=self.handle)
        self.verify()

    def close(self) -> None:
        if self.handle is None:
            return
        if os.name == "nt":
            _win_close(self.handle)
        else:
            os.close(self.handle)
        self.handle = None


def windows_root_quarantine_capability() -> Dict[str, Any]:
    """Describe the fixture-only exact-root quarantine primitive."""

    return {
        "contract": "windows-root-handle-quarantine/v1",
        "available": os.name == "nt",
        "platform": os.name,
        "rename_primitive": (
            "SetFileInformationByHandle/FileRenameInfo"
            if os.name == "nt"
            else None
        ),
        "root_handle_delete_access": os.name == "nt",
        "root_handle_share_delete": False,
        "parent_handle_retained": os.name == "nt",
        "root_handle_retained_through_cleanup": os.name == "nt",
        "root_disposition_primitive": (
            "SetFileInformationByHandle/FileDispositionInfo"
            if os.name == "nt"
            else None
        ),
        "descendant_handles_retained": os.name == "nt",
        "descendant_handle_delete_access": os.name == "nt",
        "descendant_handle_share_delete": False,
        "descendant_disposition_primitive": (
            "SetFileInformationByHandle/FileDispositionInfo"
            if os.name == "nt"
            else None
        ),
        "reparse_points_admitted": False,
    }


class WindowsRootQuarantinedError(FixtureError):
    """Report a handle rename whose postcondition could not be closed."""

    def __init__(
        self,
        message: str,
        *,
        tombstone: Path,
        root_identity: Mapping[str, Any],
    ) -> None:
        super().__init__(message)
        self.tombstone = Path(tombstone)
        self.root_identity = dict(root_identity)


class WindowsRootQuarantine:
    """Retain the exact parent/root handles after an atomic quarantine."""

    def __init__(
        self,
        *,
        parent_handle: int,
        root_handle: int,
        evidence: Mapping[str, Any],
        parent_final: str,
        tombstone_final: str,
    ) -> None:
        self.parent_handle = parent_handle
        self.root_handle = root_handle
        self.evidence = dict(evidence)
        self.parent_final = parent_final
        self.tombstone_final = tombstone_final
        self.disposed = False

    def __enter__(self) -> "WindowsRootQuarantine":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __getitem__(self, key: str) -> Any:
        return self.evidence[key]

    def verify(self) -> None:
        if os.name != "nt" or not self.root_handle:
            raise FixtureError("Windows root quarantine handle is closed")
        root_information = _win_information(self.root_handle)
        parent_information = _win_information(self.parent_handle)
        if (
            _win_root_identity(root_information)
            != self.evidence["root_identity"]
            or root_information.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
            or not root_information.file_attributes
            & _FILE_ATTRIBUTE_DIRECTORY
            or _win_final_path(self.root_handle)
            != self.tombstone_final
            or _win_root_identity(parent_information)
            != self.evidence["parent_identity"]
            or parent_information.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
            or _win_final_path(self.parent_handle) != self.parent_final
        ):
            raise FixtureError(
                "Windows root quarantine retained identity changed"
            )

    def dispose_empty_root(self) -> None:
        """Delete the already-empty tombstone through its retained handle."""

        self.verify()
        _win_clear_readonly(self.root_handle)
        disposition = _FileDispositionInfo()
        disposition.delete_file = True
        if not _kernel32.SetFileInformationByHandle(
            self.root_handle,
            4,
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise _win_error(
                "exact tombstone handle disposition failed"
            )
        _win_close(self.root_handle)
        self.root_handle = 0
        self.disposed = True
        tombstone = Path(self.evidence["tombstone"])
        if os.path.lexists(tombstone):
            raise FixtureError(
                "exact tombstone remains after handle disposition"
            )
        parent_information = _win_information(self.parent_handle)
        if (
            _win_root_identity(parent_information)
            != self.evidence["parent_identity"]
            or parent_information.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
            or _win_final_path(self.parent_handle) != self.parent_final
        ):
            raise FixtureError(
                "quarantine parent changed during root disposition"
            )

    def close(self) -> None:
        if os.name == "nt":
            _win_close(self.root_handle)
            _win_close(self.parent_handle)
        self.root_handle = 0
        self.parent_handle = 0


class WindowsPinnedTreePartialError(FixtureError):
    """Report irreversible progress during handle-bound tree disposal."""

    def __init__(
        self,
        message: str,
        *,
        removed: Sequence[str],
    ) -> None:
        super().__init__(message)
        self.removed = list(removed)


class WindowsPinnedTree:
    """Hold DELETE/no-share-delete handles for every tombstone descendant."""

    def __init__(
        self,
        *,
        quarantine: WindowsRootQuarantine,
        expected: Mapping[str, str],
        records: Mapping[str, Mapping[str, Any]],
    ) -> None:
        self.quarantine = quarantine
        self.expected = dict(expected)
        self.records = {
            relative: dict(record)
            for relative, record in records.items()
        }

    def _direct_children(self) -> Dict[str, list[str]]:
        result: Dict[str, list[str]] = {}
        for relative in self.expected:
            if not relative:
                continue
            parent, _, name = relative.rpartition("/")
            result.setdefault(parent, []).append(name)
        for names in result.values():
            names.sort()
        return result

    def _path(self, relative: str) -> Path:
        root = Path(self.quarantine["tombstone"])
        if not relative:
            return root
        return root.joinpath(*PurePosixPath(relative).parts)

    def _expected_final(self, relative: str) -> str:
        if not relative:
            return self.quarantine.tombstone_final
        return ntpath.normcase(
            ntpath.normpath(
                ntpath.join(
                    self.quarantine.tombstone_final,
                    *PurePosixPath(relative).parts,
                )
            )
        )

    @staticmethod
    def _record_identity(
        information: Any,
    ) -> Dict[str, int]:
        return {
            **_win_identity(information),
            "attributes": int(information.file_attributes),
        }

    def _verify_record(self, relative: str) -> None:
        record = self.records[relative]
        handle = int(record["handle"])
        if not handle:
            raise FixtureError(
                f"pinned tombstone handle is closed: {relative}"
            )
        information = _win_information(handle)
        directory = bool(
            information.file_attributes & _FILE_ATTRIBUTE_DIRECTORY
        )
        if (
            self._record_identity(information) != record["identity"]
            or information.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
            or information.number_of_links != 1
            or directory != (self.expected[relative] == "directory")
            or _win_final_path(handle) != self._expected_final(relative)
        ):
            raise FixtureError(
                f"pinned tombstone identity changed: {relative}"
            )

    def revalidate(self) -> None:
        """Re-enumerate the exact namespace and bind each name to its handle."""

        self.quarantine.verify()
        direct = self._direct_children()
        for relative, kind in sorted(self.expected.items()):
            if kind != "directory":
                continue
            path = self._path(relative)
            try:
                with os.scandir(path) as iterator:
                    names = sorted(item.name for item in iterator)
            except OSError as error:
                raise FixtureError(
                    "cannot re-enumerate pinned tombstone directory "
                    f"{relative or '.'}: {error}"
                ) from error
            if names != direct.get(relative, []):
                raise FixtureError(
                    "pinned tombstone exact child set changed: "
                    f"{relative or '.'}"
                )
        for relative in sorted(self.records):
            self._verify_record(relative)
            record = self.records[relative]
            path = self._path(relative)
            probe = 0
            try:
                probe = _win_open_path(
                    path,
                    access=_FILE_READ_ATTRIBUTES,
                    share=(
                        _FILE_SHARE_READ
                        | _FILE_SHARE_WRITE
                        | _FILE_SHARE_DELETE
                    ),
                    directory=(
                        self.expected[relative] == "directory"
                    ),
                )
                information = _win_information(probe)
                if (
                    self._record_identity(information)
                    != record["identity"]
                    or _win_final_path(probe)
                    != self._expected_final(relative)
                ):
                    raise FixtureError(
                        "pinned tombstone name no longer maps to retained "
                        f"identity: {relative}"
                    )
            finally:
                _win_close(probe)
        self.quarantine.verify()

    @staticmethod
    def _clear_readonly(handle: int) -> None:
        _win_clear_readonly(handle)

    @staticmethod
    def _dispose_handle(handle: int) -> None:
        disposition = _FileDispositionInfo()
        disposition.delete_file = True
        if not _kernel32.SetFileInformationByHandle(
            handle,
            4,
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise _win_error(
                "pinned tombstone handle disposition failed"
            )

    def dispose(
        self,
        *,
        after_disposition: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """Delete descendants postorder, then dispose the retained root."""

        self.revalidate()
        _win_clear_readonly(self.quarantine.root_handle)
        self.quarantine.verify()
        removed: list[str] = []
        mutation_started = False
        ordered = sorted(
            self.records,
            key=lambda relative: (
                -len(PurePosixPath(relative).parts),
                relative,
            ),
        )
        try:
            for relative in ordered:
                self._verify_record(relative)
                record = self.records[relative]
                handle = int(record["handle"])
                self._clear_readonly(handle)
                self._dispose_handle(handle)
                mutation_started = True
                _win_close(handle)
                record["handle"] = 0
                removed.append(relative)
                if os.path.lexists(self._path(relative)):
                    raise FixtureError(
                        "pinned tombstone name remains after disposition: "
                        f"{relative}"
                    )
                if after_disposition is not None:
                    after_disposition(relative, len(removed))
            self.quarantine.verify()
            self.quarantine.dispose_empty_root()
            mutation_started = True
            removed.append("")
            return {
                "removed_entries": len(removed),
                "descendant_entries": len(self.records),
                "handle_bound": True,
            }
        except Exception as error:
            self.close()
            if mutation_started:
                raise WindowsPinnedTreePartialError(
                    str(error), removed=removed
                ) from error
            raise

    def close(self) -> None:
        for record in self.records.values():
            handle = int(record.get("handle", 0))
            _win_close(handle)
            record["handle"] = 0


def pin_quarantined_tree_windows(
    quarantine: WindowsRootQuarantine,
    expected_entries: Mapping[str, str],
) -> WindowsPinnedTree:
    """Pin every exact tombstone descendant without delete sharing."""

    if os.name != "nt":
        raise FixtureError(
            "pinned tombstone disposal requires Windows"
        )
    if (
        not isinstance(expected_entries, Mapping)
        or expected_entries.get("") != "directory"
        or any(
            not isinstance(relative, str)
            or not isinstance(kind, str)
            or kind not in {"file", "directory"}
            or (
                relative
                and (
                    PurePosixPath(relative).is_absolute()
                    or "\\" in relative
                    or any(
                        part in {"", ".", ".."}
                        for part in PurePosixPath(relative).parts
                    )
                )
            )
            for relative, kind in expected_entries.items()
        )
    ):
        raise FixtureError(
            "pinned tombstone expected-entry map is invalid"
        )
    expected = dict(expected_entries)
    direct: Dict[str, list[str]] = {}
    for relative in expected:
        if not relative:
            continue
        parent, _, name = relative.rpartition("/")
        if parent not in expected or expected[parent] != "directory":
            raise FixtureError(
                f"pinned tombstone parent is not declared: {relative}"
            )
        direct.setdefault(parent, []).append(name)
    for names in direct.values():
        names.sort()

    root = Path(quarantine["tombstone"])
    records: Dict[str, Dict[str, Any]] = {}

    def expected_final(relative: str) -> str:
        return ntpath.normcase(
            ntpath.normpath(
                ntpath.join(
                    quarantine.tombstone_final,
                    *PurePosixPath(relative).parts,
                )
            )
        )

    def visit(relative: str) -> None:
        directory = (
            root
            if not relative
            else root.joinpath(*PurePosixPath(relative).parts)
        )
        try:
            with os.scandir(directory) as iterator:
                names = sorted(item.name for item in iterator)
        except OSError as error:
            raise FixtureError(
                f"cannot enumerate pinned tombstone "
                f"{relative or '.'}: {error}"
            ) from error
        if names != direct.get(relative, []):
            raise FixtureError(
                "pinned tombstone initial child set differs from "
                f"validated snapshot: {relative or '.'}"
            )
        for name in names:
            child_relative = (
                name if not relative else f"{relative}/{name}"
            )
            kind = expected[child_relative]
            path = root.joinpath(
                *PurePosixPath(child_relative).parts
            )
            handle = 0
            try:
                handle = _win_open_path(
                    path,
                    access=(
                        _DELETE
                        | _FILE_READ_ATTRIBUTES
                        | _FILE_WRITE_ATTRIBUTES
                        | (
                            _FILE_LIST_DIRECTORY
                            if kind == "directory"
                            else 0
                        )
                    ),
                    share=_FILE_SHARE_READ | _FILE_SHARE_WRITE,
                    directory=(kind == "directory"),
                )
                information = _win_information(handle)
                is_directory = bool(
                    information.file_attributes
                    & _FILE_ATTRIBUTE_DIRECTORY
                )
                if (
                    information.file_attributes
                    & _FILE_ATTRIBUTE_REPARSE_POINT
                    or information.number_of_links != 1
                    or is_directory != (kind == "directory")
                    or _win_final_path(handle)
                    != expected_final(child_relative)
                ):
                    raise FixtureError(
                        "pinned tombstone entry is unsafe or escaped: "
                        f"{child_relative}"
                    )
                records[child_relative] = {
                    "handle": handle,
                    "identity": WindowsPinnedTree._record_identity(
                        information
                    ),
                }
                handle = 0
                if kind == "directory":
                    visit(child_relative)
            finally:
                _win_close(handle)

    try:
        quarantine.verify()
        visit("")
        pinned = WindowsPinnedTree(
            quarantine=quarantine,
            expected=expected,
            records=records,
        )
        pinned.revalidate()
        return pinned
    except Exception:
        for record in records.values():
            _win_close(int(record.get("handle", 0)))
        raise


def quarantine_root_child_windows(
    parent: Path,
    child_name: str,
    tombstone_name: str,
    *,
    expected_identity: Mapping[str, Any],
    after_rename: Optional[Callable[[Path, Path], None]] = None,
) -> WindowsRootQuarantine:
    """Rename one retained, non-reparse Windows directory by its handle.

    The parent and child handles deliberately deny delete sharing. The rename
    is issued against the already-verified child handle to an absolute path
    whose final parent is the retained parent handle. No sibling is enumerated.
    """

    if os.name != "nt":
        raise FixtureError(
            "exact stale recovery requires Windows handle quarantine"
        )
    child_name = _root_child_name(child_name)
    tombstone_name = _root_child_name(tombstone_name)
    if child_name.casefold() == tombstone_name.casefold():
        raise FixtureError("quarantine tombstone must differ from source")
    if set(expected_identity) != {
        "volume",
        "index_high",
        "index_low",
    }:
        raise FixtureError("quarantine expected identity fields are invalid")

    parent = Path(os.path.abspath(parent))
    source = parent / child_name
    tombstone = parent / tombstone_name
    parent_handle = 0
    root_handle = 0
    renamed = False
    try:
        parent_handle = _win_open_path(
            parent,
            access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
            share=_FILE_SHARE_READ | _FILE_SHARE_WRITE,
            directory=True,
        )
        parent_information = _win_information(parent_handle)
        if (
            not parent_information.file_attributes
            & _FILE_ATTRIBUTE_DIRECTORY
            or parent_information.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise FixtureError(
                "quarantine parent must be a retained non-reparse directory"
            )
        parent_identity = _win_root_identity(parent_information)
        parent_final = _win_final_path(parent_handle)
        if os.path.lexists(tombstone):
            raise FixtureError("quarantine tombstone already exists")

        root_handle = _win_open_path(
            source,
            access=(
                _DELETE
                | _FILE_LIST_DIRECTORY
                | _FILE_READ_ATTRIBUTES
                | _FILE_WRITE_ATTRIBUTES
            ),
            share=_FILE_SHARE_READ | _FILE_SHARE_WRITE,
            directory=True,
        )
        root_information = _win_information(root_handle)
        root_identity = _win_root_identity(root_information)
        expected_source_final = ntpath.normcase(
            ntpath.normpath(ntpath.join(parent_final, child_name))
        )
        if (
            root_identity != dict(expected_identity)
            or not root_information.file_attributes
            & _FILE_ATTRIBUTE_DIRECTORY
            or root_information.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
            or _win_final_path(root_handle) != expected_source_final
        ):
            raise FixtureError(
                "quarantine source identity/final path is not exact"
            )

        encoded_name = str(tombstone).encode("utf-16-le")
        file_name_offset = _FileRenameInfo.file_name.offset
        buffer_size = ctypes.sizeof(_FileRenameInfo) + len(encoded_name)
        buffer = ctypes.create_string_buffer(buffer_size)
        rename = ctypes.cast(
            buffer, ctypes.POINTER(_FileRenameInfo)
        ).contents
        rename.replace_if_exists = False
        rename.root_directory = None
        rename.file_name_length = len(encoded_name)
        ctypes.memmove(
            ctypes.addressof(buffer) + file_name_offset,
            encoded_name,
            len(encoded_name),
        )
        if not _kernel32.SetFileInformationByHandle(
            root_handle,
            _FILE_RENAME_INFO_CLASS,
            buffer,
            buffer_size,
        ):
            raise _win_error("exact root handle quarantine rename failed")
        renamed = True
        if after_rename is not None:
            after_rename(source, tombstone)

        final_information = _win_information(root_handle)
        expected_tombstone_final = ntpath.normcase(
            ntpath.normpath(ntpath.join(parent_final, tombstone_name))
        )
        if (
            _win_root_identity(final_information) != root_identity
            or final_information.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
            or not final_information.file_attributes
            & _FILE_ATTRIBUTE_DIRECTORY
            or _win_final_path(root_handle) != expected_tombstone_final
            or os.path.lexists(source)
        ):
            raise FixtureError(
                "exact root handle quarantine postcondition failed"
            )
        retained_parent = _win_information(parent_handle)
        if (
            _win_root_identity(retained_parent) != parent_identity
            or retained_parent.file_attributes
            & _FILE_ATTRIBUTE_REPARSE_POINT
            or _win_final_path(parent_handle) != parent_final
        ):
            raise FixtureError(
                "quarantine parent identity changed during rename"
            )
        evidence = {
            "contract": "windows-root-handle-quarantine/v1",
            "source": str(source),
            "tombstone": str(tombstone),
            "root_identity": dict(root_identity),
            "parent_identity": dict(parent_identity),
            "source_absent": True,
            "siblings_enumerated": False,
        }
        retained = WindowsRootQuarantine(
            parent_handle=parent_handle,
            root_handle=root_handle,
            evidence=evidence,
            parent_final=parent_final,
            tombstone_final=expected_tombstone_final,
        )
        parent_handle = 0
        root_handle = 0
        return retained
    except Exception as error:
        if renamed:
            raise WindowsRootQuarantinedError(
                "root was quarantined but its exact postcondition could not "
                f"be established; inspect {tombstone}: {error}",
                tombstone=tombstone,
                root_identity=root_identity,
            ) from error
        raise
    finally:
        _win_close(root_handle)
        _win_close(parent_handle)
