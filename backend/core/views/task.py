from core.models import Task
from core.serializers import TaskSerializer

from .base import OwnedViewSet


class TaskViewSet(OwnedViewSet):
    queryset = Task.objects.select_related("project")
    serializer_class = TaskSerializer
    filterset_fields = ["project", "visit", "status", "priority"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_date", "priority", "position", "created_at"]
