"""Windows：msvcrt 扩展键优先；仅输出开 VT（不开 VT 输入，避免 ESC[A 与 msvcrt 打架）。"""

from __future__ import annotations

import ctypes
import msvcrt
import sys
import time
from typing import Optional

from .keys import KeyEvent
from .keystream import KeyStream

_ENABLE_VT_OUT = 0x0004
_vt_ready = False


def _ensure_vt_out() -> None:
    global _vt_ready
    if _vt_ready:
        return
    try:
        handle = ctypes.windll.kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ctypes.windll.kernel32.SetConsoleMode(handle, mode.value | _ENABLE_VT_OUT)
    except Exception:
        pass
    _vt_ready = True


class WinConsole:
    def __init__(self) -> None:
        _ensure_vt_out()
        self._stream = KeyStream()

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def read_key(self, *, timeout: Optional[float] = None) -> Optional[KeyEvent]:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            self._pump()
            ev = self._stream.poll()
            if ev is not None:
                return ev
            if deadline is not None and time.monotonic() >= deadline:
                # 再 poll 一次：让挂起 ESC/\xe0 超时丢弃
                return self._stream.poll()
            time.sleep(0.005)

    def _pump(self) -> None:
        while msvcrt.kbhit():
            self._stream.push(msvcrt.getwch())
