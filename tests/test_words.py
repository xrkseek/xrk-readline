"""词跳转。"""

from __future__ import annotations

from xrk_readline.editor import _word_left, _word_right


def test_word_nav() -> None:
    #  f o o _ _ b a r - b a z
    #  0 1 2 3 4 5 6 7 8 9 10 11
    buf = list("foo  bar-baz")
    assert _word_left(buf, 12) == 9
    assert _word_left(buf, 9) == 5
    assert _word_left(buf, 5) == 0
    assert _word_right(buf, 0) == 3
    assert _word_right(buf, 3) == 8
    assert _word_right(buf, 8) == 12


if __name__ == "__main__":
    test_word_nav()
    print("ok")
