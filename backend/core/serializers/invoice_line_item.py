from rest_framework import serializers

from core.models import InvoiceLineItem

from .base import OwnedSerializer


class InvoiceLineItemSerializer(OwnedSerializer):
    total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = InvoiceLineItem
        fields = [
            "id", "invoice", "position", "description", "quantity",
            "unit", "unit_price", "total", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
