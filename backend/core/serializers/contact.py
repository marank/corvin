from core.models import Contact

from .base import OwnedSerializer


class ContactSerializer(OwnedSerializer):
    owner_fk_fields = ("customer",)

    class Meta:
        model = Contact
        fields = [
            "id", "customer", "name", "role", "email", "phone",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
