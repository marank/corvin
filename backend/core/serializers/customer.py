from rest_framework import serializers

from core.models import Customer

from .address import AddressSerializer
from .base import OwnedSerializer


class CustomerSerializer(OwnedSerializer):
    owner_fk_fields = ("bank_account",)

    project_count = serializers.IntegerField(read_only=True)
    uninvoiced_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    addresses = AddressSerializer(many=True, read_only=True)
    primary_address = AddressSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "number", "name", "email", "phone", "website", "vat_id",
            "notes", "buyer_reference",
            "rounding_increment_minutes", "payment_terms_days", "bank_account", "is_active",
            "project_count", "uninvoiced_hours",
            "addresses", "primary_address",
            "created_at", "updated_at",
        ]
        read_only_fields = ["number", "created_at", "updated_at"]
