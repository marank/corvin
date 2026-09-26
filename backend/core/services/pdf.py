from io import BytesIO
from pathlib import Path

from django.template import Context, Template
from django.utils import timezone
from django.utils.safestring import mark_safe

from core.models import (
    CompanyContact,
    CompanyImage,
    Invoice,
    InvoiceTemplate,
    TextBlock,
)

from .erechnung import build_xrechnung_xml


def company_image_context(owner, for_pdf=False) -> dict:
    images = CompanyImage.objects.filter(owner=owner)
    return {
        image.key: Path(image.image.path).as_uri() if for_pdf else image.image.url
        for image in images
    }


def template_page_context(template: InvoiceTemplate, document_type="invoice") -> dict:
    return {
        "document_type": document_type,
        "size": template.page_size,
        "width": template.page_width,
        "height": template.page_height,
        "margin_top": template.margin_top,
        "margin_right": template.margin_right,
        "margin_bottom": template.margin_bottom,
        "margin_left": template.margin_left,
        "font_size": str(template.font_size),
        "primary_font": template.primary_font,
        "secondary_font": template.secondary_font,
        "primary_color": template.primary_color,
        "secondary_color": template.secondary_color,
        "tertiary_color": template.tertiary_color,
        "background_color": template.background_color,
        "text_color": template.text_color,
    }


def default_template_context(invoice: Invoice, for_pdf=False) -> dict:
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
        "images": company_image_context(invoice.owner, for_pdf),
        "company_contacts": list(CompanyContact.objects.filter(owner=invoice.owner)),
        "invoice_contacts": list(invoice.contacts.all()),
    }


def text_block_context(owner, context: Context) -> dict:
    rendered = {}
    for block in TextBlock.objects.filter(owner=owner):
        rendered[block.key] = mark_safe(Template(block.content).render(context))
    return rendered


def render_invoice_html(
    invoice: Invoice, template: InvoiceTemplate | None = None, for_pdf=False
) -> str:
    """Render the invoice's DB-stored template to a full HTML document."""
    template = template or invoice.template or InvoiceTemplate.objects.filter(
        owner=invoice.owner, is_default=True
    ).first()
    if template is None:
        raise ValueError("No invoice template available.")

    context = Context(default_template_context(invoice, for_pdf))
    context["page"] = template_page_context(template, "invoice")
    context["text_blocks"] = text_block_context(invoice.owner, context)
    body = Template(template.body_html).render(context)
    header = Template(template.header_html).render(context)
    footer = Template(template.footer_html).render(context)
    css = Template(template.css).render(context)

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
{css}
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
    html = render_invoice_html(invoice, for_pdf=True)

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
