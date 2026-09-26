from django.conf import settings
from django.db import models

from .base import UuidModel


class NumberSequence(UuidModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    entity = models.CharField(max_length=30, default="invoice")
    scope_key = models.CharField(max_length=100, blank=True, default="global")
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "entity", "scope_key"],
                name="unique_number_sequence_scope",
            )
        ]
