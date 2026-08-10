# xrk-readline

轻量 CLI 行编辑库：**C 扩展读控制台** + **Python 做编辑器**，可选纯 Python 回退。  
适合在 uvicorn / 后台线程里挂 `prompt>`，不挂钩进程级 `PyOS_Readline`（避开 pyreadline3 一类坑）。

## 架构（开源友好）

```
┌─────────────────────────────────────┐
│  Python: Readline / History / Tab   │  ← 易改、易测
├─────────────────────────────────────┤
│  C: xrk_readline._native            │  ← Win WriteConsoleW / _getwch
│     或 pure: win_console/posix      │     POSIX termios + select
└─────────────────────────────────────┘
```

| 层 | 语言 | 职责 |
|----|------|------|
| 编辑器 | Python | 缓冲、历史、补全、重绘 |
| 控制台 I/O | **C**（优先） | 原始按键、UTF-8 输出、VT、raw mode |
| 回退 | Python | 无编译器 / `XRK_READLINE_PURE=1` |

发布时用 **cibuildwheel** 打各平台 wheel；源码包在能编译的环境装 C 扩展，否则仍可用。

## 安装

```bash
pip install xrk-readline
# 开发（编 C 扩展，需本机编译器：Windows=MSVC Build Tools）
pip install -e .
# 强制纯 Python
XRK_READLINE_PURE=1 pip install -e .
```

```python
from xrk_readline import Readline, backend_name

print(backend_name())  # "native-c" 或 "pure-python"
rl = Readline()
line = rl.readline("app> ")
```

## 快捷键

←→ Home End · Backspace Delete · ↑↓ 历史 · Tab 补全 · Ctrl+C / Ctrl+D

## 拆仓发布

本目录可直接作为独立 Git 仓库根：

```text
xrk-readline/
  pyproject.toml
  setup.py              # Extension("xrk_readline._native", ...)
  LICENSE
  README.md
  src/native/_native.c
  src/xrk_readline/
```

建议 CI：`cibuildwheel` → PyPI；标签 `v0.2.0`。

## License

MIT
