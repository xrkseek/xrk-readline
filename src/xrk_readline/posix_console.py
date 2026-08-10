"""POSIX 控制台：termios cbreak + ANSI。"""

from __future__ import annotations

import select
import sys
import termios
import tty
from contextlib import contextmanager
from typing import Iterator, Optional

from .keys import Key, KeyEvent


class PosixConsole:
    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    @contextmanager
    def _cbreak(self) -> Iterator[None]:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def read_key(self, *, timeout: Optional[float] = None) -> Optional[KeyEvent]:
        fd = sys.stdin.fileno()
        # 每次短超时轮询，便于外部 stop；整段 readline 期间保持 cbreak
        if not hasattr(self, "_raw_depth"):
            self._raw_depth = 0
        return self._read_with_raw(fd, timeout)

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

    def _read_with_raw(self, fd: int, timeout: Optional[float]) -> Optional[KeyEvent]:
        owned = getattr(self, "_raw_depth", 0) == 0
        if owned:
            self.enter_raw()
        try:
            slice_t = 0.05 if timeout is None else timeout
            while True:
                ready, _, _ = select.select([fd], [], [], slice_t)
                if ready:
                    ch = sys.stdin.read(1)
                    return self._decode(ch, fd)
                if timeout is not None:
                    return None
                # timeout is None：一直等到有键
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
        # 非阻塞再读
        seq = ""
        for _ in range(4):
            ready, _, _ = select.select([fd], [], [], 0.02)
            if not ready:
                break
            seq += sys.stdin.read(1)
        table = {
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
        for key, kind in table.items():
            if seq.startswith(key) or seq == key:
                return KeyEvent(kind)
        if seq.startswith("[3"):
            return KeyEvent(Key.DELETE)
        return KeyEvent(Key.CHAR, "")
