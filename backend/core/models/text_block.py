from django.core.validators import RegexValidator
from django.db import models

from .base import OwnedModel


class TextBlock(OwnedModel):
    name = models.CharField(max_length=255)
    key = models.CharField(
        max_length=100,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]*$")],
    )
    content = models.TextField()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "key"],
                name="unique_text_block_key_per_owner",
            )
        ]

    def __str__(self):
        return self.name
