"""xrk-readline：C 控制台 + Python 行编辑（可纯 Python 回退）。"""

from .console import backend_name
from .editor import Readline

__all__ = ["Readline", "backend_name"]
__version__ = "0.2.3"
