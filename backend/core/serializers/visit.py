from rest_framework import serializers

from core.models import OnSiteVisit

from .base import NumberedSerializer


class OnSiteVisitSerializer(NumberedSerializer[OnSiteVisit]):
    owner_fk_fields = ("customer", "project")

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = OnSiteVisit
        fields = [
            "id",
            "number",
            "customer",
            "customer_name",
            "project",
            "project_name",
            "date",
            "location",
            "arrival",
            "departure",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
