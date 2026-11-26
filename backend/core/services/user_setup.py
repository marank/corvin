"""What a new user starts with: company settings and the default templates, assigned."""

from django.contrib.auth.models import User
from django.db import transaction

from core.models import CompanySettings

from .mail_templates import ensure_mail_templates
from .templates import ensure_default_template


@transaction.atomic
def set_up_user(user: User) -> None:
    CompanySettings.objects.get_or_create(user=user)
    ensure_default_template(user)
    ensure_mail_templates(user)
