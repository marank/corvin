from types import SimpleNamespace

from core.models import Task
from core.serializers import TaskSerializer
from core.services.numbering import next_number

from .base import OwnedViewSet


class TaskViewSet(OwnedViewSet):
    queryset = Task.objects.select_related("project", "customer")
    serializer_class = TaskSerializer
    filterset_fields = ["customer", "project", "visit", "status", "priority"]
    search_fields = ["number", "title", "description"]
    ordering_fields = ["number", "due_date", "priority", "position", "created_at"]

    def perform_create(self, serializer):
        project = serializer.validated_data.get("project")
        customer = serializer.validated_data.get("customer")
        if not customer and project:
            customer = project.customer
        task_data = {**serializer.validated_data, "customer": customer}
        task = SimpleNamespace(**task_data)
        serializer.save(number=next_number(
            self.request.user, "task",
            {"customer": customer, "project": project, "task": task,
             "visit": serializer.validated_data.get("visit")},
        ))
