from django.conf import settings
from django.db import models


class CompanySettings(models.Model):
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
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)
    default_vat_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=19
    )
    invoice_prefix = models.CharField(max_length=20, default="RE")
    payment_terms_days = models.PositiveIntegerField(default=14)
    locale = models.CharField(max_length=5, default="de")
    theme = models.CharField(max_length=10, default="light")

    def __str__(self):
        return f"Settings of {self.user}"
