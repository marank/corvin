from django.core.management.base import BaseCommand

from config.settings.base import env
from core.services.admin_user import ensure_admin


class Command(BaseCommand):
    help = "Create the administrator from ADMIN_USERNAME/ADMIN_EMAIL/ADMIN_PASSWORD if missing."

    def handle(self, *args, **options):
        message = ensure_admin(
            env("ADMIN_USERNAME", default="admin"),
            env("ADMIN_EMAIL", default=""),
            env("ADMIN_PASSWORD", default=""),
        )
        self.stdout.write(message)
