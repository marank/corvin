from getpass import getpass
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.services.admin_user import set_password


class Command(BaseCommand):
    help = "Set a user's password exactly as typed (unlike changepassword: no password rules)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("username")

    def handle(self, *args: Any, username: str, **options: Any) -> None:
        if not User.objects.filter(username__iexact=username).exists():
            raise CommandError(f"User '{username}' does not exist.")
        password = getpass("Password: ")
        if not password:
            raise CommandError("Password is empty, nothing changed.")
        if getpass("Password (again): ") != password:
            raise CommandError("Passwords do not match, nothing changed.")
        set_password(username, password)
        self.stdout.write(f"Password for '{username}' changed.")
