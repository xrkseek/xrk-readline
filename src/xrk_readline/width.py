"""终端显示宽度与光标几何（含 CJK / 折行）。"""

from __future__ import annotations

import shutil
import unicodedata


def char_width(ch: str) -> int:
    if not ch:
        return 0
    if unicodedata.combining(ch):
        return 0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("F", "W"):
        return 2
    if ord(ch) >= 0x1F300:
        return 2
    return 1


def text_width(s: str) -> int:
    return sum(char_width(c) for c in s)


def term_cols(fallback: int = 80) -> int:
    try:
        return max(8, shutil.get_terminal_size().columns)
    except OSError:
        return fallback


def rows_for(width: int, cols: int) -> int:
    if width <= 0:
        return 1
    return width // cols + (1 if width % cols else 0)


def xy_for(offset: int, cols: int) -> tuple[int, int]:
    """显示列 offset 对应的 (row, col)，从块左上角起算。"""
    if offset <= 0 or cols <= 0:
        return 0, 0
    return offset // cols, offset % cols
