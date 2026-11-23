from types import SimpleNamespace

from django.db.models import Count, Q, QuerySet, Sum
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import BaseSerializer

from core.models import Address, Contact, Customer
from core.request_helpers import request_user
from core.serializers import (
    AddressSerializer,
    ContactSerializer,
    CustomerSerializer,
)
from core.services.numbering import next_number

from .base import OwnedViewSet


class CustomerViewSet(OwnedViewSet[Customer]):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filterset_fields = ["is_active"]
    search_fields = ["number", "name", "email", "addresses__city"]
    protected_message = _(
        "This customer still has invoices or time entries and cannot be deleted. "
        "Deactivate the customer instead."
    )
    ordering_fields = [
        "number",
        "name",
        "email",
        "project_count",
        "uninvoiced_hours",
        "created_at",
    ]

    def perform_create(self, serializer: BaseSerializer[Customer]) -> None:
        customer = SimpleNamespace(**serializer.validated_data)
        serializer.save(
            number=next_number(request_user(self.request), "customer", {"customer": customer})
        )

    def get_queryset(self) -> QuerySet[Customer]:
        return (
            super()
            .get_queryset()
            .prefetch_related("addresses")
            .annotate(
                project_count=Count("projects", distinct=True),
                uninvoiced_hours=Sum(
                    "time_entries__duration_minutes",
                    filter=Q(
                        time_entries__invoice__isnull=True,
                        time_entries__billable=True,
                        time_entries__end_datetime__isnull=False,
                        time_entries__contract__isnull=True,
                    ),
                    # 0, not NULL: PostgreSQL sorts NULL first when descending.
                    default=0,
                )
                / 60.0,
            )
            .order_by("name")
            .distinct()
        )


class ContactViewSet(OwnedViewSet[Contact]):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filterset_fields = ["customer"]
    search_fields = ["first_name", "last_name", "email", "role"]
    ordering_fields = ["first_name", "last_name", "email", "role", "created_at"]


class AddressViewSet(OwnedViewSet[Address]):
    queryset = Address.objects.select_related("customer")
    serializer_class = AddressSerializer
    filterset_fields = ["customer", "is_primary"]
    ordering_fields = ["label", "street", "postal_code", "city", "country", "created_at"]
