from core.models import BankAccount

from .base import OwnedSerializer


class BankAccountSerializer(OwnedSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "id", "name", "bank_name", "account_holder", "iban", "bic",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
