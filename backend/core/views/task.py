from types import SimpleNamespace

from rest_framework.serializers import BaseSerializer

from core.models import Task
from core.request_helpers import request_user
from core.serializers import TaskSerializer
from core.services.numbering import next_number

from .base import OwnedViewSet


class TaskViewSet(OwnedViewSet[Task]):
    queryset = Task.objects.select_related("project", "customer")
    serializer_class = TaskSerializer
    filterset_fields = ["customer", "project", "visit", "status", "priority"]
    search_fields = ["number", "title", "description"]
    ordering_fields = [
        "number",
        "title",
        "customer__name",
        "project__name",
        "due_date",
        "priority",
        "status",
        "position",
        "created_at",
    ]

    def perform_create(self, serializer: BaseSerializer[Task]) -> None:
        project = serializer.validated_data.get("project")
        customer = serializer.validated_data.get("customer")
        if not customer and project:
            customer = project.customer
        task_data = {**serializer.validated_data, "customer": customer}
        task = SimpleNamespace(**task_data)
        serializer.save(
            number=next_number(
                request_user(self.request),
                "task",
                {
                    "customer": customer,
                    "project": project,
                    "task": task,
                    "visit": serializer.validated_data.get("visit"),
                },
            )
        )
