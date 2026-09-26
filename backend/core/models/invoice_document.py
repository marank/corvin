from django.db import models

from .base import OwnedModel
from .invoice import Invoice


class InvoiceDocument(OwnedModel):
    """Immutable archived document written at invoice finalize (GoBD)."""

    class Kind(models.TextChoices):
        PDF = "pdf", "PDF"
        XML = "xml", "XML (e-invoice)"

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(upload_to="invoice_docs/%Y/%m/")
    sha256 = models.CharField(max_length=64)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "kind"], name="unique_doc_kind_per_invoice"
            )
        ]

    def __str__(self):
        return f"{self.invoice.number} ({self.kind})"
