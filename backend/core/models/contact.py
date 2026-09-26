from django.db import models

from .base import OwnedModel
from .customer import Customer


class Contact(OwnedModel):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="contacts"
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    is_invoice_contact = models.BooleanField(default=False)

    class Meta:
        ordering = ["last_name", "first_name"]

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.name} ({self.customer.name})"
