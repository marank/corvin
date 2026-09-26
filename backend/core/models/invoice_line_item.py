from decimal import Decimal

from django.db import models

from .base import OwnedModel
from .invoice import Invoice


class InvoiceLineItem(OwnedModel):
    class Unit(models.TextChoices):
        HOURS = "hours", "Hours"
        FLAT = "flat", "Flat rate"
        PIECE = "piece", "Piece"

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="items"
    )
    position = models.PositiveIntegerField(default=0)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(
        max_length=10, choices=Unit.choices, default=Unit.HOURS
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["position", "id"]

    @property
    def total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    def __str__(self):
        return self.description
