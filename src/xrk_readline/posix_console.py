"""POSIX：raw + os.read → KeyStream（SSH/xterm 友好）。"""

from __future__ import annotations

import os
import select
import sys
import termios
import tty
from typing import Optional

from .keys import KeyEvent
from .keystream import KeyStream

# 普通光标键 + 数字小键盘；仍识别 ESC OA
_TERM_SETUP = b"\x1b[?1l\x1b>"


class PosixConsole:
    def __init__(self) -> None:
        self._fd = -1
        self._old: Optional[list] = None
        self._raw_depth = 0
        self._stream = KeyStream()

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def enter_raw(self) -> None:
        if self._raw_depth == 0:
            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
            # setraw：关回显/规范模式，SSH 下比 cbreak 更稳
            tty.setraw(self._fd)
            self._stream.clear()
            try:
                os.write(sys.stdout.fileno(), _TERM_SETUP)
            except OSError:
                pass
        self._raw_depth += 1

    def leave_raw(self) -> None:
        self._raw_depth = max(0, self._raw_depth - 1)
        if self._raw_depth == 0 and self._old is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)
            self._old = None
            self._stream.clear()

    def read_key(self, *, timeout: Optional[float] = None) -> Optional[KeyEvent]:
        fd = sys.stdin.fileno()
        owned = self._raw_depth == 0
        if owned:
            self.enter_raw()
        try:
            wait = 0.05 if timeout is None else timeout
            self._pump(fd, wait)
            # 半截序列：同一次调用里再等一小段（SSH 分包）
            for _ in range(3):
                ev = self._stream.poll()
                if ev is not None:
                    return ev
                if not self._stream.pending:
                    return None
                self._pump(fd, 0.03)
            return self._stream.poll()
        finally:
            if owned:
                self.leave_raw()

    def _ready(self, fd: int, timeout: float) -> bool:
        try:
            ready, _, _ = select.select([fd], [], [], max(0.0, timeout))
        except (ValueError, OSError):
            return False
        return bool(ready)

    def _pump(self, fd: int, timeout: float) -> None:
        if not self._ready(fd, timeout):
            return
        while self._ready(fd, 0.0):
            try:
                chunk = os.read(fd, 512)
            except OSError:
                break
            if not chunk:
                break
            self._stream.push_bytes(chunk)
