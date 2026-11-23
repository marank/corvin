from core.models import Payment

from .base import OwnedSerializer


class PaymentSerializer(OwnedSerializer[Payment]):
    owner_fk_fields = ("invoice",)

    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "date",
            "amount",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
