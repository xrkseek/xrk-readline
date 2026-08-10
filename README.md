# xrk-readline

轻量 CLI 行编辑：**C 扩展读控制台** + **Python 编辑器**，无编译器时自动纯 Python 回退。  
适合在 uvicorn / 后台线程挂 `prompt>`，**不**挂钩进程级 `PyOS_Readline`（避开 pyreadline3 坑）。

仓库：[github.com/xrkseek/xrk-readline](https://github.com/xrkseek/xrk-readline)

## 安装

```bash
pip install xrk-readline
```

（发到 PyPI 后即可用上面这行。怎么发：见下方「发布到 PyPI」。）

临时从仓库装：

```bash
pip install git+https://github.com/xrkseek/xrk-readline.git
```

## 发布到 PyPI（你要当 pip 源时做这些）

正式源是 [pypi.org](https://pypi.org)（账号 **xrkseek**）。

### 1. 注册

1. 打开 https://pypi.org/account/register/ 注册并验证邮箱  
2. （建议）https://test.pypi.org 先练手  

### 2. 配置 Trusted Publisher（推荐，免 API Token）

1. 登录 PyPI → https://pypi.org/manage/account/publishing/  
2. **Add a new pending publisher**：
   - PyPI project name: `xrk-readline`
   - Owner: `xrkseek`
   - Repository: `xrk-readline`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. 在 GitHub 仓库 **Settings → Environments** 新建环境名：`pypi`

### 3. 发版

```bash
git tag v0.2.0
git push origin v0.2.0
```

或在 GitHub 创建 Release `v0.2.0`。Actions `publish` 会上传纯 Python wheel + sdist。

### 4. 验证

```bash
pip index versions xrk-readline
pip install xrk-readline==0.2.0
python -c "from xrk_readline import backend_name; print(backend_name())"
```

本地手动上传（可选）：

```bash
pip install build twine
XRK_READLINE_PURE=1 python -m build
twine upload dist/*
```

## 开发者本地

```bash
git clone git@github.com:xrkseek/xrk-readline.git
cd xrk-readline
pip install -e .
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

**Pages = 文档站**，**不是** pip 源。

| 方式 | 用户命令 |
|------|----------|
| **PyPI** | `pip install xrk-readline` |
| Git 直装 | `pip install git+https://github.com/xrkseek/xrk-readline.git` |
| Pages | 只能看网页 |

## License

MIT
