"""历史：↑ 更旧，↓ 更新；草稿槽在条目末尾。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional


class History:
    def __init__(self, max_len: int = 500) -> None:
        self._max = max(1, int(max_len))
        self._items: List[str] = []
        self._idx: int = 0
        self._draft: str = ""
        self._nav: bool = False

    def __len__(self) -> int:
        return len(self._items)

    def set_max_len(self, n: int) -> None:
        self._max = max(1, int(n))
        if len(self._items) > self._max:
            self._items = self._items[-self._max :]
        self.reset_nav()

    def reset_nav(self) -> None:
        self._nav = False
        self._draft = ""
        self._idx = len(self._items)

    def add(self, line: str) -> None:
        text = (line or "").rstrip("\r\n")
        if text and not (self._items and self._items[-1] == text):
            self._items.append(text)
            if len(self._items) > self._max:
                self._items = self._items[-self._max :]
        self.reset_nav()

    def older(self, current: str) -> Optional[str]:
        if not self._items:
            return None
        if not self._nav:
            self._draft = current
            self._nav = True
            self._idx = len(self._items)
        if self._idx <= 0:
            return None
        self._idx -= 1
        return self._items[self._idx]

    def newer(self, current: str) -> Optional[str]:
        if not self._nav:
            return None
        if self._idx >= len(self._items):
            return None
        self._idx += 1
        if self._idx >= len(self._items):
            self._idx = len(self._items)
            return self._draft
        return self._items[self._idx]

    def load(self, path: str | Path) -> None:
        p = Path(path)
        if not p.is_file():
            return
        try:
            raw = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return
        self._items = [ln for ln in raw if ln][-self._max :]
        self.reset_nav()

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            "\n".join(self._items) + ("\n" if self._items else ""),
            encoding="utf-8",
        )
