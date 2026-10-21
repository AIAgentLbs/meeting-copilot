"""The one way this app makes a folder only the person reads (MEETONTRACK-84).

POSIX: mode 0o700. Windows: no mode. Python 3.13 turns mkdir(mode=0o700) into a protected
owner-only ACL (SYSTEM, Administrators, OWNER RIGHTS). Made from an elevated process, the
folder is owned by BUILTIN\\Administrators, and the same person's normal (non-elevated)
session can no longer open it: [WinError 5] Access is denied on archive\\<meeting>. The
user-profile folders the app writes to are already private to the person, so on Windows a
new folder inherits that ACL instead.

A folder already locked that way is moved aside (nothing is deleted or read) and made
again. The parent folder grants the person delete-child, which yields DELETE on the locked
folder, enough to rename it; os.rename also asks for SYNCHRONIZE, which the lock denies, so
the rename opens the folder with DELETE alone. Only the exact folder asked for is healed,
never its parents.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

WINDOWS = os.name == "nt"


def private_dir(path) -> Path:
    path = Path(path)
    if not WINDOWS:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        return path
    path.mkdir(parents=True, exist_ok=True)
    try:
        with os.scandir(path):
            pass
    except PermissionError:
        aside = path.with_name(f"{path.name}.inaccessible-{time.strftime('%Y%m%d-%H%M%S')}")
        _move_aside(path, aside)
        path.mkdir()
    return path


def _move_aside(source: Path, target: Path) -> None:
    import ctypes
    from ctypes import wintypes

    class UnicodeString(ctypes.Structure):
        _fields_ = [("Length", ctypes.c_ushort), ("MaximumLength", ctypes.c_ushort), ("Buffer", ctypes.c_wchar_p)]

    class ObjectAttributes(ctypes.Structure):
        _fields_ = [("Length", ctypes.c_ulong), ("RootDirectory", wintypes.HANDLE),
                    ("ObjectName", ctypes.POINTER(UnicodeString)), ("Attributes", ctypes.c_ulong),
                    ("SecurityDescriptor", ctypes.c_void_p), ("SecurityQualityOfService", ctypes.c_void_p)]

    class IoStatusBlock(ctypes.Structure):
        _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_void_p)]

    name = "\\??\\" + str(source.absolute())
    new = "\\??\\" + str(target.absolute())

    class RenameInformation(ctypes.Structure):
        _fields_ = [("ReplaceIfExists", ctypes.c_ulong), ("RootDirectory", wintypes.HANDLE),
                    ("FileNameLength", ctypes.c_ulong), ("FileName", ctypes.c_wchar * (len(new) + 1))]

    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtOpenFile.restype = ntdll.NtSetInformationFile.restype = ntdll.NtClose.restype = ctypes.c_long
    text = UnicodeString(len(name) * 2, len(name) * 2 + 2, name)
    attributes = ObjectAttributes(ctypes.sizeof(ObjectAttributes), None, ctypes.pointer(text), 0x40, None, None)
    handle, status = wintypes.HANDLE(), IoStatusBlock()
    # DELETE only; share read/write/delete; FILE_DIRECTORY_FILE. FileRenameInformation = 10.
    code = ntdll.NtOpenFile(ctypes.byref(handle), 0x00010000, ctypes.byref(attributes), ctypes.byref(status), 7, 1)
    if code == 0:
        info = RenameInformation(0, None, len(new) * 2, new)
        code = ntdll.NtSetInformationFile(handle, ctypes.byref(status), ctypes.byref(info), ctypes.sizeof(info), 10)
        ntdll.NtClose(handle)
    if code != 0:
        raise PermissionError(ntdll.RtlNtStatusToDosError(code), f"Cannot move aside {source}", str(source))
