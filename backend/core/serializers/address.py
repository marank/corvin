from core.models import Address

from .base import OwnedSerializer


class AddressSerializer(OwnedSerializer):
    owner_fk_fields = ("customer",)

    class Meta:
        model = Address
        fields = [
            "id",
            "customer",
            "label",
            "street",
            "postal_code",
            "city",
            "country",
            "is_primary",
            "is_invoice_address",
            "is_delivery_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
