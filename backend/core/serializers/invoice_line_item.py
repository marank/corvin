from rest_framework import serializers

from core.models import InvoiceLineItem, TimeEntry

from .base import OwnedSerializer


class InvoiceLineItemSerializer(OwnedSerializer[InvoiceLineItem]):
    owner_fk_fields = ("invoice",)

    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    # The time entries this line bills (set by invoicing, not through this API).
    time_entry_ids: serializers.PrimaryKeyRelatedField[TimeEntry] = (
        serializers.PrimaryKeyRelatedField(source="time_entries", many=True, read_only=True)
    )

    class Meta:
        model = InvoiceLineItem
        fields = [
            "id",
            "invoice",
            "position",
            "description",
            "quantity",
            "unit",
            "unit_price",
            "total",
            "time_entry_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"position": {"required": False}}
