"""优先使用 C 扩展控制台；无编译产物时回退纯 Python。"""

from __future__ import annotations

import sys
from typing import Optional

from .keys import Key, KeyEvent


def create_console():
    try:
        from . import _native  # type: ignore

        return NativeConsole(_native)
    except ImportError:
        if sys.platform == "win32":
            from .win_console import WinConsole

            return WinConsole()
        from .posix_console import PosixConsole

        return PosixConsole()


def backend_name() -> str:
    try:
        from . import _native  # type: ignore

        return str(_native.backend())
    except ImportError:
        return "pure-python"


class NativeConsole:
    """包装 xrk_readline._native（C）。"""

    def __init__(self, native) -> None:
        self._n = native
        self._raw = 0

    def write(self, text: str) -> None:
        self._n.write(text)

    def flush(self) -> None:
        self._n.flush()

    def enter_raw(self) -> None:
        if self._raw == 0:
            self._n.enter_raw()
        self._raw += 1

    def leave_raw(self) -> None:
        self._raw = max(0, self._raw - 1)
        if self._raw == 0:
            self._n.leave_raw()

    def read_key(self, *, timeout: Optional[float] = None) -> Optional[KeyEvent]:
        ms = 50 if timeout is None else max(0, int(timeout * 1000))
        item = self._n.read_key(ms)
        if item is None:
            return None
        kind, ch = item
        return KeyEvent(kind if kind else Key.CHAR, ch or "")
