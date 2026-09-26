from django.db import models

from .base import OwnedModel


class Customer(OwnedModel):
    name = models.CharField(max_length=255)
    street = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, default="Deutschland")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    buyer_reference = models.CharField(
        max_length=255, blank=True, help_text="Leitweg-ID (XRechnung)"
    )
    rounding_increment_minutes = models.PositiveIntegerField(
        null=True, blank=True, help_text="Round time entries up to this increment"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
