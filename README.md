# xrk-readline

轻量 CLI 行编辑：**C 扩展读控制台** + **Python 编辑器**，无编译器时自动纯 Python 回退。  
适合在 uvicorn / 后台线程挂 `prompt>`，**不**挂钩进程级 `PyOS_Readline`（避开 pyreadline3 坑）。

仓库：[github.com/sunflowermm/xrk-readline](https://github.com/sunflowermm/xrk-readline)

## 安装

### PyPI（正式 pip 源，发布后）

```bash
pip install xrk-readline
# 或
uv pip install xrk-readline
```

```toml
# pyproject.toml
dependencies = ["xrk-readline>=0.2.0"]
```

### 还没上 PyPI 时：从 Git 拉

```bash
pip install "git+https://github.com/sunflowermm/xrk-readline.git"
```

## 发布到 PyPI（你要当 pip 源时做这些）

Pages / GitHub 本身**不能**当 `pip install 包名` 的官方源。正式源是 [pypi.org](https://pypi.org)。

### 1. 注册

1. 打开 https://pypi.org/account/register/ 注册并验证邮箱  
2. （建议）https://test.pypi.org 先练手  

### 2. 配置 Trusted Publisher（推荐，免 API Token）

1. 登录 PyPI → **Your projects** → **Publishing** / 或首次上传前用  
   https://pypi.org/manage/account/publishing/  
2. **Add a new pending publisher**：
   - PyPI project name: `xrk-readline`
   - Owner: `sunflowermm`
   - Repository: `xrk-readline`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. 在 GitHub 仓库 **Settings → Environments** 新建环境名：`pypi`（可加审批）

### 3. 发版

```bash
# 版本与 pyproject.toml 的 version 一致，例如 0.2.0
git tag v0.2.0
git push origin v0.2.0
```

或在 GitHub 点 **Release** 创建 `v0.2.0`。  
Actions 里的 `publish` 会构建 **纯 Python wheel + sdist** 并上传 PyPI。  
（C 扩展留给本机有编译器时从源码编；首发先保证全平台 `pip install` 能装上。）

### 4. 验证

```bash
pip index versions xrk-readline
pip install xrk-readline==0.2.0
python -c "from xrk_readline import backend_name; print(backend_name())"
```

本地手动上传（不推荐，不如 Trusted Publisher）：

```bash
pip install build twine
XRK_READLINE_PURE=1 python -m build
twine upload dist/*   # 需 PyPI API token
```

## 开发者本地

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

**Pages = 文档站**（安装说明页），**不是** pip 源。

| 方式 | 用户命令 |
|------|----------|
| **PyPI** | `pip install xrk-readline` |
| Git 直装 | `pip install "git+https://github.com/sunflowermm/xrk-readline.git"` |
| Pages | 只能看网页，不能当包索引 |
## License

MIT
