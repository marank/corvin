from io import BytesIO

from django.template import Context, Template
from django.utils import timezone

from core.models import Invoice, InvoiceTemplate

from .erechnung import build_xrechnung_xml


def default_template_context(invoice: Invoice) -> dict:
    company = getattr(invoice.owner, "company_settings", None)
    return {
        "invoice": invoice,
        "items": list(invoice.items.all()),
        "customer": invoice.customer,
        "project": invoice.project,
        "contract": invoice.contract,
        "company": company,
        "payments": list(invoice.payments.all()),
        "amount_paid": invoice.amount_paid,
        "remaining": invoice.remaining,
        "now": timezone.now(),
    }


def render_invoice_html(invoice: Invoice, template: InvoiceTemplate | None = None) -> str:
    """Render the invoice's DB-stored template to a full HTML document."""
    template = template or invoice.template or InvoiceTemplate.objects.filter(
        owner=invoice.owner, is_default=True
    ).first()
    if template is None:
        raise ValueError("No invoice template available.")

    context = Context(default_template_context(invoice))
    body = Template(template.body_html).render(context)
    header = Template(template.header_html).render(context)
    footer = Template(template.footer_html).render(context)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
  size: {template.page_size};
  margin: {template.margin_top}mm {template.margin_right}mm
          {template.margin_bottom}mm {template.margin_left}mm;
  @top-center {{ content: element(pageHeader); }}
  @bottom-center {{ content: element(pageFooter); }}
}}
#page-header {{ position: running(pageHeader); }}
#page-footer {{ position: running(pageFooter); }}
{template.css}
</style>
</head>
<body>
<div id="page-header">{header}</div>
<div id="page-footer">{footer}</div>
{body}
</body>
</html>"""


def render_invoice_pdf(invoice: Invoice) -> bytes:
    """Render PDF. ZUGFeRD: PDF/A-3 with embedded XML; else plain PDF."""
    html = render_invoice_html(invoice)

    from weasyprint import HTML  # deferred: native libs load lazily on Windows

    pdf_io = BytesIO()
    if invoice.e_invoice_format == Invoice.EInvoiceFormat.ZUGFERD:
        xml = build_xrechnung_xml(invoice)
        HTML(string=html).write_pdf(pdf_io, pdf_variant="pdf/a-3u")
        # embeds factur-x.xml + adds the Factur-X XMP extension schema
        from drafthorse.pdf import attach_xml

        pdf_io = BytesIO(attach_xml(pdf_io.getvalue(), xml))
    else:
        HTML(string=html).write_pdf(pdf_io)
    return pdf_io.getvalue()
