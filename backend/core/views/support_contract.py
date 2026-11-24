from types import SimpleNamespace

from django.db.models import QuerySet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from core.models import SupportContract
from core.request_helpers import request_user
from core.serializers import InvoiceSerializer, SupportContractSerializer
from core.services.contracts import contract_usage, generate_invoice
from core.services.number_changes import number_locked_annotation
from core.services.numbering import next_number

from .base import OwnedViewSet


class SupportContractViewSet(OwnedViewSet[SupportContract]):
    queryset = SupportContract.objects.select_related("customer", "project", "template")
    serializer_class = SupportContractSerializer
    filterset_fields = ["customer", "project", "active", "period"]
    search_fields = ["number", "name", "customer__name"]
    ordering_fields = [
        "number",
        "name",
        "customer__name",
        "project__name",
        "period",
        "fixed_price",
        "created_at",
    ]

    def get_queryset(self) -> QuerySet[SupportContract]:
        return (
            super().get_queryset().annotate(number_locked=number_locked_annotation(SupportContract))
        )

    def perform_create(self, serializer: BaseSerializer[SupportContract]) -> None:
        customer = serializer.validated_data["customer"]
        project = serializer.validated_data.get("project")
        contract = SimpleNamespace(**serializer.validated_data)
        serializer.save(
            number=next_number(
                request_user(self.request),
                "contract",
                {"customer": customer, "project": project, "contract": contract},
            )
        )

    @action(detail=True, methods=["get"])
    def usage(self, request: Request, pk: str | None = None) -> Response:
        return Response(contract_usage(self.get_object()))

    @action(detail=True, methods=["post"])
    def run_now(self, request: Request, pk: str | None = None) -> Response:
        contract = self.get_object()
        invoice = generate_invoice(contract)
        from core.models.support_contract import add_periods

        contract.next_billing_date = add_periods(contract.next_billing_date, contract.period)
        contract.save(update_fields=["next_billing_date", "updated_at"])
        return Response(
            InvoiceSerializer(invoice, context={"request": request}).data,
            status=201,
        )
