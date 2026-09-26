from decimal import Decimal

from django.http import HttpResponse
from django.template import Context, Template
from django.utils import timezone
from rest_framework.decorators import action

from core.models import InvoiceTemplate
from core.serializers import InvoiceTemplateSerializer

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
    ), items, _SampleObj(
        name="Musterkunde GmbH", street="Musterstraße 1",
        postal_code="10115", city="Berlin", country="Deutschland",
    ), company


class InvoiceTemplateViewSet(OwnedViewSet):
    queryset = InvoiceTemplate.objects.all()
    serializer_class = InvoiceTemplateSerializer
    search_fields = ["name"]

    def list(self, request, *args, **kwargs):
        # auto-seed a default template on first access
        if not self.get_queryset().exists():
            InvoiceTemplate.objects.create(
                owner=request.user,
                name="Default (DIN A4)",
                is_default=True,
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
                    "IBAN {{ company.iban }} · VAT {{ company.vat_id }}"
                ),
            )
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Render the template with sample data (HTML)."""
        template = self.get_object()
        invoice, items, customer, company = _sample_invoice(request)
        ctx = Context({
            "invoice": invoice, "items": items,
            "customer": customer, "company": company,
        })
        body = Template(template.body_html).render(ctx)
        header = Template(template.header_html).render(ctx)
        footer = Template(template.footer_html).render(ctx)
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {{ width: {'210mm' if template.page_size == 'A4' else '8.5in'}; margin: 0 auto;
  padding: {template.margin_top}mm {template.margin_right}mm {template.margin_bottom}mm {template.margin_left}mm;
  font-family: sans-serif; box-sizing: border-box; }}
{template.css}
</style></head><body>
<header>{header}</header>{body}<footer>{footer}</footer>
</body></html>"""
        return HttpResponse(html, content_type="text/html")
