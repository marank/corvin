import json
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse
from django.template import Context, Template
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import override
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import CompanyContact, DocumentTemplate
from core.serializers import DocumentTemplateSerializer
from core.services.pdf import (
    build_pdf_html,
    company_image_context,
    template_page_context,
    text_block_context,
    write_pdf,
)
from core.services.templates import ensure_default_template

from .base import OwnedViewSet


class _SampleObj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _sample_invoice(request):
    company = getattr(request.user, "company_settings", None)
    items = [
        _SampleObj(position=i, description=d, quantity=q, unit="hours", unit_price=p, total=q * p)
        for i, (d, q, p) in enumerate(
            [
                (_("Consulting"), Decimal("8"), Decimal("85")),
                (_("On-site support"), Decimal("4"), Decimal("95")),
            ],
            start=1,
        )
    ]
    subtotal = sum(i.total for i in items)
    vat = subtotal * Decimal("0.19")
    return (
        _SampleObj(
            number="RE-2026-0042",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate(),
            subtotal=subtotal,
            vat_rate=Decimal("19"),
            vat_amount=vat,
            total=subtotal + vat,
            currency="EUR",
            amount_paid=Decimal("0"),
            remaining=subtotal + vat,
            notes="",
            bank_account=_SampleObj(
                name="Geschäftskonto",
                bank_name="Musterbank",
                account_holder="Musterfirma GmbH",
                iban="DE02120300000000202051",
                bic="BYLADEM1001",
            ),
        ),
        items,
        _SampleObj(
            name="Musterkunde GmbH",
            street="Musterstraße 1",
            postal_code="10115",
            city="Berlin",
            country="Deutschland",
        ),
        company,
    )


class DocumentTemplateViewSet(OwnedViewSet):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "page_size", "created_at"]

    def list(self, request, *args, **kwargs):
        ensure_default_template(request.user)
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="export")
    def export_template(self, request, pk=None):
        template = self.get_object()
        data = DocumentTemplateSerializer(template, context={"request": request}).data
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)
        payload = {
            "format": "corvin.document-template",
            "version": 1,
            "template": data,
        }
        filename = slugify(template.name) or "document-template"
        return HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

    @action(detail=False, methods=["post"], url_path="import")
    def import_template(self, request):
        payload = request.data
        if not isinstance(payload, dict):
            return Response(
                {"detail": _("Invalid template file.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            payload.get("format") != "corvin.document-template"
            or payload.get("version") != 1
            or not isinstance(payload.get("template"), dict)
        ):
            return Response(
                {"detail": _("Unsupported template format or version.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = {**payload["template"]}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return Response(
            self.get_serializer(template).data,
            status=status.HTTP_201_CREATED,
        )

    def _build_preview_context(self, request, template, for_pdf=False):
        """Build shared sample-data context for HTML and PDF previews."""
        invoice, items, customer, company = _sample_invoice(request)
        # WeasyPrint reads the images from disk, the browser through the API.
        images = company_image_context(request.user, for_pdf)
        if not for_pdf:
            images = {key: request.build_absolute_uri(url) for key, url in images.items()}
        ctx = Context(
            {
                "invoice": invoice,
                "items": items,
                "customer": customer,
                "company": company,
                "images": images,
                "company_contacts": list(CompanyContact.objects.filter(owner=request.user)),
                "invoice_contacts": [
                    _SampleObj(name="Erika Musterfrau"),
                    _SampleObj(name="Max Mustermann"),
                ],
                "page": template_page_context(template, "invoice"),
            }
        )
        ctx["text_blocks"] = text_block_context(request.user, ctx)
        return ctx

    def _preview_template(self, request):
        """The stored template; a POST previews unsaved designer changes without storing them."""
        template = self.get_object()
        if request.method == "POST":
            serializer = self.get_serializer(template, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            for field, value in serializer.validated_data.items():
                setattr(template, field, value)
        return template

    def _render_preview_html(self, ctx, template):
        return build_pdf_html(
            template,
            header=Template(template.header_html).render(ctx),
            body=Template(template.body_html).render(ctx),
            footer=Template(template.footer_html).render(ctx),
            css=Template(template.css).render(ctx),
        )

    @xframe_options_exempt
    @action(detail=True, methods=["get", "post"])
    @override(settings.LANGUAGE_CODE)
    def preview(self, request, pk=None):
        """Render the template with sample data (HTML)."""
        template = self._preview_template(request)
        ctx = self._build_preview_context(request, template)
        return HttpResponse(self._render_preview_html(ctx, template), content_type="text/html")

    @action(detail=True, methods=["get", "post"], url_path="preview-pdf")
    @override(settings.LANGUAGE_CODE)
    def preview_pdf(self, request, pk=None):
        """Render the template with sample data as a PDF (inline)."""
        template = self._preview_template(request)
        ctx = self._build_preview_context(request, template, for_pdf=True)
        return HttpResponse(
            write_pdf(self._render_preview_html(ctx, template), request.user),
            content_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
