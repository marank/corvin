import json
from decimal import Decimal

from django.http import HttpResponse
from django.template import Context, Template
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import CompanyContact, CompanyImage, DocumentTemplate
from core.serializers import DocumentTemplateSerializer
from core.services.pdf import (
    build_pdf_html,
    company_image_context,
    template_page_context,
    text_block_context,
)

from .base import OwnedViewSet

SAMPLE_BODY = """<h1>Rechnung {{ invoice.number }}</h1>
<p>{{ customer.name }}</p>
<table class="items">
<thead><tr><th>Pos.</th><th>Description</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead>
<tbody>
{% for item in items %}
<tr><td>{{ item.position }}</td><td>{{ item.description }}</td>
<td>{{ item.quantity }} {{ item.unit }}</td><td>{{ item.unit_price }}</td>
<td>{{ item.total }}</td></tr>
{% endfor %}
</tbody></table>
<p>Net: {{ invoice.subtotal }} &nbsp; VAT ({{ invoice.vat_rate }}%): {{ invoice.vat_amount }} &nbsp; <b>Total: {{ invoice.total }} {{ invoice.currency }}</b></p>"""


class _SampleObj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _sample_invoice(request):
    company = getattr(request.user, "company_settings", None)
    items = [
        _SampleObj(position=i, description=d, quantity=q, unit="hours",
                   unit_price=p, total=q * p)
        for i, (d, q, p) in enumerate(
            [("Consulting services", Decimal("8"), Decimal("85")),
             ("On-site support", Decimal("4"), Decimal("95"))],
            start=1,
        )
    ]
    subtotal = sum(i.total for i in items)
    vat = subtotal * Decimal("0.19")
    return _SampleObj(
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
            name="Geschäftskonto", bank_name="Musterbank",
            account_holder="Musterfirma GmbH", iban="DE02120300000000202051",
            bic="BYLADEM1001",
        ),
    ), items, _SampleObj(
        name="Musterkunde GmbH", street="Musterstraße 1",
        postal_code="10115", city="Berlin", country="Deutschland",
    ), company


class DocumentTemplateViewSet(OwnedViewSet):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "page_size", "created_at"]

    def list(self, request, *args, **kwargs):
        # auto-seed a default template on first access
        if not self.get_queryset().exists():
            DocumentTemplate.objects.create(
                owner=request.user,
                name="Default (DIN A4)",
                body_html=SAMPLE_BODY,
                css=(
                    "body { font-family: sans-serif; font-size: 10pt; }\n"
                    ".items { width: 100%; border-collapse: collapse; }\n"
                    ".items td, .items th { border-bottom: 1px solid #ccc; "
                    "padding: 4px; text-align: left; }\n"
                    "#page-footer { font-size: 8pt; color: #666; }"
                ),
                footer_html=(
                    "{{ company.company_name }} · {{ company.street }} · "
                    "{{ company.postal_code }} {{ company.city }} · "
                    "IBAN {{ invoice.bank_account.iban }} · VAT {{ company.vat_id }}"
                ),
            )
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="export")
    def export_template(self, request, pk=None):
        template = self.get_object()
        data = DocumentTemplateSerializer(template, context={"request": request}).data
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)
        payload = {
            "format": "projectmanager.document-template",
            "version": 1,
            "template": data,
        }
        filename = slugify(template.name) or "document-template"
        return HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.json"'
            },
        )

    @action(detail=False, methods=["post"], url_path="import")
    def import_template(self, request):
        payload = request.data
        if not isinstance(payload, dict):
            return Response(
                {"detail": "Invalid template file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            payload.get("format") != "projectmanager.document-template"
            or payload.get("version") != 1
            or not isinstance(payload.get("template"), dict)
        ):
            return Response(
                {"detail": "Unsupported template format or version."},
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

    def _build_preview_context(self, request, template):
        """Build shared sample-data context for HTML and PDF previews."""
        invoice, items, customer, company = _sample_invoice(request)
        ctx = Context({
            "invoice": invoice, "items": items,
            "customer": customer, "company": company,
            "images": {
                key: request.build_absolute_uri(url)
                for key, url in company_image_context(request.user).items()
            },
            "company_contacts": list(
                CompanyContact.objects.filter(owner=request.user)
            ),
            "invoice_contacts": [
                _SampleObj(name="Erika Musterfrau"),
                _SampleObj(name="Max Mustermann"),
            ],
            "page": template_page_context(template, "invoice"),
        })
        ctx["text_blocks"] = text_block_context(request.user, ctx)
        return ctx

    @xframe_options_exempt
    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Render the template with sample data (HTML)."""
        template = self.get_object()
        ctx = self._build_preview_context(request, template)
        body = Template(template.body_html).render(ctx)
        header = Template(template.header_html).render(ctx)
        footer = Template(template.footer_html).render(ctx)
        css = Template(template.css).render(ctx)
        page_width = template.page_width
        page_height = template.page_height
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
{css}
html, body {{ margin: 0; min-height: 100%; }}
body {{
  padding: 24px;
  background: #e5e7eb;
  box-sizing: border-box;
}}
.preview-page {{
  width: {page_width};
  height: {page_height};
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  border: 1px solid #9ca3af;
  box-sizing: border-box;
}}
.preview-page > #page-header, .preview-page > #page-footer {{ flex: 0 0 auto; min-height: 0; }}
.preview-page > #page-content {{ flex: 1 1 auto; min-height: 0; }}
</style></head><body>
<div class="preview-page"><div id="page-header">{header}</div><div id="page-content">{body}</div><div id="page-footer">{footer}</div></div>
</body></html>"""
        return HttpResponse(html, content_type="text/html")

    @action(detail=True, methods=["get"], url_path="preview-pdf")
    def preview_pdf(self, request, pk=None):
        """Render the template with sample data as a PDF (inline)."""
        from io import BytesIO

        template = self.get_object()
        ctx = self._build_preview_context(request, template)

        # Use PDF image paths instead of URLs for WeasyPrint
        from pathlib import Path

        ctx["images"] = {
            img.key: Path(img.image.path).as_uri()
            for img in CompanyImage.objects.filter(owner=request.user)
        }

        html = build_pdf_html(
            template,
            header=Template(template.header_html).render(ctx),
            body=Template(template.body_html).render(ctx),
            footer=Template(template.footer_html).render(ctx),
            css=Template(template.css).render(ctx),
        )

        from weasyprint import HTML

        pdf_io = BytesIO()
        HTML(string=html).write_pdf(pdf_io)
        return HttpResponse(
            pdf_io.getvalue(),
            content_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
