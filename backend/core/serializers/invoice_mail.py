from rest_framework import serializers

from core.models import InvoiceMail


class InvoiceMailSerializer(serializers.ModelSerializer[InvoiceMail]):
    """A mail in an invoice's history; the HTML only in the detail (InvoiceMailDetail)."""

    class Meta:
        model = InvoiceMail
        fields = [
            "id",
            "kind",
            "to",
            "subject",
            "attachments",
            "status",
            "sent_at",
            "error",
            "created_at",
        ]
        read_only_fields = fields


class InvoiceMailDetailSerializer(InvoiceMailSerializer):
    class Meta(InvoiceMailSerializer.Meta):
        fields = [*InvoiceMailSerializer.Meta.fields, "html"]
        read_only_fields = fields
