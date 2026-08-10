"""Windows 控制台：msvcrt + ANSI / Ctrl 组合键。"""

from __future__ import annotations

import ctypes
import msvcrt
import sys
import time
from typing import Optional

from .keys import Key, KeyEvent

_ENABLE_VT = 0x0004
_vt_ready = False

_CTRL = {
    "\x01": Key.CTRL_A,
    "\x05": Key.CTRL_E,
    "\x0b": Key.CTRL_K,
    "\x15": Key.CTRL_U,
    "\x17": Key.CTRL_W,
    "\x0c": Key.CTRL_L,
    "\x19": Key.CTRL_Y,
    "\x03": Key.CTRL_C,
    "\x04": Key.CTRL_D,
}

# 传统功能键第二码
_LEGACY = {
    "H": Key.UP,
    "P": Key.DOWN,
    "K": Key.LEFT,
    "M": Key.RIGHT,
    "G": Key.HOME,
    "O": Key.END,
    "S": Key.DELETE,
    "s": Key.WORD_LEFT,   # Ctrl+Left
    "t": Key.WORD_RIGHT,  # Ctrl+Right
}


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


def _csi_kind(seq: str) -> Optional[str]:
    """解析 CSI 终字节序列，如 A / 1;5D / 3~。"""
    if not seq:
        return None
    if seq in ("A",):
        return Key.UP
    if seq in ("B",):
        return Key.DOWN
    if seq in ("C",):
        return Key.RIGHT
    if seq in ("D",):
        return Key.LEFT
    if seq in ("H",):
        return Key.HOME
    if seq in ("F",):
        return Key.END
    if seq.endswith("~"):
        if seq.startswith("3"):
            return Key.DELETE
        return None
    # modifier: 1;5C = Ctrl+Right
    if ";" in seq and seq[-1] in "ABCDHF":
        parts = seq[:-1].split(";")
        mod = parts[-1] if len(parts) > 1 else ""
        final = seq[-1]
        ctrl = mod == "5" or mod.endswith("5")
        if final == "C":
            return Key.WORD_RIGHT if ctrl else Key.RIGHT
        if final == "D":
            return Key.WORD_LEFT if ctrl else Key.LEFT
        if final == "A":
            return Key.UP
        if final == "B":
            return Key.DOWN
        if final == "H":
            return Key.HOME
        if final == "F":
            return Key.END
    return None


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
        ctrl = _CTRL.get(ch)
        if ctrl:
            return KeyEvent(ctrl)
        if ch in ("\x00", "\xe0"):
            code = self._read_more(0.05) or ""
            kind = _LEGACY.get(code)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")
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
            seq = ""
            for _ in range(12):
                c = self._read_more(0.04)
                if not c:
                    break
                seq += c
                if c.isalpha() or c == "~":
                    break
            kind = _csi_kind(seq)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")
        if n1 == "O":
            n2 = self._read_more(0.04)
            if n2 == "H":
                return KeyEvent(Key.HOME)
            if n2 == "F":
                return KeyEvent(Key.END)
        return KeyEvent(Key.CHAR, "")
