#!/usr/bin/env python
"""Move files/directories to the Windows Recycle Bin via shell32 SHFileOperationW.

Backend for the recycle-bin plugin's `rm` shim. Silent by design: FOF_NOERRORUI
keeps a headless gateway session from ever blocking on a dialog.
Exit codes: 0 all ok, 1 missing/unusable path, 2 SHFileOperation error.
"""
import ctypes
import ctypes.wintypes as wintypes
import os
import sys

FO_DELETE = 3
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def recycle(path: str) -> int:
    """Return 0 on success, else an exit code (1 missing, 2 SHFileOperation error)."""
    if not os.path.lexists(path):
        print(f"rm: cannot remove '{path}': No such file or directory", file=sys.stderr)
        return 1
    # pFrom is a double-NUL-terminated list of source paths.
    op = SHFILEOPSTRUCTW(
        None,
        FO_DELETE,
        os.path.abspath(path) + "\0\0",
        None,
        FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI,
        False,
        None,
        None,
    )
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc != 0 or op.fAnyOperationsAborted:
        print(f"rm: cannot recycle '{path}': SHFileOperation error {rc}", file=sys.stderr)
        return 2
    return 0


def main(argv) -> int:
    rc = 0
    for path in argv:
        rc |= recycle(path)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
