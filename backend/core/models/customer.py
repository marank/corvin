from typing import TYPE_CHECKING

from django.db import models
from django.utils.functional import cached_property

from .base import OwnedModel

if TYPE_CHECKING:
    from .address import Address


class Customer(OwnedModel):
    number = models.CharField(max_length=50, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    vat_id = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    buyer_reference = models.CharField(
        max_length=255, blank=True, help_text="Leitweg-ID (XRechnung)"
    )
    rounding_increment_minutes = models.PositiveIntegerField(
        null=True, blank=True, help_text="Round time entries up to this increment"
    )
    payment_terms_days = models.PositiveIntegerField(null=True, blank=True)
    bank_account = models.ForeignKey(
        "BankAccount",
        on_delete=models.SET_NULL,
        related_name="customers",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "number"],
                condition=~models.Q(number=""),
                name="unique_customer_number_per_owner",
            )
        ]

    @property
    def primary_address(self) -> Address | None:
        return self.addresses.filter(is_primary=True).first() or self.addresses.first()

    @cached_property
    def invoice_address(self) -> Address | None:
        """Where invoices go: the address marked for invoices, else the primary one."""
        addresses = list(self.addresses.all())  # primary first (Address.Meta.ordering)
        return next((a for a in addresses if a.is_invoice_address), None) or next(
            iter(addresses), None
        )

    # Convenience proxies for invoice templates / e-invoicing —
    # resolve to the invoice address.
    @property
    def street(self) -> str:
        return self.invoice_address.street if self.invoice_address else ""

    @property
    def postal_code(self) -> str:
        return self.invoice_address.postal_code if self.invoice_address else ""

    @property
    def city(self) -> str:
        return self.invoice_address.city if self.invoice_address else ""

    @property
    def country(self) -> str:
        return self.invoice_address.country if self.invoice_address else ""

    def __str__(self) -> str:
        return self.name
