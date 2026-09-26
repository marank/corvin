from django.db.models import Count, Q, Sum

from core.models import Contact, Customer
from core.serializers import ContactSerializer, CustomerSerializer

from .base import OwnedViewSet


class CustomerViewSet(OwnedViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "email", "city"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                project_count=Count("projects", distinct=True),
                uninvoiced_hours=Sum(
                    "projects__time_entries__duration_minutes",
                    filter=Q(
                        projects__time_entries__invoice__isnull=True,
                        projects__time_entries__billable=True,
                        projects__time_entries__end_time__isnull=False,
                        projects__time_entries__contract__isnull=True,
                    ),
                )
                / 60.0,
            )
            .order_by("name")
        )


class ContactViewSet(OwnedViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filterset_fields = ["customer"]
    search_fields = ["name", "email", "role"]
