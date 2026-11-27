from rest_framework import serializers

from core.models import SupportContract

from .base import LockableNumberSerializer


class SupportContractSerializer(LockableNumberSerializer[SupportContract]):
    owner_fk_fields = ("customer", "project", "template")

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = SupportContract
        fields = [
            "id",
            "number",
            "number_locked",
            "customer",
            "customer_name",
            "project",
            "project_name",
            "name",
            "included_hours",
            "period",
            "fixed_price",
            "bill_overage",
            "overage_rate",
            "start_date",
            "end_date",
            "next_billing_date",
            "active",
            "travel_included",
            "template",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
