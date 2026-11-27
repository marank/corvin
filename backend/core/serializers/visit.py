from rest_framework import serializers

from core.models import OnSiteVisit

from .base import NumberedSerializer


class OnSiteVisitSerializer(NumberedSerializer[OnSiteVisit]):
    owner_fk_fields = ("customer", "project")

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    # The distance that counts when the visit has none of its own.
    customer_distance_km = serializers.DecimalField(
        source="customer.travel_distance_km",
        max_digits=7,
        decimal_places=1,
        read_only=True,
        default=None,
    )
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default=None)

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
            "bill_travel",
            "distance_km",
            "travel_price",
            "customer_distance_km",
            "invoice",
            "invoice_number",
            "created_at",
            "updated_at",
        ]
        # Invoicing links a trip to its invoice, never this API.
        read_only_fields = ["invoice", "created_at", "updated_at"]
