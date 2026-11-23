from decimal import Decimal

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from .bank_account import BankAccount
from .base import OwnedModel
from .contact import Contact
from .customer import Customer
from .document_template import DocumentTemplate
from .project import Project
from .support_contract import SupportContract


class Invoice(OwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    class EInvoiceFormat(models.TextChoices):
        NONE = "none", "None"
        ZUGFERD = "zugferd", "ZUGFeRD (PDF/A-3 + XML)"
        XRECHNUNG = "xrechnung", "XRechnung (XML only)"

    number = models.CharField(max_length=50, blank=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices")
    contacts = models.ManyToManyField(Contact, blank=True, related_name="invoices")
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        SupportContract,
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    issue_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=19)
    currency = models.CharField(max_length=3, default="EUR")
    e_invoice_format = models.CharField(
        max_length=15,
        choices=EInvoiceFormat.choices,
        default=EInvoiceFormat.NONE,
    )
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    bank_account_override = models.ForeignKey(
        "BankAccount",
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    documents = GenericRelation(
        "DocumentArchive", content_type_field="content_type", object_id_field="object_id"
    )

    class Meta:
        ordering = ["-issue_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "number"],
                condition=~models.Q(number=""),
                name="unique_invoice_number_per_owner",
            )
        ]

    @property
    def bank_account(self) -> BankAccount | None:
        if self.bank_account_override_id:
            return self.bank_account_override
        if self.customer.bank_account_id:
            return self.customer.bank_account
        company = getattr(self.owner, "company_settings", None)
        return company.default_bank_account if company else None

    @property
    def amount_paid(self) -> Decimal:
        return sum((p.amount for p in self.payments.all()), Decimal(0))

    @property
    def remaining(self) -> Decimal:
        return self.total - self.amount_paid

    @property
    def partially_paid(self) -> bool:
        return self.amount_paid > 0 and self.remaining > 0

    def recalc_totals(self) -> None:
        self.subtotal = sum(i.total for i in self.items.all())
        self.vat_amount = (self.subtotal * self.vat_rate / 100).quantize(Decimal("0.01"))
        self.total = self.subtotal + self.vat_amount
        self.save(update_fields=["subtotal", "vat_amount", "total", "updated_at"])

    def __str__(self) -> str:
        return f"{self.number} ({self.customer.name})"
