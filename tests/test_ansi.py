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


if __name__ == "__main__":
    test_tables()
    test_utf8_chinese()
    test_utf8_split_packets()
    test_csi_and_orphan()
    test_literal_bracket()
    print("ok")
