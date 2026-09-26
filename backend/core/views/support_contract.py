from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import SupportContract
from core.serializers import InvoiceSerializer, SupportContractSerializer
from core.services.contracts import contract_usage, generate_invoice

from .base import OwnedViewSet


class SupportContractViewSet(OwnedViewSet):
    queryset = SupportContract.objects.select_related(
        "customer", "project", "template"
    )
    serializer_class = SupportContractSerializer
    filterset_fields = ["customer", "project", "active", "period"]
    search_fields = ["name", "customer__name"]

    @action(detail=True, methods=["get"])
    def usage(self, request, pk=None):
        return Response(contract_usage(self.get_object()))

    @action(detail=True, methods=["post"])
    def run_now(self, request, pk=None):
        contract = self.get_object()
        invoice = generate_invoice(contract)
        from core.models.support_contract import add_periods

        contract.next_billing_date = add_periods(
            contract.next_billing_date, contract.period
        )
        contract.save(update_fields=["next_billing_date", "updated_at"])
        return Response(
            InvoiceSerializer(invoice, context={"request": request}).data,
            status=201,
        )
