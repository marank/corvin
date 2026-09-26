from core.models import Payment
from core.serializers import PaymentSerializer

from .base import OwnedViewSet


class PaymentViewSet(OwnedViewSet):
    queryset = Payment.objects.select_related("invoice")
    serializer_class = PaymentSerializer
    filterset_fields = ["invoice"]
    ordering_fields = ["date", "amount"]
