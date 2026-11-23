from types import SimpleNamespace

from rest_framework.serializers import BaseSerializer

from core.models import OnSiteVisit
from core.request_helpers import request_user
from core.serializers import OnSiteVisitSerializer
from core.services.numbering import next_number

from .base import OwnedViewSet


class OnSiteVisitViewSet(OwnedViewSet[OnSiteVisit]):
    queryset = OnSiteVisit.objects.select_related("customer", "project")
    serializer_class = OnSiteVisitSerializer
    filterset_fields = ["customer", "project", "date"]
    search_fields = ["number", "customer__name", "location", "notes"]
    ordering_fields = [
        "number",
        "date",
        "customer__name",
        "project__name",
        "location",
        "arrival",
        "departure",
        "created_at",
    ]

    def perform_create(self, serializer: BaseSerializer[OnSiteVisit]) -> None:
        customer = serializer.validated_data["customer"]
        project = serializer.validated_data.get("project")
        visit = SimpleNamespace(**serializer.validated_data)
        serializer.save(
            number=next_number(
                request_user(self.request),
                "visit",
                {"customer": customer, "project": project, "visit": visit},
            )
        )
