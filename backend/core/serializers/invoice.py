from typing import Any, cast

from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.fields import Field

from core.models import Contact, Invoice

from .bank_account import BankAccountSerializer
from .base import NumberedSerializer
from .contact import ContactSerializer
from .invoice_line_item import InvoiceLineItemSerializer
from .payment import PaymentSerializer


class InvoiceSerializer(NumberedSerializer[Invoice]):
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
    # Whether it bills time entries (then a time report exists).
    has_time_entries = serializers.SerializerMethodField()

    def get_has_time_entries(self, obj: Invoice) -> bool:
        annotated = getattr(obj, "time_entries_billed", None)
        return bool(annotated) if annotated is not None else obj.time_entries.exists()

    def get_fields(self) -> dict[str, Field[Any, Any, Any, Any]]:
        fields = super().get_fields()
        contact_ids = cast(serializers.ManyRelatedField, fields["contact_ids"])
        # drf-stubs declare `queryset` as `QuerySet | Manager`; mypy then treats the
        # assignment as a Manager descriptor call.
        contact_ids.child_relation.queryset = self.owned(Contact.objects.all())  # type: ignore[arg-type]  # see above
        return fields

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        contacts = attrs.get("contacts", [])
        if customer and any(contact.customer_id != customer.id for contact in contacts):
            raise serializers.ValidationError(
                {"contact_ids": _("All contacts must belong to the invoice customer.")}
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
            "has_time_entries",
            "is_external",
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
            "subtotal",
            "vat_amount",
            "total",
            "sent_at",
            "is_external",
            "created_at",
            "updated_at",
        ]
