"""POSIX 控制台。"""

from __future__ import annotations

import select
import sys
import termios
import tty
from typing import Optional

from .keys import Key, KeyEvent

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


def _csi_kind(seq: str) -> Optional[str]:
    if not seq:
        return None
    simple = {
        "A": Key.UP,
        "B": Key.DOWN,
        "C": Key.RIGHT,
        "D": Key.LEFT,
        "H": Key.HOME,
        "F": Key.END,
        "3~": Key.DELETE,
    }
    if seq in simple:
        return simple[seq]
    if seq.endswith("~") and seq.startswith("3"):
        return Key.DELETE
    if ";" in seq and seq[-1] in "ABCDHF":
        parts = seq[:-1].split(";")
        mod = parts[-1] if len(parts) > 1 else ""
        final = seq[-1]
        ctrl = "5" in mod
        if final == "C":
            return Key.WORD_RIGHT if ctrl else Key.RIGHT
        if final == "D":
            return Key.WORD_LEFT if ctrl else Key.LEFT
        return {
            "A": Key.UP,
            "B": Key.DOWN,
            "H": Key.HOME,
            "F": Key.END,
        }.get(final)
    return None


class PosixConsole:
    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def enter_raw(self) -> None:
        if getattr(self, "_raw_depth", 0) == 0:
            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        self._raw_depth = getattr(self, "_raw_depth", 0) + 1

    def leave_raw(self) -> None:
        depth = getattr(self, "_raw_depth", 0) - 1
        self._raw_depth = max(0, depth)
        if depth <= 0 and hasattr(self, "_old"):
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)

    def read_key(self, *, timeout: Optional[float] = None) -> Optional[KeyEvent]:
        fd = sys.stdin.fileno()
        owned = getattr(self, "_raw_depth", 0) == 0
        if owned:
            self.enter_raw()
        try:
            slice_t = 0.05 if timeout is None else timeout
            ready, _, _ = select.select([fd], [], [], slice_t)
            if not ready:
                return None
            return self._decode(sys.stdin.read(1), fd)
        finally:
            if owned:
                self.leave_raw()

    def _decode(self, ch: str, fd: int) -> KeyEvent:
        if ch in ("\r", "\n"):
            return KeyEvent(Key.ENTER)
        if ch in ("\x7f", "\b"):
            return KeyEvent(Key.BACKSPACE)
        if ch == "\t":
            return KeyEvent(Key.TAB)
        ctrl = _CTRL.get(ch)
        if ctrl:
            return KeyEvent(ctrl)
        if ch == "\x1b":
            return self._ansi(fd)
        if ch.isprintable():
            return KeyEvent(Key.CHAR, ch)
        return KeyEvent(Key.CHAR, "")

    def _ansi(self, fd: int) -> KeyEvent:
        n1 = self._read_ch(fd, 0.04)
        if not n1:
            return KeyEvent(Key.CHAR, "")
        if n1 == "[":
            seq = ""
            for _ in range(12):
                c = self._read_ch(fd, 0.04)
                if not c:
                    break
                seq += c
                if c.isalpha() or c == "~":
                    break
            kind = _csi_kind(seq)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")
        if n1 == "O":
            n2 = self._read_ch(fd, 0.04)
            if n2 == "H":
                return KeyEvent(Key.HOME)
            if n2 == "F":
                return KeyEvent(Key.END)
        return KeyEvent(Key.CHAR, "")

    def _read_ch(self, fd: int, timeout: float) -> str:
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return ""
        return sys.stdin.read(1)
