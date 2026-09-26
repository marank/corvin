from rest_framework import serializers

from core.models import Task

from .base import OwnedSerializer


class TaskSerializer(OwnedSerializer):
    owner_fk_fields = ("project", "visit")

    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )

    class Meta:
        model = Task
        fields = [
            "id", "project", "project_name", "visit", "title",
            "description", "due_date", "priority", "status", "position",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
