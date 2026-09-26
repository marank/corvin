from rest_framework import serializers

from core.models import Invoice

from .base import OwnedSerializer
from .invoice_line_item import InvoiceLineItemSerializer
from .payment import PaymentSerializer


class InvoiceSerializer(OwnedSerializer):
    owner_fk_fields = ("customer", "project", "contract", "template")

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    contract_name = serializers.CharField(
        source="contract.name", read_only=True, default=None
    )
    items = InvoiceLineItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    amount_paid = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    remaining = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    partially_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "customer", "customer_name",
            "project", "project_name", "contract", "contract_name",
            "issue_date", "due_date", "status",
            "vat_rate", "currency", "e_invoice_format", "notes",
            "subtotal", "vat_amount", "total",
            "amount_paid", "remaining", "partially_paid",
            "sent_at", "template", "items", "payments",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "number", "subtotal", "vat_amount", "total",
            "sent_at", "created_at", "updated_at",
        ]
