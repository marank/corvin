from core.models import OnSiteVisit
from core.serializers import OnSiteVisitSerializer

from .base import OwnedViewSet


class OnSiteVisitViewSet(OwnedViewSet):
    queryset = OnSiteVisit.objects.select_related("customer", "project")
    serializer_class = OnSiteVisitSerializer
    filterset_fields = ["customer", "project", "date"]
    search_fields = ["customer__name", "location", "notes"]
    ordering_fields = ["date", "created_at"]
