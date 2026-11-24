from types import SimpleNamespace

from django.db.models import QuerySet
from rest_framework.serializers import BaseSerializer

from core.models import Project
from core.request_helpers import request_user
from core.serializers import ProjectSerializer
from core.services.number_changes import number_locked_annotation
from core.services.numbering import next_number

from .base import OwnedViewSet


class ProjectViewSet(OwnedViewSet[Project]):
    queryset = Project.objects.select_related("customer")
    serializer_class = ProjectSerializer
    filterset_fields = ["customer", "status"]
    search_fields = ["number", "name", "customer__name"]
    ordering_fields = [
        "number",
        "name",
        "customer__name",
        "status",
        "created_at",
    ]

    def get_queryset(self) -> QuerySet[Project]:
        return super().get_queryset().annotate(number_locked=number_locked_annotation(Project))

    def perform_create(self, serializer: BaseSerializer[Project]) -> None:
        customer = serializer.validated_data["customer"]
        project = SimpleNamespace(**serializer.validated_data)
        serializer.save(
            number=next_number(
                request_user(self.request),
                "project",
                {"customer": customer, "project": project},
            )
        )
