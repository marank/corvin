from core.models import HourlyRate
from core.serializers import HourlyRateSerializer

from .base import OwnedViewSet


class HourlyRateViewSet(OwnedViewSet):
    queryset = HourlyRate.objects.select_related("customer", "project")
    serializer_class = HourlyRateSerializer
    filterset_fields = {"customer": ["exact", "isnull"], "project": ["exact", "isnull"]}
    ordering_fields = ["valid_from", "amount"]
