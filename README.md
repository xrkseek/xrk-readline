# xrk-readline

轻量 CLI 行编辑：**C 扩展读控制台** + **Python 编辑器**，无编译器时自动纯 Python 回退。  
适合在 uvicorn / 后台线程挂 `prompt>`，**不**挂钩进程级 `PyOS_Readline`（避开 pyreadline3 坑）。

仓库：[github.com/sunflowermm/xrk-readline](https://github.com/sunflowermm/xrk-readline)

## 用户怎么装（推荐：从 Git 拉）

当前以 GitHub 为分发源（尚未上 PyPI 时用这个）：

```bash
# HTTPS
pip install "git+https://github.com/sunflowermm/xrk-readline.git"

# SSH
pip install "git+ssh://git@github.com/sunflowermm/xrk-readline.git"

# 钉版本 / 分支
pip install "git+https://github.com/sunflowermm/xrk-readline.git@main"
pip install "git+https://github.com/sunflowermm/xrk-readline.git@v0.2.0"

# uv
uv pip install "git+https://github.com/sunflowermm/xrk-readline.git"

# 强制纯 Python（不编 C 扩展）
XRK_READLINE_PURE=1 pip install "git+https://github.com/sunflowermm/xrk-readline.git"
```

`pyproject.toml` / `requirements.txt`：

```toml
# pyproject.toml
dependencies = [
  "xrk-readline @ git+https://github.com/sunflowermm/xrk-readline.git",
]
```

```text
# requirements.txt
xrk-readline @ git+https://github.com/sunflowermm/xrk-readline.git
```

开发者本地：

```bash
git clone git@github.com:sunflowermm/xrk-readline.git
cd xrk-readline
pip install -e .
# Windows 编 C 扩展需 MSVC Build Tools；编不过会 optional 跳过，仍可用纯 Python
```

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

### 快捷键

| 键 | 行为 |
|----|------|
| ← → Home End | 光标 |
| Backspace Delete | 删除 |
| ↑ ↓ | 历史 |
| Tab | 补全（需 `set_completer`） |
| Ctrl+C | 有内容先清空；空行 `KeyboardInterrupt` |
| Ctrl+D | 空行 `EOFError` |

## 架构

| 层 | 语言 | 职责 |
|----|------|------|
| 编辑器 | Python | 缓冲、历史、补全、重绘 |
| 控制台 I/O | C（优先） | 按键、UTF-8 输出、VT、raw |
| 回退 | Python | `XRK_READLINE_PURE=1` / 无编译器 |

## GitHub Pages？

**Pages 适合放文档站，不适合当 pip 源。**

| 方式 | 用途 |
|------|------|
| `pip install git+https://...` | **拉代码安装**（推荐现在就用） |
| [PyPI](https://pypi.org) | `pip install xrk-readline`（需你上传 wheel/sdist） |
| GitHub Pages | 说明页 / API 文档；用户仍用上面命令安装 |

本仓 `docs/` 可开 Pages 展示安装说明；安装命令仍写 `git+https://...`。

## License

MIT
