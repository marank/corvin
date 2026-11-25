from typing import Any

from django.db import models

from .base import OwnedModel


class CompanyImage(OwnedModel):
    class Kind(models.TextChoices):
        LOGO_LIGHT = "logo_light", "Full logo for light backgrounds"
        LOGO_DARK = "logo_dark", "Full logo for dark backgrounds"
        ICON_LIGHT = "icon_light", "Icon for light backgrounds"
        ICON_DARK = "icon_dark", "Icon for dark backgrounds"
        ADDITIONAL = "additional", "Additional"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="company-images/")

    class Meta:
        ordering = ["kind", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "kind"],
                condition=~models.Q(kind="additional"),
                name="unique_company_image_kind_per_owner",
            ),
            models.UniqueConstraint(
                fields=["owner", "key"],
                name="unique_company_image_key_per_owner",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.kind != self.Kind.ADDITIONAL:
            self.key = self.kind
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
