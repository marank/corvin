from typing import Any

from django.core.management.base import BaseCommand

from config.env import env_str
from core.services.admin_user import ensure_admin


class Command(BaseCommand):
    help = "Create the administrator from ADMIN_USERNAME/ADMIN_EMAIL/ADMIN_PASSWORD if missing."

    def handle(self, *args: Any, **options: Any) -> None:
        message = ensure_admin(
            env_str("ADMIN_USERNAME", "admin"),
            env_str("ADMIN_EMAIL", ""),
            env_str("ADMIN_PASSWORD", ""),
        )
        self.stdout.write(message)
