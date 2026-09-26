from types import SimpleNamespace

from core.models import Project
from core.serializers import ProjectSerializer
from core.services.numbering import next_number

from .base import OwnedViewSet


class ProjectViewSet(OwnedViewSet):
    queryset = Project.objects.select_related("customer")
    serializer_class = ProjectSerializer
    filterset_fields = ["customer", "status"]
    search_fields = ["number", "name", "customer__name"]
    ordering_fields = ["number", "name", "status", "created_at"]

    def perform_create(self, serializer):
        customer = serializer.validated_data["customer"]
        project = SimpleNamespace(**serializer.validated_data)
        serializer.save(number=next_number(
            self.request.user, "project",
            {"customer": customer, "project": project},
        ))
