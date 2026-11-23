"""Nightly backups into ``settings.BACKUP_DIR``, run by the ``backup`` job of the worker.

Each run writes ``<database>-<UTC timestamp>.dump`` (``pg_dump``, PostgreSQL's custom format;
restore with ``pg_restore``) and ``media-<UTC timestamp>.tar.gz`` (uploads and the archived
invoice PDFs/XML), then deletes backups older than ``BACKUP_KEEP_DAYS`` days. Files are
written under a ``.partial`` name first, so a failed run never looks like a valid backup.
"""

import logging
import os
import subprocess
import tarfile
import time
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)

# A file that is still ".partial" after this long belongs to a run that died.
STALE_PARTIAL_SECONDS = 3600


class BackupError(Exception):
    """pg_dump failed; the message is its error output."""


def available() -> bool:
    """Dumps need PostgreSQL; native development on SQLite has none."""
    return connection.vendor == "postgresql"


def backup() -> list[Path]:
    """Dump the database and the uploads into ``BACKUP_DIR`` now; return the new files."""
    directory = Path(settings.BACKUP_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = f"{timezone.now():%Y%m%dT%H%M%SZ}"
    files = [dump_database(directory, stamp), archive_media(directory, stamp)]
    remove_old_backups(directory)
    return files


def dump_database(directory: Path, stamp: str) -> Path:
    database = connection.settings_dict
    target = directory / f"{database['NAME']}-{stamp}.dump"
    partial = target.with_name(f"{target.name}.partial")
    environment = {
        **os.environ,
        "PGHOST": str(database["HOST"]),
        "PGPORT": str(database["PORT"]),
        "PGDATABASE": str(database["NAME"]),
        "PGUSER": str(database["USER"]),
        "PGPASSWORD": str(database["PASSWORD"]),
    }
    try:
        # S603/S607: fixed argument list; pg_dump comes from the image's postgresql-client.
        # umask: the dump holds every password hash and personal record.
        subprocess.run(  # noqa: S603
            ["pg_dump", "--format=custom", f"--file={partial}"],  # noqa: S607
            env=environment,
            umask=0o077,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        partial.unlink(missing_ok=True)
        message = error.stderr.strip() or f"pg_dump exited with {error.returncode}"
        raise BackupError(message) from error
    partial.rename(target)
    logger.info("Database dumped to %s", target)
    return target


def archive_media(directory: Path, stamp: str) -> Path:
    target = directory / f"media-{stamp}.tar.gz"
    partial = target.with_name(f"{target.name}.partial")
    media = Path(settings.MEDIA_ROOT)
    try:
        # Opened with 0600 like the dump: archived invoices hold customer data.
        descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "wb") as file, tarfile.open(fileobj=file, mode="w:gz") as tar:
            if media.is_dir():
                tar.add(media, arcname=".")
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.rename(target)
    logger.info("Uploads archived to %s", target)
    return target


def remove_old_backups(directory: Path) -> list[Path]:
    """Delete backups older than ``BACKUP_KEEP_DAYS`` days and leftovers of failed runs."""
    now = time.time()
    keep_after = now - settings.BACKUP_KEEP_DAYS * 86400
    removed = [
        path
        for pattern in ("*.dump", "*.tar.gz")
        for path in directory.glob(pattern)
        if path.stat().st_mtime < keep_after
    ]
    removed += [
        path
        for path in directory.glob("*.partial")
        if path.stat().st_mtime < now - STALE_PARTIAL_SECONDS
    ]
    for path in removed:
        path.unlink()
        logger.info("Removed old backup %s", path)
    return sorted(removed)
