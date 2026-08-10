"""行编辑核心。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .console import create_console
from .history import History
from .keys import Key
from .width import text_width

Completer = Callable[[str, int], Optional[str]]


class Readline:
    """行编辑：C 控制台后端（或纯 Python 回退）+ Python 编辑逻辑。"""

    def __init__(self, *, history_size: int = 500) -> None:
        self._history = History(history_size)
        self._completer: Optional[Completer] = None
        self._completer_delims = " \t\n;"
        self._console = create_console()
        self._stop_check: Optional[Callable[[], bool]] = None

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
        """兼容 GNU readline 调用点。"""

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
        clear_w = 0
        enter_raw = getattr(self._console, "enter_raw", None)
        leave_raw = getattr(self._console, "leave_raw", None)
        if callable(enter_raw):
            enter_raw()

        try:
            clear_w = self._paint(prompt, buf, pos, clear_w)

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
                        clear_w = self._paint(prompt, buf, pos, clear_w)
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
                        clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.BACKSPACE and pos > 0:
                    del buf[pos - 1]
                    pos -= 1
                    clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.DELETE and pos < len(buf):
                    del buf[pos]
                    clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.LEFT and pos > 0:
                    pos -= 1
                    clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.RIGHT and pos < len(buf):
                    pos += 1
                    clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.HOME:
                    pos = 0
                    clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.END:
                    pos = len(buf)
                    clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.UP:
                    nxt = self._history.older("".join(buf))
                    if nxt is not None:
                        buf[:] = list(nxt)
                        pos = len(buf)
                        clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.DOWN:
                    nxt = self._history.newer("".join(buf))
                    if nxt is not None:
                        buf[:] = list(nxt)
                        pos = len(buf)
                        clear_w = self._paint(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.TAB:
                    clear_w, pos = self._complete(prompt, buf, pos, clear_w)
                    continue

                if kind == Key.CHAR and ev.char:
                    buf[pos:pos] = list(ev.char)
                    pos += len(ev.char)
                    clear_w = self._paint(prompt, buf, pos, clear_w)
        finally:
            if callable(leave_raw):
                leave_raw()

    def _complete(
        self, prompt: str, buf: List[str], pos: int, clear_w: int
    ) -> Tuple[int, int]:
        if not self._completer:
            return clear_w, pos
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
            return clear_w, pos

        if len(matches) == 1:
            insertion = matches[0]
            buf[:] = list(line[:start] + insertion + line[pos:])
            new_pos = start + len(insertion)
            return self._paint(prompt, buf, new_pos, clear_w), new_pos

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
            return self._paint(prompt, buf, new_pos, 0), new_pos
        return self._paint(prompt, buf, pos, 0), pos

    def _paint(self, prompt: str, buf: List[str], pos: int, clear_width: int) -> int:
        text = "".join(buf)
        total_w = text_width(prompt) + text_width(text)
        wipe = max(clear_width, total_w)
        self._console.write("\r" + " " * wipe + "\r")
        self._console.write(prompt + text)
        after = text_width(text[pos:])
        if after:
            self._console.write(f"\x1b[{after}D")
        self._console.flush()
        return total_w
