import os
import sys

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# WeasyPrint on Windows needs the GTK/Pango runtime (installed via MSYS2).
# Registers the DLL directory for this process only — no global PATH change.
if sys.platform == "win32":
    for _dll_dir in (
        env("MSYS2_BIN_DIR", default=""),
        r"C:\msys64\ucrt64\bin",
        r"C:\msys64\mingw64\bin",
    ):
        if _dll_dir and os.path.isdir(_dll_dir):
            os.add_dll_directory(_dll_dir)
            break

# Dev frontend runs on vite :5173 and proxies /api + /media — same origin,
# so CSRF/CORS stay simple. Trusted origins anyway for flexibility.
CSRF_TRUSTED_ORIGINS = env(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)
