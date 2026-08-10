# xrk-readline

轻量 CLI 行编辑：可选 C 控制台扩展 + Python 编辑器（无编译器时纯 Python）。

- 源码：https://github.com/xrkseek/xrk-readline
- PyPI：https://pypi.org/project/xrk-readline/

## 安装

```bash
pip install xrk-readline
```

## 用法

```python
from xrk_readline import Readline, backend_name

rl = Readline()
rl.set_completer(
    lambda text, state: next(
        (w for i, w in enumerate(["help", "exit", "list"]) if w.startswith(text) and i == state),
        None,
    )
)
line = rl.readline("app> ")
```

| 键 | 行为 |
|----|------|
| ← → Home End · Ctrl+A/E | 光标 |
| Ctrl+← / Ctrl+→ | 按词移动 |
| Backspace · Delete | 删除 |
| Ctrl+W · Ctrl+U · Ctrl+K | 删词 / 删到行首 / 删到行尾 |
| Ctrl+Y | 粘贴上次删除 |
| Ctrl+L | 清屏重绘 |
| ↑ ↓ | 历史 |
| Tab | 补全 |
| Ctrl+C | 清空或中断 |
| Ctrl+D | 空行结束输入 |

## 开发与发版

```bash
git clone git@github.com:xrkseek/xrk-readline.git
cd xrk-readline
pip install -e .
```

打 tag `v*` 或发 GitHub Release，由 Actions `publish.yml` 上传 PyPI（Trusted Publisher，环境 `pypi`）。

## License

MIT
