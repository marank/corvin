from django.conf import settings
from django.db import models


class NumberSequence(models.Model):
    """Per-owner invoice number sequence: PREFIX-YYYY-NNNN."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    prefix = models.CharField(max_length=20, default="RE")
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "year", "prefix"],
                name="unique_sequence_per_owner_year_prefix",
            )
        ]
