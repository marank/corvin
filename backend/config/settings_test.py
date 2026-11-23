"""Settings for the tests: the development settings, independent of a developer's .env."""

import os

os.environ.setdefault("DEBUG", "true")  # set before .env is read, so .env cannot turn it off

from .settings import *  # noqa: F403  (SQLite natively, PostgreSQL via DB_TYPE in CI)
