"""历史记录。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional


class History:
    def __init__(self, max_len: int = 500) -> None:
        self._max = max(1, int(max_len))
        self._items: List[str] = []
        self._cursor: Optional[int] = None  # None = 当前编辑行
        self._stash: str = ""

    def __len__(self) -> int:
        return len(self._items)

    def set_max_len(self, n: int) -> None:
        self._max = max(1, int(n))
        if len(self._items) > self._max:
            self._items = self._items[-self._max :]

    def add(self, line: str) -> None:
        text = (line or "").rstrip("\r\n")
        if not text:
            return
        if self._items and self._items[-1] == text:
            self._cursor = None
            self._stash = ""
            return
        self._items.append(text)
        if len(self._items) > self._max:
            self._items = self._items[-self._max :]
        self._cursor = None
        self._stash = ""

    def begin_nav(self, current: str) -> None:
        if self._cursor is None:
            self._stash = current

    def older(self, current: str) -> Optional[str]:
        if not self._items:
            return None
        self.begin_nav(current)
        if self._cursor is None:
            self._cursor = len(self._items) - 1
        elif self._cursor > 0:
            self._cursor -= 1
        return self._items[self._cursor]

    def newer(self, current: str) -> Optional[str]:
        if self._cursor is None:
            return None
        self.begin_nav(current)
        assert self._cursor is not None
        if self._cursor < len(self._items) - 1:
            self._cursor += 1
            return self._items[self._cursor]
        self._cursor = None
        return self._stash

    @property
    def navigating(self) -> bool:
        return self._cursor is not None

    def load(self, path: str | Path) -> None:
        p = Path(path)
        if not p.is_file():
            return
        try:
            raw = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return
        self._items = [ln for ln in raw if ln][-self._max :]
        self._cursor = None
        self._stash = ""

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(self._items) + ("\n" if self._items else ""), encoding="utf-8")
