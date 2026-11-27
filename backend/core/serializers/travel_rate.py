from rest_framework import serializers

from core.models import TravelRate

from .base import OwnedSerializer


class TravelRateSerializer(OwnedSerializer[TravelRate]):
    owner_fk_fields = ("customer", "project")

    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = TravelRate
        fields = [
            "id",
            "customer",
            "customer_name",
            "project",
            "project_name",
            "kind",
            "amount",
            "round_trip",
            "valid_from",
            "valid_to",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
