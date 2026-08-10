"""按键流与历史解码测试。"""

from __future__ import annotations

import time

from xrk_readline.keys import Key
from xrk_readline.keystream import KeyStream, csi_kind, ss3_kind


def test_csi_ss3_tables() -> None:
    assert csi_kind("A") == Key.UP
    assert csi_kind("1;5D") == Key.WORD_LEFT
    assert csi_kind("3~") == Key.DELETE
    assert ss3_kind("B") == Key.DOWN


def test_csi_across_polls() -> None:
    """ESC 与 [A 分片到达：中途 poll 必须为 None，不能漏出 [A。"""
    s = KeyStream()
    s.push("\x1b")
    assert s.poll(now=100.0) is None
    s.push("[")
    assert s.poll(now=100.1) is None
    s.push("A")
    ev = s.poll(now=100.2)
    assert ev is not None and ev.kind == Key.UP


def test_ss3_across_polls() -> None:
    s = KeyStream()
    s.push("\x1b")
    assert s.poll(now=1.0) is None
    s.push("O")
    assert s.poll(now=1.1) is None
    s.push("A")
    ev = s.poll(now=1.2)
    assert ev is not None and ev.kind == Key.UP


def test_win_legacy_across_polls() -> None:
    s = KeyStream()
    s.push("\xe0")
    assert s.poll(now=1.0) is None
    s.push("H")
    ev = s.poll(now=1.1)
    assert ev is not None and ev.kind == Key.UP


def test_burst_csi() -> None:
    s = KeyStream()
    for ch in "\x1b[A":
        s.push(ch)
    ev = s.poll(now=time.monotonic())
    assert ev is not None and ev.kind == Key.UP


if __name__ == "__main__":
    test_csi_ss3_tables()
    test_csi_across_polls()
    test_ss3_across_polls()
    test_win_legacy_across_polls()
    test_burst_csi()
    print("ok")
