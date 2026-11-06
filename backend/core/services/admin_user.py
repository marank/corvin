"""First administrator from ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD."""

from django.contrib.auth.models import User
from django.db import transaction

from core.models import CompanySettings


def ensure_admin(username: str, email: str, password: str) -> str:
    """Create the superuser with exactly the given password unless it exists.

    Never touches an existing user. Returns what happened as a short message for the log.
    """
    if not username or not password:
        return "ADMIN_USERNAME or ADMIN_PASSWORD is empty, no administrator created."
    if User.objects.filter(username=username).exists():
        return f"Administrator '{username}' exists."
    with transaction.atomic():
        user = User.objects.create_superuser(username, email, password)
        CompanySettings.objects.get_or_create(user=user)
    return f"Administrator '{username}' created."


def set_password(username: str, password: str) -> None:
    """Set the password exactly as given, without Django's password rules."""
    user = User.objects.get(username=username)
    user.set_password(password)
    user.save(update_fields=["password"])
