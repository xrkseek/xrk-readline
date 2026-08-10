"""Windows 控制台：msvcrt，不安装进程级 readline hook。"""

from __future__ import annotations

import ctypes
import msvcrt
import sys
import time
from typing import Optional

from .keys import Key, KeyEvent

_ENABLE_VT = 0x0004
_vt_ready = False


def _ensure_vt() -> None:
    """开启虚拟终端序列，便于 \\x1b 光标移动。"""
    global _vt_ready
    if _vt_ready:
        return
    try:
        handle = ctypes.windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint()
        if ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ctypes.windll.kernel32.SetConsoleMode(handle, mode.value | _ENABLE_VT)
    except Exception:
        pass
    _vt_ready = True


class WinConsole:
    def __init__(self) -> None:
        _ensure_vt()

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def read_key(self, *, timeout: Optional[float] = None) -> Optional[KeyEvent]:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if msvcrt.kbhit():
                return self._decode(msvcrt.getwch())
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.02)

    def _decode(self, ch: str) -> KeyEvent:
        if ch in ("\r", "\n"):
            return KeyEvent(Key.ENTER)
        if ch in ("\x08", "\x7f"):
            return KeyEvent(Key.BACKSPACE)
        if ch == "\t":
            return KeyEvent(Key.TAB)
        if ch == "\x03":
            return KeyEvent(Key.CTRL_C)
        if ch == "\x04":
            return KeyEvent(Key.CTRL_D)
        # 功能键前缀
        if ch in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            mapping = {
                "H": Key.UP,
                "P": Key.DOWN,
                "K": Key.LEFT,
                "M": Key.RIGHT,
                "G": Key.HOME,
                "O": Key.END,
                "S": Key.DELETE,
            }
            kind = mapping.get(code)
            if kind:
                return KeyEvent(kind)
            return KeyEvent(Key.CHAR, "")
        if ch.isprintable() or ord(ch) > 127:
            return KeyEvent(Key.CHAR, ch)
        return KeyEvent(Key.CHAR, "")
