# xrk-readline

轻量 CLI 行编辑：**C 扩展读控制台** + **Python 编辑器**，无编译器时自动纯 Python 回退。  
适合在 uvicorn / 后台线程挂 `prompt>`，**不**挂钩进程级 `PyOS_Readline`。

- 仓库：[github.com/xrkseek/xrk-readline](https://github.com/xrkseek/xrk-readline)
- PyPI：[pypi.org/project/xrk-readline](https://pypi.org/project/xrk-readline/)
- 文档：[xrkseek.github.io/xrk-readline](https://xrkseek.github.io/xrk-readline/)

## 安装

```bash
pip install xrk-readline
```

开发：

```bash
git clone git@github.com:xrkseek/xrk-readline.git
cd xrk-readline
pip install -e .
```

发版：打 tag `v*` 或 GitHub Release → Actions `publish.yml`（Trusted Publisher，环境 `pypi`）。

## 用法

```python
from xrk_readline import Readline, backend_name

print(backend_name())  # "native-c" 或 "pure-python"

rl = Readline()
rl.set_completer(lambda text, state: ["help", "exit", "list"][state]
                 if state < 3 and ["help", "exit", "list"][state].startswith(text) else None)

try:
    line = rl.readline("app> ")
except KeyboardInterrupt:
    print("^C")
except EOFError:
    print("bye")
```

| 键 | 行为 |
|----|------|
| ← → · Home/End · Ctrl+A/E | 光标 |
| Ctrl+← / Ctrl+→ | 按词跳转 |
| Backspace · Delete | 删除 |
| Ctrl+W | 删上一词（可 Ctrl+Y 粘回） |
| Ctrl+U / Ctrl+K | 删到行首 / 行尾 |
| Ctrl+Y | 粘贴上次删除 |
| Ctrl+L | 清屏并重绘 |
| ↑ ↓ | 历史（可来回） |
| Tab | 补全（需 `set_completer`） |
| Ctrl+C | 有内容先清空；空行中断 |
| Ctrl+D | 空行结束 |

## 架构

| 层 | 语言 | 职责 |
|----|------|------|
| 编辑器 | Python | 缓冲、历史、补全、重绘 |
| 控制台 I/O | C（优先） | 按键、UTF-8 输出、VT、raw |
| 回退 | Python | `XRK_READLINE_PURE=1` / 无编译器 |

## License

MIT
