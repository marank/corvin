from django.db import models

from .base import OwnedModel
from .invoice import Invoice


class Payment(OwnedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        invoice = self.invoice
        if invoice.amount_paid >= invoice.total and invoice.total > 0:
            invoice.status = Invoice.Status.PAID
            invoice.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return f"{self.amount} on {self.date}"
