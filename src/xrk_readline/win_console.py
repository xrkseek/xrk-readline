"""Windows 控制台：ReadConsoleInput 按虚拟键识别，避免 msvcrt \\xe0+H 拆包要按两下。"""

from __future__ import annotations

import ctypes
import msvcrt
import sys
import time
from ctypes import wintypes
from typing import Optional

from .keys import Key, KeyEvent
from .keystream import KeyStream

_ENABLE_VT_OUT = 0x0004
_KEY_EVENT = 0x0001

_VK_LEFT = 0x25
_VK_UP = 0x26
_VK_RIGHT = 0x27
_VK_DOWN = 0x28
_VK_HOME = 0x24
_VK_END = 0x23
_VK_DELETE = 0x2E
_VK_BACK = 0x08
_VK_TAB = 0x09
_VK_RETURN = 0x0D
_VK_ESCAPE = 0x1B

_CTRL_MASK = 0x0008 | 0x0004  # LEFT_CTRL | RIGHT_CTRL

_kernel32 = ctypes.windll.kernel32
_kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
_kernel32.GetStdHandle.restype = wintypes.HANDLE
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.ReadConsoleInputW.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
_kernel32.ReadConsoleInputW.restype = wintypes.BOOL
_vt_ready = False


class _KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("UnicodeChar", wintypes.WCHAR),
        ("dwControlKeyState", wintypes.DWORD),
    ]


class _INPUT_RECORD(ctypes.Structure):
    class _EVENT(ctypes.Union):
        _fields_ = [("KeyEvent", _KEY_EVENT_RECORD)]

    _anonymous_ = ("Event",)
    _fields_ = [
        ("EventType", wintypes.WORD),
        ("Event", _EVENT),
    ]


def _ensure_vt_out() -> None:
    global _vt_ready
    if _vt_ready:
        return
    try:
        handle = _kernel32.GetStdHandle(-11)
        mode = wintypes.DWORD()
        if _kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            _kernel32.SetConsoleMode(handle, mode.value | _ENABLE_VT_OUT)
    except Exception:
        pass
    _vt_ready = True


def _vk_event(vk: int, ctrl: bool) -> Optional[KeyEvent]:
    if vk == _VK_UP:
        return KeyEvent(Key.UP)
    if vk == _VK_DOWN:
        return KeyEvent(Key.DOWN)
    if vk == _VK_LEFT:
        return KeyEvent(Key.WORD_LEFT if ctrl else Key.LEFT)
    if vk == _VK_RIGHT:
        return KeyEvent(Key.WORD_RIGHT if ctrl else Key.RIGHT)
    if vk == _VK_HOME:
        return KeyEvent(Key.HOME)
    if vk == _VK_END:
        return KeyEvent(Key.END)
    if vk == _VK_DELETE:
        return KeyEvent(Key.DELETE)
    if vk == _VK_BACK:
        return KeyEvent(Key.BACKSPACE)
    if vk == _VK_TAB:
        return KeyEvent(Key.TAB)
    if vk == _VK_RETURN:
        return KeyEvent(Key.ENTER)
    return None


class WinConsole:
    def __init__(self) -> None:
        _ensure_vt_out()
        self._stream = KeyStream()
        self._hin = _kernel32.GetStdHandle(-10)
        self._use_console_input = self._hin not in (0, -1, None)

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def enter_raw(self) -> None:
        self._stream.clear()

    def leave_raw(self) -> None:
        self._stream.clear()

    def read_key(self, *, timeout: Optional[float] = None) -> Optional[KeyEvent]:
        if self._use_console_input:
            return self._read_console_input(timeout=timeout)
        return self._read_msvcrt(timeout=timeout)

    def _read_console_input(self, *, timeout: Optional[float]) -> Optional[KeyEvent]:
        deadline = None if timeout is None else time.monotonic() + timeout
        # 先消化 KeyStream 里可能残留的字节路径事件
        ev = self._stream.poll()
        if ev is not None:
            return ev

        while True:
            wait_ms = 50
            if deadline is not None:
                remain = deadline - time.monotonic()
                if remain <= 0:
                    return self._stream.poll()
                wait_ms = max(1, min(50, int(remain * 1000)))

            rc = _kernel32.WaitForSingleObject(self._hin, wait_ms)
            if rc != 0:  # WAIT_TIMEOUT / failed
                if deadline is not None and time.monotonic() >= deadline:
                    return self._stream.poll()
                continue

            record = _INPUT_RECORD()
            read = wintypes.DWORD()
            if not _kernel32.ReadConsoleInputW(
                self._hin, ctypes.byref(record), 1, ctypes.byref(read)
            ):
                continue
            if read.value != 1 or record.EventType != _KEY_EVENT:
                continue
            ke = record.KeyEvent
            if not ke.bKeyDown:
                continue

            ctrl = bool(ke.dwControlKeyState & _CTRL_MASK)
            mapped = _vk_event(ke.wVirtualKeyCode, ctrl)
            if mapped is not None:
                return mapped

            ch = ke.UnicodeChar
            if not ch or ch == "\x00":
                continue
            if ch == "\r" or ch == "\n":
                return KeyEvent(Key.ENTER)
            if ch == "\x08":
                return KeyEvent(Key.BACKSPACE)
            if ch == "\t":
                return KeyEvent(Key.TAB)
            if ch == "\x03":
                return KeyEvent(Key.CTRL_C)
            if ch == "\x04":
                return KeyEvent(Key.CTRL_D)
            if ch == "\x01":
                return KeyEvent(Key.CTRL_A)
            if ch == "\x05":
                return KeyEvent(Key.CTRL_E)
            if ch == "\x0b":
                return KeyEvent(Key.CTRL_K)
            if ch == "\x15":
                return KeyEvent(Key.CTRL_U)
            if ch == "\x17":
                return KeyEvent(Key.CTRL_W)
            if ch == "\x0c":
                return KeyEvent(Key.CTRL_L)
            if ch == "\x19":
                return KeyEvent(Key.CTRL_Y)
            if ch.isprintable() or ord(ch) > 127:
                return KeyEvent(Key.CHAR, ch)

    def _read_msvcrt(self, *, timeout: Optional[float]) -> Optional[KeyEvent]:
        """无控制台句柄时回退（少见）。"""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            self._pump_msvcrt()
            for _ in range(4):
                ev = self._stream.poll()
                if ev is not None:
                    return ev
                if not self._stream.pending:
                    break
                time.sleep(0.005)
                self._pump_msvcrt()
            if deadline is not None and time.monotonic() >= deadline:
                return self._stream.poll()
            time.sleep(0.005)

    def _pump_msvcrt(self) -> None:
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            self._stream.push(ch)
            if ch in ("\x00", "\xe0"):
                end = time.monotonic() + 0.05
                while time.monotonic() < end:
                    if msvcrt.kbhit():
                        self._stream.push(msvcrt.getwch())
                        break
                    time.sleep(0.001)
