from __future__ import annotations

import os

from setuptools import Extension, setup

ext_modules: list[Extension] = []
if os.environ.get("XRK_READLINE_PURE", "").strip() not in ("1", "true", "yes"):
    ext_modules.append(
        Extension(
            "xrk_readline._native",
            sources=["src/native/_native.c"],
            optional=True,
        )
    )

setup(ext_modules=ext_modules, zip_safe=False)
