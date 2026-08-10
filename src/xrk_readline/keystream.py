"""按键流：跨 poll 挂起未完成序列；兼容 SSH/xterm 吞掉 ESC 只剩 [A 的情况。"""

from __future__ import annotations

import time
from typing import List, Optional

from .keys import Key, KeyEvent

# 单独 ESC 等待；半截 CSI 更长，超时整段丢弃（不漏成字符）
ESC_WAIT = 1.0
CSI_STUCK = 2.5

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

        orphan = self._poll_orphan_arrow()
        if orphan is not None:
            return orphan
        if self._orphan_waiting():
            return None

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

    def _age(self, now: float) -> float:
        return 0.0 if self._hold_at is None else (now - self._hold_at)

    def _drop_head(self) -> None:
        if self._q:
            self._q.pop(0)
        self._hold_at = None

    def _drop_prefix(self, n: int) -> None:
        del self._q[:n]
        self._hold_at = None

    def _orphan_waiting(self) -> bool:
        if not self._q:
            return False
        if self._q[0] == "[":
            if len(self._q) == 1:
                return True
            for c in self._q[1:]:
                if c.isalpha() or c == "~":
                    return False
                if c not in "0123456789;?":
                    return False
            return True
        if self._q[0] == "O":
            return len(self._q) == 1
        return False

    def _poll_orphan_arrow(self) -> Optional[KeyEvent]:
        """无 ESC 的 CSI/SS3 残片（ConPTY / 部分 SSH）。"""
        if not self._q:
            return None
        if self._q[0] == "[":
            end = None
            for i in range(1, min(len(self._q), 16)):
                c = self._q[i]
                if c.isalpha() or c == "~":
                    end = i
                    break
            if end is None:
                return None
            seq = "".join(self._q[1 : end + 1])
            kind = csi_kind(seq)
            if kind is None:
                return None
            self._drop_prefix(end + 1)
            return KeyEvent(kind)
        if self._q[0] == "O" and len(self._q) >= 2:
            kind = ss3_kind(self._q[1])
            if kind is None:
                return None
            self._drop_prefix(2)
            return KeyEvent(kind)
        return None

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
        age = self._age(now)

        # ESC ESC… → 折叠为一个 ESC
        while len(self._q) >= 2 and self._q[0] == "\x1b" and self._q[1] == "\x1b":
            self._q.pop(0)

        if len(self._q) < 2:
            if age >= ESC_WAIT:
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
                if age >= CSI_STUCK:
                    # 半截 CSI：整段丢掉，绝不把 [ 打进行缓冲
                    self._q.clear()
                    self._hold_at = None
                return None
            seq = "".join(self._q[2 : end + 1])
            self._drop_prefix(end + 1)
            kind = csi_kind(seq)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")

        if n1 == "O":
            if len(self._q) < 3:
                if age >= CSI_STUCK:
                    self._q.clear()
                    self._hold_at = None
                return None
            ch = self._q[2]
            self._drop_prefix(3)
            kind = ss3_kind(ch)
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")

        # ESC + 普通字符：当作 Alt，忽略修饰，保留后续字符
        self._drop_head()
        return None
