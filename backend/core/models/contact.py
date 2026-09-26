from django.db import models

from .base import OwnedModel
from .customer import Customer


class Contact(OwnedModel):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="contacts"
    )
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.customer.name})"
