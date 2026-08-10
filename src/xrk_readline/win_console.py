"""Windows：msvcrt；扩展键一次读齐两字节，避免只剩 H/P。"""

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
            for _ in range(4):
                ev = self._stream.poll()
                if ev is not None:
                    return ev
                if not self._stream.pending:
                    break
                # 半截 \\xe0：再吸一眼第二字节
                time.sleep(0.005)
                self._pump()
            if deadline is not None and time.monotonic() >= deadline:
                return self._stream.poll()
            time.sleep(0.005)

    def _pump(self) -> None:
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            self._stream.push(ch)
            # 扩展键：同一次泵入扫描码，避免 \\xe0 与 H 被拆到两次 poll
            if ch in ("\x00", "\xe0") and msvcrt.kbhit():
                self._stream.push(msvcrt.getwch())
