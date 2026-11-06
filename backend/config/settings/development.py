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

# Fixed key while .env still has the placeholder; production refuses to start with it.
if SECRET_KEY == "change-me":  # noqa: F405
    SECRET_KEY = "django-insecure-dev-key-only-for-runserver"

# runserver and Vite on localhost besides whatever APP_URLS lists (e.g. the Docker
# stack). The Vite proxy rewrites Origin to the backend host (see vite.config.ts);
# Django compares the port too, so :8000 is listed explicitly.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "localhost", "127.0.0.1"]  # noqa: F405
CSRF_TRUSTED_ORIGINS = [  # noqa: F405
    *CSRF_TRUSTED_ORIGINS,  # noqa: F405
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
