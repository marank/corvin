from django.db import models

from .base import OwnedModel
from .customer import Customer


class Address(OwnedModel):
    """A postal address belonging to a customer (multiple allowed)."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=100, blank=True, help_text="e.g. Headquarters, Billing")
    street = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, default="Deutschland")
    is_primary = models.BooleanField(default=False)
    is_invoice_address = models.BooleanField(default=False)
    is_delivery_address = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "label", "city"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            self.customer.addresses.exclude(pk=self.pk).filter(is_primary=True).update(
                is_primary=False
            )

    def __str__(self):
        parts = ", ".join(p for p in (self.street, f"{self.postal_code} {self.city}".strip()) if p)
        return f"{self.label or 'Address'}: {parts}"
