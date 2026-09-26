from copy import deepcopy

from django.conf import settings
from django.db import models

from .base import UuidModel

NUMBERING_SCHEMES = {
    "customer": {"format": "K-{counter:4}", "scope": [], "start": 1000},
    "project": {"format": "P-{counter:4}", "scope": ["customer"], "start": 1},
    "invoice": {"format": "RE-{year:4}-{counter:4}", "scope": ["year"], "start": 1},
    "contract": {"format": "V-{counter:4}", "scope": [], "start": 1},
    "visit": {"format": "B-{year:4}-{counter:4}", "scope": ["year"], "start": 1},
    "task": {"format": "T-{counter:4}", "scope": ["project"], "start": 1},
}


def default_numbering_schemes():
    return deepcopy(NUMBERING_SCHEMES)


class CompanySettings(UuidModel):
    """Per-user company profile used on invoices."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="company_settings",
    )
    company_name = models.CharField(max_length=255, blank=True)
    street = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, default="Deutschland")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    vat_id = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=34, blank=True)
    bic = models.CharField(max_length=11, blank=True)
    default_bank_account = models.ForeignKey(
        "BankAccount", on_delete=models.SET_NULL, related_name="default_for_companies",
        null=True, blank=True,
    )
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)
    default_vat_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=19
    )
    vat_enabled = models.BooleanField(default=True)
    numbering_schemes = models.JSONField(default=default_numbering_schemes)
    payment_terms_days = models.PositiveIntegerField(default=14)
    locale = models.CharField(max_length=5, default="de")
    date_format = models.CharField(max_length=50, default="DD.MM.YYYY")
    time_format = models.CharField(max_length=50, default="HH:mm")
    decimal_separator = models.CharField(max_length=1, default=",")
    thousands_separator = models.CharField(max_length=1, default=".")
    currency = models.CharField(max_length=3, default="EUR")
    currency_display = models.CharField(
        max_length=10, choices=[("symbol", "Symbol"), ("code", "Code")],
        default="symbol",
    )
    currency_position = models.CharField(
        max_length=10, choices=[("before", "Before"), ("after", "After")],
        default="after",
    )
    currency_space = models.BooleanField(default=True)
    theme = models.CharField(max_length=10, default="light")

    def __str__(self):
        return f"Settings of {self.user}"
