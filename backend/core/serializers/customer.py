from rest_framework import serializers

from core.models import Customer

from .base import OwnedSerializer


class CustomerSerializer(OwnedSerializer):
    project_count = serializers.IntegerField(read_only=True)
    uninvoiced_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Customer
        fields = [
            "id", "name", "street", "postal_code", "city", "country",
            "email", "phone", "notes", "buyer_reference",
            "rounding_increment_minutes", "is_active",
            "project_count", "uninvoiced_hours",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
