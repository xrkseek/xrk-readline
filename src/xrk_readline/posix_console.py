"""POSIX 控制台：termios cbreak + ANSI。"""

from __future__ import annotations

import select
import sys
import termios
import tty
from typing import Optional

from .keys import Key, KeyEvent

_CSI = {
    "[A": Key.UP,
    "[B": Key.DOWN,
    "[C": Key.RIGHT,
    "[D": Key.LEFT,
    "[H": Key.HOME,
    "[F": Key.END,
    "[3~": Key.DELETE,
    "OH": Key.HOME,
    "OF": Key.END,
}


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
        if ch == "\x03":
            return KeyEvent(Key.CTRL_C)
        if ch == "\x04":
            return KeyEvent(Key.CTRL_D)
        if ch == "\x1b":
            return self._ansi(fd)
        if ch.isprintable():
            return KeyEvent(Key.CHAR, ch)
        return KeyEvent(Key.CHAR, "")

    def _ansi(self, fd: int) -> KeyEvent:
        seq = ""
        for _ in range(6):
            ready, _, _ = select.select([fd], [], [], 0.025)
            if not ready:
                break
            seq += sys.stdin.read(1)
            for key, kind in _CSI.items():
                if seq == key or seq.startswith(key):
                    return KeyEvent(kind)
        return KeyEvent(Key.CHAR, "")
