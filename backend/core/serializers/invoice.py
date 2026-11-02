from rest_framework import serializers

from core.models import Contact, Invoice

from .bank_account import BankAccountSerializer
from .base import OwnedSerializer
from .contact import ContactSerializer
from .invoice_line_item import InvoiceLineItemSerializer
from .payment import PaymentSerializer


class InvoiceSerializer(OwnedSerializer):
    owner_fk_fields = (
        "customer",
        "project",
        "contract",
        "template",
        "bank_account_override",
    )

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    contract_name = serializers.CharField(source="contract.name", read_only=True, default=None)
    contacts = ContactSerializer(many=True, read_only=True)
    bank_account = BankAccountSerializer(read_only=True)
    contact_ids = serializers.PrimaryKeyRelatedField(
        source="contacts",
        many=True,
        queryset=Contact.objects.all(),
        required=False,
        write_only=True,
    )
    items = InvoiceLineItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    partially_paid = serializers.BooleanField(read_only=True)

    def get_fields(self):
        fields = super().get_fields()
        fields["contact_ids"].child_relation.queryset = Contact.objects.filter(
            owner=self.context["request"].user
        )
        return fields

    def validate(self, attrs):
        attrs = super().validate(attrs)
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        contacts = attrs.get("contacts", [])
        if customer and any(contact.customer_id != customer.id for contact in contacts):
            raise serializers.ValidationError(
                {"contact_ids": "All contacts must belong to the invoice customer."}
            )
        return attrs

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "customer",
            "customer_name",
            "contacts",
            "contact_ids",
            "project",
            "project_name",
            "contract",
            "contract_name",
            "issue_date",
            "due_date",
            "status",
            "vat_rate",
            "currency",
            "e_invoice_format",
            "notes",
            "subtotal",
            "vat_amount",
            "total",
            "amount_paid",
            "remaining",
            "partially_paid",
            "sent_at",
            "template",
            "bank_account_override",
            "bank_account",
            "items",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "number",
            "subtotal",
            "vat_amount",
            "total",
            "sent_at",
            "created_at",
            "updated_at",
        ]
