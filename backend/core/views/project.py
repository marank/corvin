from core.models import Project
from core.serializers import ProjectSerializer

from .base import OwnedViewSet


class ProjectViewSet(OwnedViewSet):
    queryset = Project.objects.select_related("customer")
    serializer_class = ProjectSerializer
    filterset_fields = ["customer", "status"]
    search_fields = ["name", "customer__name"]
    ordering_fields = ["name", "status", "created_at"]
