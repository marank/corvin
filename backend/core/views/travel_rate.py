from core.models import TravelRate
from core.serializers import TravelRateSerializer

from .base import OwnedViewSet


class TravelRateViewSet(OwnedViewSet[TravelRate]):
    queryset = TravelRate.objects.select_related("customer", "project")
    serializer_class = TravelRateSerializer
    filterset_fields = {"customer": ["exact", "isnull"], "project": ["exact", "isnull"]}
    ordering_fields = ["valid_from", "amount"]
