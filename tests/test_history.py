"""历史上下键来回切换。"""

from __future__ import annotations

from xrk_readline.history import History


def test_up_down_roundtrip() -> None:
    h = History()
    h.add("one")
    h.add("two")
    h.add("three")

    assert h.older("draft") == "three"
    assert h.older("three") == "two"
    assert h.older("two") == "one"
    assert h.older("one") is None  # 已在最旧

    assert h.newer("one") == "two"
    assert h.newer("two") == "three"
    assert h.newer("three") == "draft"
    assert h.newer("draft") is None  # 已在草稿

    assert h.older("draft") == "three"
    assert h.newer("three") == "draft"


def test_reset_allows_fresh_up() -> None:
    h = History()
    h.add("a")
    assert h.older("") == "a"
    h.reset_nav()
    assert h.older("x") == "a"
    assert h.newer("a") == "x"


if __name__ == "__main__":
    test_up_down_roundtrip()
    test_reset_allows_fresh_up()
    print("ok")
