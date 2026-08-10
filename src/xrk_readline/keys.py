"""按键事件常量。"""

from __future__ import annotations

from dataclasses import dataclass


class Key:
    ENTER = "enter"
    BACKSPACE = "backspace"
    DELETE = "delete"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    HOME = "home"
    END = "end"
    TAB = "tab"
    CTRL_C = "ctrl_c"
    CTRL_D = "ctrl_d"
    CHAR = "char"


@dataclass(frozen=True)
class KeyEvent:
    kind: str
    char: str = ""
