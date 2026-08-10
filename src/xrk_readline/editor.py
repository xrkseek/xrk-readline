"""行编辑。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .console import create_console
from .history import History
from .keys import Key
from .width import rows_for, term_cols, text_width, xy_for

Completer = Callable[[str, int], Optional[str]]


def _is_word(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _word_left(buf: List[str], pos: int) -> int:
    i = pos
    while i > 0 and not _is_word(buf[i - 1]):
        i -= 1
    while i > 0 and _is_word(buf[i - 1]):
        i -= 1
    return i


def _word_right(buf: List[str], pos: int) -> int:
    i = pos
    n = len(buf)
    while i < n and not _is_word(buf[i]):
        i += 1
    while i < n and _is_word(buf[i]):
        i += 1
    return i


class Readline:
    def __init__(self, *, history_size: int = 500) -> None:
        self._history = History(history_size)
        self._completer: Optional[Completer] = None
        self._completer_delims = " \t\n;"
        self._console = create_console()
        self._stop_check: Optional[Callable[[], bool]] = None
        self._kill: str = ""

    def set_history_length(self, n: int) -> None:
        self._history.set_max_len(n)

    def read_history_file(self, path: str | Path) -> None:
        self._history.load(path)

    def write_history_file(self, path: str | Path) -> None:
        self._history.save(path)

    def set_completer(self, fn: Optional[Completer]) -> None:
        self._completer = fn

    def set_completer_delims(self, delims: str) -> None:
        self._completer_delims = delims or " \t\n;"

    def set_stop_check(self, fn: Optional[Callable[[], bool]]) -> None:
        self._stop_check = fn

    def parse_and_bind(self, _line: str) -> None:
        pass

    def readline(self, prompt: str = "") -> str:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            self._console.write(prompt)
            self._console.flush()
            line = sys.stdin.readline()
            if line == "":
                raise EOFError
            return line

        self._history.reset_nav()
        buf: List[str] = []
        pos = 0
        prev_rows = 1
        enter_raw = getattr(self._console, "enter_raw", None)
        leave_raw = getattr(self._console, "leave_raw", None)
        if callable(enter_raw):
            enter_raw()

        try:
            prev_rows = self._paint(prompt, buf, pos, prev_rows)

            while True:
                if self._stop_check and self._stop_check():
                    self._console.write("\n")
                    self._console.flush()
                    raise EOFError

                ev = self._console.read_key(timeout=0.05)
                if ev is None:
                    continue
                kind = ev.kind

                if kind == Key.ENTER:
                    line = "".join(buf)
                    self._console.write("\n")
                    self._console.flush()
                    self._history.add(line)
                    return line + "\n"

                if kind == Key.CTRL_C:
                    if buf:
                        buf.clear()
                        pos = 0
                        self._history.reset_nav()
                        prev_rows = self._paint(prompt, buf, pos, prev_rows)
                        continue
                    self._console.write("^C\n")
                    self._console.flush()
                    self._history.reset_nav()
                    raise KeyboardInterrupt

                if kind == Key.CTRL_D:
                    if not buf:
                        self._console.write("\n")
                        self._console.flush()
                        raise EOFError
                    if pos < len(buf):
                        del buf[pos]
                        prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.CTRL_L:
                    self._console.write("\x1b[H\x1b[2J")
                    self._console.flush()
                    prev_rows = self._paint(prompt, buf, pos, 1)
                    continue

                if kind in (Key.HOME, Key.CTRL_A):
                    pos = 0
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind in (Key.END, Key.CTRL_E):
                    pos = len(buf)
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.CTRL_K:
                    if pos < len(buf):
                        self._kill = "".join(buf[pos:])
                        del buf[pos:]
                        prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.CTRL_U:
                    if pos > 0:
                        self._kill = "".join(buf[:pos])
                        del buf[:pos]
                        pos = 0
                        prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.CTRL_W:
                    left = _word_left(buf, pos)
                    if left < pos:
                        self._kill = "".join(buf[left:pos])
                        del buf[left:pos]
                        pos = left
                        prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.CTRL_Y and self._kill:
                    buf[pos:pos] = list(self._kill)
                    pos += len(self._kill)
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.BACKSPACE and pos > 0:
                    del buf[pos - 1]
                    pos -= 1
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.DELETE and pos < len(buf):
                    del buf[pos]
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.LEFT and pos > 0:
                    pos -= 1
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.RIGHT and pos < len(buf):
                    pos += 1
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.WORD_LEFT:
                    pos = _word_left(buf, pos)
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.WORD_RIGHT:
                    pos = _word_right(buf, pos)
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.UP:
                    nxt = self._history.older("".join(buf))
                    if nxt is not None:
                        buf[:] = list(nxt)
                        pos = len(buf)
                        prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.DOWN:
                    nxt = self._history.newer("".join(buf))
                    if nxt is not None:
                        buf[:] = list(nxt)
                        pos = len(buf)
                        prev_rows = self._paint(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.TAB:
                    prev_rows, pos = self._complete(prompt, buf, pos, prev_rows)
                    continue

                if kind == Key.CHAR and ev.char:
                    buf[pos:pos] = list(ev.char)
                    pos += len(ev.char)
                    prev_rows = self._paint(prompt, buf, pos, prev_rows)
        finally:
            if callable(leave_raw):
                leave_raw()

    def _complete(
        self, prompt: str, buf: List[str], pos: int, prev_rows: int
    ) -> Tuple[int, int]:
        if not self._completer:
            return prev_rows, pos
        line = "".join(buf)
        start = pos
        while start > 0 and line[start - 1] not in self._completer_delims:
            start -= 1
        prefix = line[start:pos]
        matches: List[str] = []
        state = 0
        while state <= 256:
            m = self._completer(prefix, state)
            if m is None:
                break
            matches.append(m)
            state += 1
        if not matches:
            return prev_rows, pos

        if len(matches) == 1:
            insertion = matches[0]
            buf[:] = list(line[:start] + insertion + line[pos:])
            new_pos = start + len(insertion)
            return self._paint(prompt, buf, new_pos, prev_rows), new_pos

        self._console.write("\n" + "  ".join(matches) + "\n")
        self._console.flush()
        common = matches[0]
        for m in matches[1:]:
            i = 0
            while i < len(common) and i < len(m) and common[i] == m[i]:
                i += 1
            common = common[:i]
        if len(common) > len(prefix):
            buf[:] = list(line[:start] + common + line[pos:])
            new_pos = start + len(common)
            return self._paint(prompt, buf, new_pos, 1), new_pos
        return self._paint(prompt, buf, pos, 1), pos

    def _paint(self, prompt: str, buf: List[str], pos: int, prev_rows: int) -> int:
        cols = term_cols()
        text = "".join(buf)
        total_w = text_width(prompt) + text_width(text)
        cur_w = text_width(prompt) + text_width(text[:pos])
        rows = rows_for(total_w, cols)

        if prev_rows > 1:
            self._console.write(f"\x1b[{prev_rows - 1}A")
        self._console.write("\r\x1b[J")
        self._console.write(prompt + text)

        er, ec = xy_for(total_w, cols)
        tr, tc = xy_for(cur_w, cols)
        if er > tr:
            self._console.write(f"\x1b[{er - tr}A")
        elif tr > er:
            self._console.write(f"\x1b[{tr - er}B")
        if ec > tc:
            self._console.write(f"\x1b[{ec - tc}D")
        elif tc > ec:
            self._console.write(f"\x1b[{tc - ec}C")
        self._console.flush()
        return max(1, rows)
