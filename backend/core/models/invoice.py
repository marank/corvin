from decimal import Decimal

from django.db import models

from .base import OwnedModel
from .customer import Customer
from .invoice_template import InvoiceTemplate
from .project import Project
from .support_contract import SupportContract


class Invoice(OwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    class EInvoiceFormat(models.TextChoices):
        NONE = "none", "None"
        ZUGFERD = "zugferd", "ZUGFeRD (PDF/A-3 + XML)"
        XRECHNUNG = "xrechnung", "XRechnung (XML only)"

    number = models.CharField(max_length=50)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="invoices"
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, related_name="invoices",
        null=True, blank=True,
    )
    contract = models.ForeignKey(
        SupportContract, on_delete=models.SET_NULL, related_name="invoices",
        null=True, blank=True,
    )
    issue_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFT
    )
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=19)
    currency = models.CharField(max_length=3, default="EUR")
    e_invoice_format = models.CharField(
        max_length=15, choices=EInvoiceFormat.choices,
        default=EInvoiceFormat.NONE,
    )
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    template = models.ForeignKey(
        InvoiceTemplate, on_delete=models.SET_NULL, related_name="invoices",
        null=True, blank=True,
    )

    class Meta:
        ordering = ["-issue_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "number"], name="unique_invoice_number_per_owner"
            )
        ]

    @property
    def amount_paid(self):
        return sum(p.amount for p in self.payments.all())

    @property
    def remaining(self):
        return self.total - self.amount_paid

    @property
    def partially_paid(self):
        return self.amount_paid > 0 and self.remaining > 0

    def recalc_totals(self):
        self.subtotal = sum(i.total for i in self.items.all())
        self.vat_amount = (self.subtotal * self.vat_rate / 100).quantize(
            Decimal("0.01")
        )
        self.total = self.subtotal + self.vat_amount
        self.save(update_fields=["subtotal", "vat_amount", "total", "updated_at"])

    def __str__(self):
        return f"{self.number} ({self.customer.name})"
