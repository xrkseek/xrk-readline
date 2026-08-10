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
    WORD_LEFT = "word_left"
    WORD_RIGHT = "word_right"
    CTRL_A = "ctrl_a"
    CTRL_E = "ctrl_e"
    CTRL_K = "ctrl_k"
    CTRL_U = "ctrl_u"
    CTRL_W = "ctrl_w"
    CTRL_L = "ctrl_l"
    CTRL_Y = "ctrl_y"
    CTRL_C = "ctrl_c"
    CTRL_D = "ctrl_d"
    CHAR = "char"


@dataclass(frozen=True)
class KeyEvent:
    kind: str
    char: str = ""
