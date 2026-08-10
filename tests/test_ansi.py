"""KeyStream 单元测试。"""

from __future__ import annotations

from xrk_readline.keys import Key
from xrk_readline.keystream import KeyStream, csi_kind, ss3_kind


def test_tables() -> None:
    assert csi_kind("A") == Key.UP
    assert ss3_kind("B") == Key.DOWN


def test_utf8_chinese() -> None:
    """帮助 = UTF-8 E5 B8 AE E5 8A A9，不得拆成 latin-1 乱码。"""
    s = KeyStream()
    s.push_bytes("帮助".encode("utf-8"))
    a = s.poll(now=1.0)
    b = s.poll(now=1.0)
    assert a is not None and a.kind == Key.CHAR and a.char == "帮"
    assert b is not None and b.kind == Key.CHAR and b.char == "助"


def test_utf8_split_packets() -> None:
    raw = "帮".encode("utf-8")
    s = KeyStream()
    s.push_bytes(raw[:1])
    assert s.poll(now=1.0) is None
    assert s.pending
    s.push_bytes(raw[1:])
    ev = s.poll(now=1.1)
    assert ev is not None and ev.char == "帮"


def test_csi_and_orphan() -> None:
    s = KeyStream()
    s.push("\x1b")
    assert s.poll(now=1.0) is None
    s.push_bytes(b"[A")
    assert s.poll(now=1.1).kind == Key.UP

    s2 = KeyStream()
    s2.push_bytes(b"[B")
    assert s2.poll(now=1.0).kind == Key.DOWN


def test_literal_bracket() -> None:
    s = KeyStream()
    s.push("[")
    s.push("x")
    ev = s.poll(now=1.0)
    assert ev is not None and ev.char == "["


def test_win_enter_not_swallowed_by_xe0() -> None:
    """IME 残留 \\xe0 后按回车，不得把 \\r 当扫描码吃掉。"""
    s = KeyStream()
    s.push("\xe0")
    s.push("\r")
    # 先丢掉 \\xe0
    assert s.poll(now=1.0) is None
    ev = s.poll(now=1.0)
    assert ev is not None and ev.kind == Key.ENTER


def test_win_legacy_arrow_waits() -> None:
    """\\xe0 后即使隔很久也不能丢掉，否则会打出 H/P。"""
    s = KeyStream()
    s.push("\xe0")
    assert s.poll(now=1.0) is None
    assert s.poll(now=2.0) is None
    s.push("H")
    ev = s.poll(now=2.1)
    assert ev is not None and ev.kind == Key.UP
    s.push("\xe0")
    s.push("P")
    assert s.poll(now=3.0).kind == Key.DOWN


def test_history_skips_same_as_current() -> None:
    from xrk_readline.history import History

    h = History()
    h.add("a")
    h.add("b")
    # 当前已是最新历史时，一下 ↑ 应跳到更旧的 a
    assert h.older("b") == "a"


if __name__ == "__main__":
    test_tables()
    test_utf8_chinese()
    test_utf8_split_packets()
    test_csi_and_orphan()
    test_literal_bracket()
    test_win_enter_not_swallowed_by_xe0()
    test_win_legacy_arrow_waits()
    test_history_skips_same_as_current()
    print("ok")
