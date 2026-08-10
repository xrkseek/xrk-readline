"""KeyStream 单元测试。"""

from __future__ import annotations

import time

from xrk_readline.keys import Key
from xrk_readline.keystream import KeyStream, csi_kind, ss3_kind


def test_tables() -> None:
    assert csi_kind("A") == Key.UP
    assert csi_kind("1;5D") == Key.WORD_LEFT
    assert ss3_kind("B") == Key.DOWN


def test_csi_across_polls() -> None:
    s = KeyStream()
    s.push("\x1b")
    assert s.poll(now=100.0) is None
    s.push("[")
    assert s.poll(now=100.1) is None
    s.push("A")
    ev = s.poll(now=100.2)
    assert ev is not None and ev.kind == Key.UP


def test_orphan_csi_no_esc() -> None:
    """终端吞掉 ESC 后只剩 [A。"""
    s = KeyStream()
    s.push("[")
    s.push("A")
    ev = s.poll(now=1.0)
    assert ev is not None and ev.kind == Key.UP


def test_orphan_ss3() -> None:
    s = KeyStream()
    s.push("O")
    s.push("B")
    ev = s.poll(now=1.0)
    assert ev is not None and ev.kind == Key.DOWN


def test_literal_bracket_stays() -> None:
    """单独 [ 后不是方向键终结符 → 仍当字符。"""
    s = KeyStream()
    s.push("[")
    s.push("x")
    ev = s.poll(now=1.0)
    assert ev is not None and ev.kind == Key.CHAR and ev.char == "["


def test_win_legacy() -> None:
    s = KeyStream()
    s.push("\xe0")
    assert s.poll(now=1.0) is None
    s.push("H")
    ev = s.poll(now=1.1)
    assert ev is not None and ev.kind == Key.UP


def test_orphan_csi_split() -> None:
    s = KeyStream()
    s.push("[")
    assert s.poll(now=1.0) is None
    s.push("A")
    ev = s.poll(now=1.1)
    assert ev is not None and ev.kind == Key.UP


if __name__ == "__main__":
    test_tables()
    test_csi_across_polls()
    test_orphan_csi_no_esc()
    test_orphan_csi_split()
    test_orphan_ss3()
    test_literal_bracket_stays()
    test_win_legacy()
    print("ok")
