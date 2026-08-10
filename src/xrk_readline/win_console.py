"""Windows 控制台：msvcrt + ANSI 方向键（Windows Terminal）。"""

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
    global _vt_ready
    if _vt_ready:
        return
    try:
        handle = ctypes.windll.kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ctypes.windll.kernel32.SetConsoleMode(handle, mode.value | _ENABLE_VT)
    except Exception:
        pass
    _vt_ready = True


_LEGACY = {
    "H": Key.UP,
    "P": Key.DOWN,
    "K": Key.LEFT,
    "M": Key.RIGHT,
    "G": Key.HOME,
    "O": Key.END,
    "S": Key.DELETE,
}

_CSI = {
    "A": Key.UP,
    "B": Key.DOWN,
    "C": Key.RIGHT,
    "D": Key.LEFT,
    "H": Key.HOME,
    "F": Key.END,
}


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
            time.sleep(0.01)

    def _read_more(self, wait: float = 0.03) -> str:
        end = time.monotonic() + wait
        while time.monotonic() < end:
            if msvcrt.kbhit():
                return msvcrt.getwch()
            time.sleep(0.005)
        return ""

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
        # 传统功能键：0 / 0xE0 前缀
        if ch in ("\x00", "\xe0"):
            code = self._read_more(0.05) or ""
            kind = _LEGACY.get(code)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")
        # Windows Terminal / VT：ESC [ A
        if ch == "\x1b":
            return self._ansi()
        if ch.isprintable() or ord(ch) > 127:
            return KeyEvent(Key.CHAR, ch)
        return KeyEvent(Key.CHAR, "")

    def _ansi(self) -> KeyEvent:
        n1 = self._read_more(0.04)
        if not n1:
            return KeyEvent(Key.CHAR, "")
        if n1 == "[":
            n2 = self._read_more(0.04)
            if not n2:
                return KeyEvent(Key.CHAR, "")
            if n2 in _CSI:
                return KeyEvent(_CSI[n2])
            if n2 == "3" and self._read_more(0.04) == "~":
                return KeyEvent(Key.DELETE)
            return KeyEvent(Key.CHAR, "")
        if n1 == "O":
            n2 = self._read_more(0.04)
            if n2 == "H":
                return KeyEvent(Key.HOME)
            if n2 == "F":
                return KeyEvent(Key.END)
        return KeyEvent(Key.CHAR, "")
