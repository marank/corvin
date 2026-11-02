from types import SimpleNamespace

from core.models import OnSiteVisit
from core.serializers import OnSiteVisitSerializer
from core.services.numbering import next_number

from .base import OwnedViewSet


class OnSiteVisitViewSet(OwnedViewSet):
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

    def perform_create(self, serializer):
        customer = serializer.validated_data["customer"]
        project = serializer.validated_data.get("project")
        visit = SimpleNamespace(**serializer.validated_data)
        serializer.save(
            number=next_number(
                self.request.user,
                "visit",
                {"customer": customer, "project": project, "visit": visit},
            )
        )
