from core.models import BankAccount
from core.serializers import BankAccountSerializer

from .base import OwnedViewSet


class BankAccountViewSet(OwnedViewSet[BankAccount]):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer
    search_fields = ["name", "bank_name", "account_holder", "iban", "bic"]
    ordering_fields = ["name", "bank_name", "created_at"]
