"""Build xrk-readline: optional C extension + pure Python package."""

from __future__ import annotations

import os
import sys

from setuptools import Extension, setup

ext_modules: list[Extension] = []

if os.environ.get("XRK_READLINE_PURE", "").strip() not in ("1", "true", "yes"):
    ext_modules.append(
        Extension(
            "xrk_readline._native",
            sources=["src/native/_native.c"],
            optional=True,  # 无编译器时跳过，走纯 Python
        )
    )

setup(
    ext_modules=ext_modules,
    # Windows 上尽量用 MSVC；失败则 optional=True 仍可安装纯 Python
    zip_safe=False,
)
