"""按键流：未完成的 ESC/CSI/SS3、Win 扩展键跨 poll 挂起，避免 [A 漏成字符。"""

from __future__ import annotations

import time
from typing import List, Optional

from .keys import Key, KeyEvent

ESC_WAIT = 0.4

CTRL = {
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

_ARROWS = {
    "A": Key.UP,
    "B": Key.DOWN,
    "C": Key.RIGHT,
    "D": Key.LEFT,
    "H": Key.HOME,
    "F": Key.END,
}

_TILDE = {
    "1": Key.HOME,
    "7": Key.HOME,
    "4": Key.END,
    "8": Key.END,
    "3": Key.DELETE,
}

_WIN_LEGACY = {
    "H": Key.UP,
    "P": Key.DOWN,
    "K": Key.LEFT,
    "M": Key.RIGHT,
    "G": Key.HOME,
    "O": Key.END,
    "S": Key.DELETE,
    "s": Key.WORD_LEFT,
    "t": Key.WORD_RIGHT,
}


def csi_kind(seq: str) -> Optional[str]:
    if not seq:
        return None
    if seq in _ARROWS:
        return _ARROWS[seq]
    if seq.endswith("~"):
        return _TILDE.get(seq[:-1].split(";", 1)[0])
    final = seq[-1]
    if final not in "ABCDHF":
        return None
    ctrl = ";5" in seq[:-1]
    if final == "C":
        return Key.WORD_RIGHT if ctrl else Key.RIGHT
    if final == "D":
        return Key.WORD_LEFT if ctrl else Key.LEFT
    return _ARROWS.get(final)


def ss3_kind(ch: str) -> Optional[str]:
    return _ARROWS.get(ch)


class KeyStream:
    """字符队列 → 完整 KeyEvent；缺字节时返回 None 并保留队列。"""

    def __init__(self) -> None:
        self._q: List[str] = []
        self._hold_at: Optional[float] = None

    @property
    def pending(self) -> bool:
        return bool(self._q)

    def clear(self) -> None:
        self._q.clear()
        self._hold_at = None

    def push(self, ch: str) -> None:
        if ch:
            self._q.append(ch)

    def push_bytes(self, data: bytes) -> None:
        if data:
            self._q.extend(data.decode("latin-1"))

    def poll(self, now: Optional[float] = None) -> Optional[KeyEvent]:
        now = time.monotonic() if now is None else now
        if not self._q:
            self._hold_at = None
            return None

        head = self._q[0]
        if head == "\x1b":
            return self._poll_esc(now)
        if head in ("\x00", "\xe0"):
            return self._poll_win_legacy()

        self._hold_at = None
        ch = self._q.pop(0)
        if ch in ("\r", "\n"):
            return KeyEvent(Key.ENTER)
        if ch in ("\x7f", "\b"):
            return KeyEvent(Key.BACKSPACE)
        if ch == "\t":
            return KeyEvent(Key.TAB)
        ctrl = CTRL.get(ch)
        if ctrl:
            return KeyEvent(ctrl)
        if ch.isprintable() or ord(ch) > 127:
            return KeyEvent(Key.CHAR, ch)
        return KeyEvent(Key.CHAR, "")

    def _begin_hold(self, now: float) -> None:
        if self._hold_at is None:
            self._hold_at = now

    def _timed_out(self, now: float) -> bool:
        return self._hold_at is not None and (now - self._hold_at) >= ESC_WAIT

    def _drop_head(self) -> None:
        if self._q:
            self._q.pop(0)
        self._hold_at = None

    def _poll_win_legacy(self) -> Optional[KeyEvent]:
        if len(self._q) < 2:
            return None
        self._q.pop(0)
        code = self._q.pop(0)
        self._hold_at = None
        kind = _WIN_LEGACY.get(code)
        return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")

    def _poll_esc(self, now: float) -> Optional[KeyEvent]:
        self._begin_hold(now)
        # 单独 ESC：超时丢弃；ESC[ / ESC O：死等终结，绝不漏 [A
        if len(self._q) < 2:
            if self._timed_out(now):
                self._drop_head()
            return None

        n1 = self._q[1]
        if n1 == "[":
            end = None
            for i in range(2, len(self._q)):
                c = self._q[i]
                if c.isalpha() or c == "~":
                    end = i
                    break
            if end is None:
                return None
            seq = "".join(self._q[2 : end + 1])
            del self._q[: end + 1]
            self._hold_at = None
            kind = csi_kind(seq)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")

        if n1 == "O":
            if len(self._q) < 3:
                return None
            ch = self._q[2]
            del self._q[:3]
            self._hold_at = None
            kind = ss3_kind(ch)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")

        self._drop_head()
        return None
