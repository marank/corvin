from rest_framework import serializers

from core.models import Contact

from .base import OwnedSerializer


class ContactSerializer(OwnedSerializer):
    owner_fk_fields = ("customer",)

    name = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id", "customer", "first_name", "last_name", "name",
            "role", "email", "phone", "is_invoice_contact",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
