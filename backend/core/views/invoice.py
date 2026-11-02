from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.models import Invoice
from core.serializers import InvoiceSerializer
from core.services.archiving import archive_invoice
from core.services.consolidation import consolidate
from core.services.erechnung import build_xrechnung_xml
from core.services.mailer import send_invoice_email
from core.services.pdf import render_invoice_html, render_invoice_pdf

from .base import OwnedViewSet


class ManualLineSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = serializers.ChoiceField(choices=["hours", "flat", "piece"], default="flat")
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class ConsolidateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    contact_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    extra_lines = ManualLineSerializer(many=True, required=False)
    project_id = serializers.UUIDField(required=False, allow_null=True)
    bank_account_id = serializers.UUIDField(required=False, allow_null=True)
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    group_by = serializers.ChoiceField(choices=["entry", "day", "project"], default="entry")
    e_invoice_format = serializers.ChoiceField(
        choices=["none", "zugferd", "xrechnung"], default="none"
    )


class SendEmailSerializer(serializers.Serializer):
    to = serializers.EmailField()
    subject = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True)


def _validation_detail(error):
    if hasattr(error, "error_dict"):
        return error.message_dict
    return {"detail": error.messages}


class InvoiceViewSet(OwnedViewSet):
    queryset = Invoice.objects.select_related(
        "customer", "project", "contract", "template"
    ).prefetch_related("contacts", "items", "payments")
    serializer_class = InvoiceSerializer
    filterset_fields = {
        "customer": ["exact"],
        "project": ["exact"],
        "contract": ["exact"],
        "status": ["exact"],
        "issue_date": ["gte", "lte"],
    }
    search_fields = ["number", "customer__name", "notes"]
    ordering_fields = [
        "issue_date",
        "number",
        "customer__name",
        "status",
        "total",
        "due_date",
    ]

    def perform_create(self, serializer):
        from core.services.numbering import next_number

        company = getattr(self.request.user, "company_settings", None)
        customer = serializer.validated_data["customer"]
        issue_date = serializer.validated_data["issue_date"]
        payment_terms_days = (
            customer.payment_terms_days
            if customer.payment_terms_days is not None
            else company.payment_terms_days
            if company
            else 14
        )
        defaults = {
            "owner": self.request.user,
            "number": next_number(
                self.request.user,
                "invoice",
                {
                    "customer": customer,
                    "project": serializer.validated_data.get("project"),
                    "contract": serializer.validated_data.get("contract"),
                    "invoice": SimpleNamespace(**serializer.validated_data),
                },
            ),
        }
        if "due_date" not in serializer.validated_data:
            defaults["due_date"] = issue_date + timedelta(days=payment_terms_days)
        if "currency" not in serializer.validated_data:
            defaults["currency"] = company.currency if company else "EUR"
        if "vat_rate" not in serializer.validated_data:
            defaults["vat_rate"] = (
                company.default_vat_rate
                if company and company.vat_enabled
                else Decimal("0")
                if company
                else Decimal("19")
            )
        invoice = serializer.save(**defaults)
        if "contacts" not in serializer.validated_data:
            invoice.contacts.set(customer.contacts.filter(is_invoice_contact=True))

    def perform_update(self, serializer):
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            raise ValidationError("Only draft invoices can be edited.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != Invoice.Status.DRAFT:
            raise ValidationError("Only draft invoices can be deleted.")
        instance.delete()

    @action(detail=False, methods=["post"])
    def consolidate(self, request):
        from core.models import BankAccount, Contact, Customer, Project

        ser = ConsolidateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        customer = Customer.objects.filter(owner=request.user, pk=d["customer_id"]).first()
        if not customer:
            raise ValidationError({"customer_id": "Invalid customer."})
        project = None
        if d.get("project_id"):
            project = Project.objects.filter(owner=request.user, pk=d["project_id"]).first()
            if not project:
                raise ValidationError({"project_id": "Invalid project."})
        contacts = None
        if "contact_ids" in d:
            contacts = list(
                Contact.objects.filter(
                    owner=request.user,
                    customer=customer,
                    id__in=d["contact_ids"],
                )
            )
            if len(contacts) != len(set(d["contact_ids"])):
                raise ValidationError({"contact_ids": "Invalid contacts."})
        bank_account = None
        if d.get("bank_account_id"):
            bank_account = BankAccount.objects.filter(
                owner=request.user, pk=d["bank_account_id"]
            ).first()
            if not bank_account:
                raise ValidationError({"bank_account_id": "Invalid bank account."})
        try:
            invoice = consolidate(
                owner=request.user,
                customer=customer,
                project=project,
                date_from=d.get("date_from"),
                date_to=d.get("date_to"),
                group_by=d["group_by"],
                contacts=contacts,
                bank_account=bank_account,
                e_invoice_format=d["e_invoice_format"],
                extra_lines=d.get("extra_lines"),
            )
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        return Response(
            InvoiceSerializer(invoice, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            raise ValidationError("Invoice already finalized.")
        if not invoice.items.exists():
            raise ValidationError("Invoice has no line items.")
        try:
            archive_invoice(invoice)
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        invoice.status = Invoice.Status.ISSUED
        invoice.save(update_fields=["status", "updated_at"])
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def mark_sent(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != Invoice.Status.ISSUED:
            raise ValidationError("Only issued invoices can be marked as sent.")
        invoice.status = Invoice.Status.SENT
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=["status", "sent_at", "updated_at"])
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            raise ValidationError("Paid invoices cannot be cancelled.")
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
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

    @action(detail=True, methods=["get"])
    def xrechnung(self, request, pk=None):
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
    def preview(self, request, pk=None):
        invoice = self.get_object()
        return HttpResponse(render_invoice_html(invoice), content_type="text/html")

    @action(detail=True, methods=["post"])
    def send_email(self, request, pk=None):
        invoice = self.get_object()
        ser = SendEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            send_invoice_email(
                invoice,
                ser.validated_data["to"],
                ser.validated_data.get("subject", ""),
                ser.validated_data.get("body", ""),
            )
        except DjangoValidationError as e:
            raise ValidationError(_validation_detail(e)) from e
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)
