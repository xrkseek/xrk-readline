"""终端显示宽度（含 CJK）。"""

from __future__ import annotations

import unicodedata


def char_width(ch: str) -> int:
    if not ch:
        return 0
    if unicodedata.combining(ch):
        return 0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("F", "W"):
        return 2
    # emoji / 部分符号
    if ord(ch) >= 0x1F300:
        return 2
    return 1


def text_width(s: str) -> int:
    return sum(char_width(c) for c in s)


def slice_by_width(s: str, max_width: int) -> str:
    """截到不超过 max_width 列（用于极端窄终端时可扩展）。"""
    out: list[str] = []
    w = 0
    for c in s:
        cw = char_width(c)
        if w + cw > max_width:
            break
        out.append(c)
        w += cw
    return "".join(out)
