from django.db import transaction
from django.db.models import Max
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import BaseSerializer

from core.models import Invoice, InvoiceLineItem, TimeEntry
from core.serializers import InvoiceLineItemSerializer

from .base import OwnedViewSet


def _require_draft(invoice: Invoice) -> None:
    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError(_("Only draft invoices can be edited."))


class InvoiceLineItemViewSet(OwnedViewSet[InvoiceLineItem]):
    """Line items of draft invoices. Every change recalculates the invoice totals."""

    queryset = InvoiceLineItem.objects.select_related("invoice")
    serializer_class = InvoiceLineItemSerializer
    filterset_fields = ["invoice"]
    ordering_fields = ["position"]

    @transaction.atomic
    def perform_create(self, serializer: BaseSerializer[InvoiceLineItem]) -> None:
        invoice = serializer.validated_data["invoice"]
        _require_draft(invoice)
        position = serializer.validated_data.get("position") or (
            (invoice.items.aggregate(m=Max("position"))["m"] or 0) + 1
        )
        serializer.save(position=position)
        invoice.recalc_totals()

    @transaction.atomic
    def perform_update(self, serializer: BaseSerializer[InvoiceLineItem]) -> None:
        item = serializer.instance
        if item is None:  # DRF passes the instance on every update
            raise RuntimeError("perform_update called without an instance")
        _require_draft(item.invoice)
        target = serializer.validated_data.get("invoice")
        if target is not None and target.id != item.invoice_id:
            raise ValidationError({"invoice": _("A line item cannot be moved to another invoice.")})
        serializer.save()
        item.invoice.recalc_totals()

    @transaction.atomic
    def perform_destroy(self, instance: InvoiceLineItem) -> None:
        invoice = instance.invoice
        _require_draft(invoice)
        # The entries billed on this line become billable again.
        TimeEntry.objects.filter(invoice_item=instance).update(invoice=None, invoice_item=None)
        instance.delete()
        for position, item in enumerate(invoice.items.order_by("position", "id"), start=1):
            if item.position != position:
                item.position = position
                item.save(update_fields=["position", "updated_at"])
        invoice.recalc_totals()
