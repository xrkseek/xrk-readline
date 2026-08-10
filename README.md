# xrk-readline

轻量 CLI 行编辑：可选 C 扩展 + Python 编辑器（无编译器时纯 Python）。

- https://github.com/xrkseek/xrk-readline
- https://pypi.org/project/xrk-readline/

## 安装

```bash
pip install xrk-readline
```

## 用法

```python
from xrk_readline import Readline, backend_name

rl = Readline()
line = rl.readline("app> ")
```

| 键 | 行为 |
|----|------|
| ← → Home End · Ctrl+A/E | 光标 |
| Ctrl+← / Ctrl+→ | 按词 |
| ↑ ↓ | 历史（CSI / SS3 / Win 扩展键） |
| Tab | 补全 |
| Ctrl+C / Ctrl+D | 清空或中断 / 空行 EOF |

## 发版

打 tag `v*` → Actions `publish.yml` → PyPI（Trusted Publisher，环境 `pypi`）。

## License

MIT
