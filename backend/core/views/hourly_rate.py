from core.models import HourlyRate
from core.serializers import HourlyRateSerializer

from .base import OwnedViewSet


class HourlyRateViewSet(OwnedViewSet):
    queryset = HourlyRate.objects.select_related("customer", "project")
    serializer_class = HourlyRateSerializer
    filterset_fields = ["customer", "project"]
    ordering_fields = ["valid_from", "amount"]
