from rest_framework import serializers

from core.models import Task

from .base import OwnedSerializer


class TaskSerializer(OwnedSerializer):
    owner_fk_fields = ("customer", "project", "visit")

    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = Task
        fields = [
            "id",
            "number",
            "customer",
            "customer_name",
            "project",
            "project_name",
            "visit",
            "title",
            "description",
            "due_date",
            "priority",
            "status",
            "position",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["number", "created_at", "updated_at"]
