"""按键流：ESC/CSI/SS3 挂起；POSIX UTF-8 字节拼成 Unicode；孤儿 [A 恢复。"""

from __future__ import annotations

import time
from typing import List, Optional

from .keys import Key, KeyEvent

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


def _utf8_need(lead: int) -> int:
    if lead < 0x80:
        return 1
    if lead < 0xC2 or lead > 0xF4:
        return 0
    if lead < 0xE0:
        return 2
    if lead < 0xF0:
        return 3
    return 4


class KeyStream:
    def __init__(self) -> None:
        self._q: List[str] = []
        self._utf8 = bytearray()
        self._hold_at: Optional[float] = None

    @property
    def pending(self) -> bool:
        return bool(self._q) or bool(self._utf8)

    def clear(self) -> None:
        self._q.clear()
        self._utf8.clear()
        self._hold_at = None

    def push(self, ch: str) -> None:
        """已是 Unicode 字符（Windows getwch）。"""
        if ch:
            self._q.append(ch)

    def push_bytes(self, data: bytes) -> None:
        """原始字节（POSIX os.read）：按 UTF-8 拼成字符再入队。"""
        if not data:
            return
        self._utf8.extend(data)
        while self._utf8:
            lead = self._utf8[0]
            # 控制/ASCII：直接出队（含 ESC）
            if lead < 0x80:
                self._q.append(chr(self._utf8.pop(0)))
                continue
            need = _utf8_need(lead)
            if need < 2:
                self._utf8.pop(0)
                continue
            if len(self._utf8) < need:
                break
            raw = bytes(self._utf8[:need])
            try:
                self._q.append(raw.decode("utf-8"))
                del self._utf8[:need]
            except UnicodeDecodeError:
                self._utf8.pop(0)

    def poll(self, now: Optional[float] = None) -> Optional[KeyEvent]:
        now = time.monotonic() if now is None else now
        if not self._q:
            self._hold_at = None
            return None

        head = self._q[0]
        if head == "\x1b":
            return self._poll_esc(now)
        if len(head) == 1 and head in ("\x00", "\xe0"):
            return self._poll_win_legacy(now)

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
        if len(ch) == 1:
            ctrl = CTRL.get(ch)
            if ctrl:
                return KeyEvent(ctrl)
        if ch.isprintable() or (len(ch) == 1 and ord(ch) > 127) or len(ch) > 1:
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
                if len(c) != 1:
                    return False
                if c.isalpha() or c == "~":
                    return False
                if c not in "0123456789;?":
                    return False
            return True
        return self._q[0] == "O" and len(self._q) == 1

    def _poll_orphan_arrow(self) -> Optional[KeyEvent]:
        if not self._q:
            return None
        if self._q[0] == "[":
            end = None
            for i in range(1, min(len(self._q), 16)):
                c = self._q[i]
                if len(c) == 1 and (c.isalpha() or c == "~"):
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
        if self._q[0] == "O" and len(self._q) >= 2 and len(self._q[1]) == 1:
            kind = ss3_kind(self._q[1])
            if kind is None:
                return None
            self._drop_prefix(2)
            return KeyEvent(kind)
        return None

    def _poll_win_legacy(self, now: float) -> Optional[KeyEvent]:
        """``\\xe0``/``\\x00`` + 扫描码（↑=H ↓=P）。缺第二字节时死等，超时丢掉会漏出 H/P。"""
        if len(self._q) < 2:
            return None
        code = self._q[1]
        # 回车等：丢掉误入前缀，勿把 \\r 当扫描码
        if len(code) != 1 or code in ("\r", "\n", "\t", "\x1b", "\x08", "\x7f"):
            self._drop_head()
            return None
        kind = _WIN_LEGACY.get(code)
        if kind is None:
            self._drop_head()
            return None
        self._drop_prefix(2)
        return KeyEvent(kind)

    def _poll_esc(self, now: float) -> Optional[KeyEvent]:
        self._begin_hold(now)
        age = self._age(now)

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
                if len(c) == 1 and (c.isalpha() or c == "~"):
                    end = i
                    break
            if end is None:
                if age >= CSI_STUCK:
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
            kind = ss3_kind(ch) if len(ch) == 1 else None
            return KeyEvent(kind) if kind else KeyEvent(Key.CHAR, "")

        self._drop_head()
        return None
