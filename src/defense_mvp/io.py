"""No-replace filesystem helpers for Defense MVP artifacts."""

from __future__ import annotations

import ctypes
import errno
import json
import os
import sys
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> None:
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def rename_noreplace(source: Path, target: Path) -> None:
    """Atomically rename a directory while refusing every existing target."""
    source, target = Path(source), Path(target)
    if not source.exists():
        raise FileNotFoundError(source)
    if os.path.lexists(target):
        raise FileExistsError(f"publish target already exists: {target}")
    if sys.platform == "win32":
        os.rename(source, target)
        return
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise OSError(errno.ENOSYS, "renameat2(RENAME_NOREPLACE) is unavailable")
        renameat2.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(-100, os.fsencode(source), -100, os.fsencode(target), 1)
        if result != 0:
            number = ctypes.get_errno()
            if number in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(f"publish target already exists: {target}")
            raise OSError(number, os.strerror(number), str(target))
        return
    raise OSError(errno.ENOSYS, f"no-replace publish unsupported on {sys.platform}")
