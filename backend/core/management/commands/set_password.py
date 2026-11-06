from getpass import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from core.services.admin_user import set_password


class Command(BaseCommand):
    help = "Set a user's password exactly as typed (unlike changepassword: no password rules)."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, username, **options):
        if not User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' does not exist.")
        password = getpass("Password: ")
        if not password:
            raise CommandError("Password is empty, nothing changed.")
        if getpass("Password (again): ") != password:
            raise CommandError("Passwords do not match, nothing changed.")
        set_password(username, password)
        self.stdout.write(f"Password for '{username}' changed.")
