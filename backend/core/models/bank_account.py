from django.db import models

from .base import OwnedModel


class BankAccount(OwnedModel):
    name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255, blank=True)
    account_holder = models.CharField(max_length=255)
    iban = models.CharField(max_length=34)
    bic = models.CharField(max_length=11, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "bank_name"]

    def __str__(self) -> str:
        return self.name
