from rest_framework import serializers

from core.models import TimeEntry

from .base import OwnedSerializer


class TimeEntrySerializer(OwnedSerializer):
    owner_fk_fields = ("customer", "project", "visit", "contract")

    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    customer_name = serializers.CharField(
        source="customer.name", read_only=True
    )
    contract_name = serializers.CharField(
        source="contract.name", read_only=True, default=None
    )
    hours = serializers.FloatField(read_only=True)
    is_running = serializers.BooleanField(read_only=True)

    class Meta:
        model = TimeEntry
        fields = [
            "id", "customer", "customer_name", "project", "project_name",
            "visit", "contract", "contract_name",
            "date", "start_time", "end_time", "break_minutes",
            "duration_minutes", "hours", "is_running",
            "description", "billable", "invoice",
            "created_at", "updated_at",
        ]
        read_only_fields = ["duration_minutes", "created_at", "updated_at"]
