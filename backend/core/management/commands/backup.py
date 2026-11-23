"""Back up the database and the uploads now, e.g. before an update.

    docker compose exec worker python manage.py backup

The worker does the same every night at ``BACKUP_TIME`` (``core.tasks.backup``).
"""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.services import backups


class Command(BaseCommand):
    help = "Dump the database and the uploads into BACKUP_DIR now; delete old backups."

    def handle(self, *args: Any, **options: Any) -> None:
        if not backups.available():
            raise CommandError("Backups need PostgreSQL; with SQLite copy the database file.")
        if not settings.BACKUP_DIR:
            raise CommandError("BACKUP_DIR is not set.")
        try:
            files = backups.backup()
        except backups.BackupError as error:
            raise CommandError(f"pg_dump failed: {error}") from error
        for path in files:
            self.stdout.write(f"Written {path}")
