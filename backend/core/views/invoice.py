from datetime import datetime, time
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import django_filters
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Exists, OuterRef, QuerySet
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from core.models import CompanySettings, Invoice, InvoiceLineItem, MailTemplate
from core.request_helpers import request_user
from core.serializers import InvoiceSerializer, TimeEntrySerializer
from core.services.archiving import archive_invoice
from core.services.consolidation import consolidate, header_defaults, preview
from core.services.draft_editing import draft_state, update_draft
from core.services.erechnung import build_xrechnung_xml
from core.services.mailer import queue_invoice_email, render_invoice_mail
from core.services.pdf import render_invoice_html, render_invoice_pdf
from core.services.time_report import render_time_report_pdf

from .base import OwnedViewSet


class ManualLineSerializer(serializers.Serializer[Any]):
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal(1))
    unit = serializers.ChoiceField(
        choices=InvoiceLineItem.Unit.choices, default=InvoiceLineItem.Unit.FLAT
    )
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class EntryLineSerializer(serializers.Serializer[Any]):
    entry_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    description = serializers.CharField(max_length=500)


class ConsolidateSerializer(serializers.Serializer[Any]):
    customer_id = serializers.UUIDField()
    # Bill only these of the matching entries; omitted = all of them.
    entry_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    contact_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    extra_lines = ManualLineSerializer(many=True, required=False)
    project_id = serializers.UUIDField(required=False, allow_null=True)
    bank_account_id = serializers.UUIDField(required=False, allow_null=True)
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    group_by = serializers.ChoiceField(
        choices=Invoice.GroupBy.choices, default=Invoice.GroupBy.ENTRY
    )
    # Lines the user put together from entries (each: the entries and the text); replaces
    # the grouping. Omitted: lines are grouped by `group_by`.
    entry_lines = EntryLineSerializer(many=True, required=False)
    # Omitted: today, issue date + payment terms, the company's rate, the assigned template.
    issue_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    vat_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal(0), required=False, allow_null=True
    )
    template_id = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    # Editing a draft only: its number, corrected by hand (omitted: unchanged).
    number = serializers.CharField(max_length=50, required=False)
    # Omitted: the customer's default.
    e_invoice_format = serializers.ChoiceField(
        choices=Invoice.EInvoiceFormat.choices, required=False
    )


class PreviewLineSerializer(ManualLineSerializer):
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    # Lines built from entries: their entries, and when grouped their key and generated
    # text. Own lines have no key and no entries.
    key = serializers.CharField(allow_null=True)
    entry_ids = serializers.ListField(child=serializers.UUIDField())
    default_description = serializers.CharField(required=False)
    # Shown next to lines from entries: their project (one) and period.
    project_name = serializers.CharField(allow_null=True, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class ConsolidatePreviewSerializer(serializers.Serializer[Any]):
    lines = PreviewLineSerializer(many=True)
    entry_count = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)


class DraftStateSerializer(serializers.Serializer[Any]):
    """A draft as the create page holds it (see services.draft_editing)."""

    group_by = serializers.CharField()
    entries = TimeEntrySerializer(many=True)
    # The user's line texts by line key, where they differ from the generated ones.
    texts = serializers.DictField(child=serializers.CharField())
    own_lines = ManualLineSerializer(many=True)


class MarkSentSerializer(serializers.Serializer[Any]):
    # The day it went out (by post, through another channel); omitted: now.
    sent_on = serializers.DateField(required=False)


class SendEmailSerializer(serializers.Serializer[Any]):
    to = serializers.EmailField()
    # Empty: the template's subject. The text comes from the template.
    subject = serializers.CharField(required=False, allow_blank=True, max_length=255)
    kind = serializers.ChoiceField(
        choices=MailTemplate.Kind.choices, default=MailTemplate.Kind.INVOICE
    )


class EmailDraftSerializer(serializers.Serializer[Any]):
    subject = serializers.CharField()
    html = serializers.CharField()


def _validation_detail(error: DjangoValidationError) -> dict[str, Any]:
    if hasattr(error, "error_dict"):
        return error.message_dict
    return {"detail": error.messages}


class InvoiceFilter(django_filters.FilterSet):
    # The dashboard's "open" and "overdue" receivables, as one list filter.
    receivable = django_filters.ChoiceFilter(
        choices=[("open", "open"), ("overdue", "overdue")], method="filter_receivable"
    )

    class Meta:
        model = Invoice
        fields = {
            "customer": ["exact"],
            "project": ["exact"],
            "contract": ["exact"],
            "status": ["exact"],
            "issue_date": ["gte", "lte"],
        }

    def filter_receivable(
        self, queryset: QuerySet[Invoice], name: str, value: str
    ) -> QuerySet[Invoice]:
        queryset = queryset.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.SENT])
        if value == "overdue":
            queryset = queryset.filter(due_date__lt=timezone.localdate())
        return queryset


class InvoiceViewSet(OwnedViewSet[Invoice]):
    queryset = Invoice.objects.select_related(
        "customer", "project", "contract", "template"
    ).prefetch_related("contacts", "items__time_entries", "payments")
    serializer_class = InvoiceSerializer
    filterset_class = InvoiceFilter

    def get_queryset(self) -> QuerySet[Invoice]:
        from core.models import TimeEntry

        # For the time report link; one query for the whole list.
        billed = TimeEntry.objects.filter(invoice=OuterRef("pk"))
        return super().get_queryset().annotate(time_entries_billed=Exists(billed))

    search_fields = ["number", "customer__name", "notes"]
    ordering_fields = [
        "issue_date",
        "number",
        "customer__name",
        "status",
        "total",
        "due_date",
    ]

    def perform_create(self, serializer: BaseSerializer[Invoice]) -> None:
        from core.services.numbering import next_number

        owner = request_user(self.request)
        company: CompanySettings | None = getattr(owner, "company_settings", None)
        customer = serializer.validated_data["customer"]
        open_fields = header_defaults(customer, company, serializer.validated_data["issue_date"])
        defaults: dict[str, Any] = {
            **{k: v for k, v in open_fields.items() if k not in serializer.validated_data},
            "owner": owner,
            "number": next_number(
                owner,
                "invoice",
                {
                    "customer": customer,
                    "project": serializer.validated_data.get("project"),
                    "contract": serializer.validated_data.get("contract"),
                    "invoice": SimpleNamespace(**serializer.validated_data),
                },
            ),
        }
        invoice = serializer.save(**defaults)
        if "contacts" not in serializer.validated_data:
            invoice.contacts.set(customer.contacts.filter(is_invoice_contact=True))

    def perform_update(self, serializer: BaseSerializer[Invoice]) -> None:
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            raise ValidationError(_("Only draft invoices can be edited."))
        customer = serializer.validated_data.get("customer")
        if customer is not None and customer.id != invoice.customer_id:
            # Its time entries and contacts belong to the original customer.
            raise ValidationError({"customer": _("The customer of an invoice cannot be changed.")})
        serializer.save().recalc_totals()

    def perform_destroy(self, instance: Invoice) -> None:
        if instance.status != Invoice.Status.DRAFT:
            raise ValidationError(_("Only draft invoices can be deleted."))
        instance.delete()

    def _consolidation_args(self, request: Request) -> dict[str, Any]:
        """Validate a consolidate/preview request and resolve its ids to owned objects."""
        from core.models import BankAccount, Contact, Customer, DocumentTemplate, Project

        ser = ConsolidateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        owner = request_user(request)
        customer = Customer.objects.filter(owner=owner, pk=d["customer_id"]).first()
        if not customer:
            raise ValidationError({"customer_id": _("Invalid customer.")})
        project = None
        if d.get("project_id"):
            project = Project.objects.filter(owner=owner, pk=d["project_id"]).first()
            if not project:
                raise ValidationError({"project_id": _("Invalid project.")})
        contacts = None
        if "contact_ids" in d:
            contacts = list(
                Contact.objects.filter(
                    owner=owner,
                    customer=customer,
                    id__in=d["contact_ids"],
                )
            )
            if len(contacts) != len(set(d["contact_ids"])):
                raise ValidationError({"contact_ids": _("Invalid contacts.")})
        bank_account = None
        if d.get("bank_account_id"):
            bank_account = BankAccount.objects.filter(owner=owner, pk=d["bank_account_id"]).first()
            if not bank_account:
                raise ValidationError({"bank_account_id": _("Invalid bank account.")})
        template = None
        if d.get("template_id"):
            template = DocumentTemplate.objects.filter(owner=owner, pk=d["template_id"]).first()
            if not template:
                raise ValidationError({"template_id": _("Invalid template.")})
        return {
            "owner": owner,
            "customer": customer,
            "project": project,
            "date_from": d.get("date_from"),
            "date_to": d.get("date_to"),
            "entry_ids": d.get("entry_ids"),
            "group_by": d["group_by"],
            "entry_lines": d.get("entry_lines"),
            "contacts": contacts,
            "bank_account": bank_account,
            "e_invoice_format": d.get("e_invoice_format"),
            "extra_lines": d.get("extra_lines"),
            "vat_rate": d.get("vat_rate"),
            "template": template,
            "issue_date": d.get("issue_date"),
            "due_date": d.get("due_date"),
            "notes": d.get("notes", ""),
            "number": d.get("number"),
        }

    @action(detail=False, methods=["post"])
    def consolidate(self, request: Request) -> Response:
        args = self._consolidation_args(request)
        args.pop("number")  # a new invoice gets the next number of its scheme
        try:
            invoice = consolidate(**args)
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        return Response(
            InvoiceSerializer(invoice, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def consolidate_preview(self, request: Request) -> Response:
        """Line items and totals `consolidate` would create, without creating anything."""
        return self._preview(request)

    def _preview(self, request: Request, invoice: Invoice | None = None) -> Response:
        args = self._consolidation_args(request)
        for key in (
            "contacts",
            "bank_account",
            "e_invoice_format",
            "template",
            "issue_date",
            "due_date",
            "notes",
            "number",
        ):
            args.pop(key)
        try:
            result = preview(**args, invoice=invoice)
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        return Response(ConsolidatePreviewSerializer(result).data)

    @extend_schema(methods=["GET"], request=None, responses=DraftStateSerializer)
    @extend_schema(methods=["PUT"], request=ConsolidateSerializer, responses=InvoiceSerializer)
    @action(detail=True, methods=["get", "put"])
    def draft(self, request: Request, pk: str | None = None) -> Response:
        """A draft as the create page edits it (GET), or saved back from the page (PUT):
        header and lines replaced, entries no longer on a line open again."""
        invoice = self.get_object()
        if request.method == "GET":
            state = DraftStateSerializer(draft_state(invoice), context={"request": request})
            return Response(state.data)
        try:
            invoice = update_draft(invoice, **self._consolidation_args(request))
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @extend_schema(request=ConsolidateSerializer, responses=ConsolidatePreviewSerializer)
    @action(detail=True, methods=["post"])
    def draft_preview(self, request: Request, pk: str | None = None) -> Response:
        """Like `consolidate_preview`, with the entries this draft bills counted as open."""
        return self._preview(request, self.get_object())

    @action(detail=True, methods=["post"])
    def finalize(self, request: Request, pk: str | None = None) -> Response:
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            raise ValidationError(_("Invoice already finalized."))
        if not invoice.items.exists():
            raise ValidationError(_("Invoice has no line items."))
        account = invoice.bank_account
        if not (account and account.iban):
            raise ValidationError(_("No bank account with an IBAN for this invoice."))
        try:
            archive_invoice(invoice)
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        invoice.status = Invoice.Status.ISSUED
        invoice.save(update_fields=["status", "updated_at"])
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @extend_schema(request=MarkSentSerializer, responses=InvoiceSerializer)
    @action(detail=True, methods=["post"])
    def mark_sent(self, request: Request, pk: str | None = None) -> Response:
        invoice = self.get_object()
        if invoice.status != Invoice.Status.ISSUED:
            raise ValidationError(_("Only issued invoices can be marked as sent."))
        ser = MarkSentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sent_on = ser.validated_data.get("sent_on")
        today = timezone.localdate()
        if sent_on and sent_on > today:
            raise ValidationError({"sent_on": _("The sending date cannot be in the future.")})
        if sent_on and sent_on < invoice.issue_date:
            raise ValidationError(
                {"sent_on": _("The sending date cannot be before the issue date.")}
            )
        invoice.status = Invoice.Status.SENT
        # An earlier day: its noon, so the date stays the same in every time zone around.
        invoice.sent_at = (
            timezone.now()
            if not sent_on or sent_on == today
            else timezone.make_aware(datetime.combine(sent_on, time(12)))
        )
        invoice.save(update_fields=["status", "sent_at", "updated_at"])
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            raise ValidationError(_("Paid invoices cannot be cancelled."))
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def pdf(self, request: Request, pk: str | None = None) -> HttpResponse | FileResponse:
        invoice = self.get_object()
        doc = invoice.documents.filter(kind="pdf").first()
        if doc:
            return FileResponse(
                doc.file.open("rb"),
                as_attachment=True,
                filename=f"{invoice.number}.pdf",
                content_type="application/pdf",
            )
        pdf_bytes = render_invoice_pdf(invoice)
        return HttpResponse(
            pdf_bytes,
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'},
        )

    @extend_schema(responses=TimeEntrySerializer(many=True))
    @action(detail=True, methods=["get"], url_path="time-entries")
    def time_entries(self, request: Request, pk: str | None = None) -> Response:
        """The time entries the invoice bills (its lines say which line bills which)."""
        entries = (
            self.get_object()
            .time_entries.select_related("customer", "project", "contract")
            .prefetch_related("breaks")
            .order_by("start_datetime")
        )
        return Response(TimeEntrySerializer(entries, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="time-report")
    def time_report(self, request: Request, pk: str | None = None) -> HttpResponse:
        """The time entries the invoice bills, line by line, as a PDF (Leistungsnachweis)."""
        invoice = self.get_object()
        filename = f"{_('Time report')} {invoice.number}.pdf"
        return HttpResponse(
            render_time_report_pdf(invoice),
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @action(detail=True, methods=["get"])
    def xrechnung(self, request: Request, pk: str | None = None) -> HttpResponse:
        invoice = self.get_object()
        doc = invoice.documents.filter(kind="xml").first()
        if doc:
            content = doc.file.read()
        else:
            try:
                content = build_xrechnung_xml(invoice)
            except DjangoValidationError as e:
                raise ValidationError(_validation_detail(e)) from e
        return HttpResponse(
            content,
            content_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="{invoice.number}.xml"'},
        )

    @xframe_options_exempt
    @action(detail=True, methods=["get"])
    def preview(self, request: Request, pk: str | None = None) -> HttpResponse:
        invoice = self.get_object()
        return HttpResponse(render_invoice_html(invoice), content_type="text/html")

    @extend_schema(
        parameters=[OpenApiParameter("kind", enum=MailTemplate.Kind.values, default="invoice")],
        responses=EmailDraftSerializer,
    )
    @action(detail=True, methods=["get"])
    def email_draft(self, request: Request, pk: str | None = None) -> Response:
        """The mail of a kind as it would be sent (`?kind=`, default: the invoice mail)."""
        kind = request.query_params.get("kind", MailTemplate.Kind.INVOICE)
        if kind not in MailTemplate.Kind.values:
            raise ValidationError({"kind": _("Unknown mail kind.")})
        mail = render_invoice_mail(self.get_object(), kind, inline_images=False)
        return Response({"subject": mail.subject, "html": mail.html})

    @action(detail=True, methods=["post"])
    def send_email(self, request: Request, pk: str | None = None) -> Response:
        invoice = self.get_object()
        ser = SendEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            queue_invoice_email(
                invoice,
                ser.validated_data["to"],
                ser.validated_data.get("subject", ""),
                ser.validated_data["kind"],
            )
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        # Accepted: the worker sends the mail and then marks the invoice as sent. Without a
        # queue (native development) it is already sent here.
        invoice.refresh_from_db()
        return Response(
            InvoiceSerializer(invoice, context={"request": request}).data,
            status=status.HTTP_202_ACCEPTED,
        )
