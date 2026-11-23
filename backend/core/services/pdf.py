from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.template import Context, Template
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from core.models import (
    CompanyContact,
    CompanyImage,
    DocumentTemplate,
    Invoice,
    TextBlock,
)

from .erechnung import build_xrechnung_xml
from .templates import ensure_default_template


def company_image_context(owner: User, for_pdf: bool = False) -> dict[str, str]:
    images = CompanyImage.objects.filter(owner=owner)
    return {
        image.key: (
            Path(image.image.path).as_uri()
            if for_pdf
            else reverse("company-image-file", args=[image.pk])
        )
        for image in images
    }


def template_page_context(
    template: DocumentTemplate, document_type: str = "invoice"
) -> dict[str, Any]:
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


def document_context(
    invoice: Any,
    *,
    owner: User,
    items: list[Any],
    payments: list[Any],
    contacts: list[Any],
    for_pdf: bool = False,
) -> dict[str, Any]:
    """The variables a document template sees; real invoices and the designer's sample alike."""
    return {
        "invoice": invoice,
        "items": items,
        "customer": invoice.customer,
        "project": invoice.project,
        "contract": invoice.contract,
        "company": getattr(owner, "company_settings", None),
        "payments": payments,
        "amount_paid": invoice.amount_paid,
        "remaining": invoice.remaining,
        "now": timezone.now(),
        "images": company_image_context(owner, for_pdf),
        "company_contacts": list(CompanyContact.objects.filter(owner=owner)),
        "invoice_contacts": contacts,
    }


def default_template_context(invoice: Invoice, for_pdf: bool = False) -> dict[str, Any]:
    return document_context(
        invoice,
        owner=invoice.owner,
        items=list(invoice.items.all()),
        payments=list(invoice.payments.all()),
        contacts=list(invoice.contacts.all()),
        for_pdf=for_pdf,
    )


def text_block_context(owner: User, context: Context) -> dict[str, str]:
    # Template.render returns a SafeString: the block's own markup stays HTML, while the
    # variables it uses were autoescaped while rendering.
    return {
        block.key: Template(block.content).render(context)
        for block in TextBlock.objects.filter(owner=owner)
    }


def build_pdf_html(
    template: DocumentTemplate,
    *,
    header: str,
    body: str,
    footer: str,
    css: str,
) -> str:
    """Build the full HTML document used by WeasyPrint for PDF generation.

    This is the single source of truth for the PDF page structure shared by
    real invoice rendering and template preview. The content flows over as many
    pages as it needs; header and footer repeat on every page inside the top and
    bottom page margins.
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{css}
@page {{
  size: {template.page_width} {template.page_height};
  margin: {template.margin_top}mm {template.margin_right}mm {template.margin_bottom}mm {template.margin_left}mm;
  @top-center {{ content: element(page-header); width: 100%; }}
  @bottom-center {{ content: element(page-footer); width: 100%; }}
}}
html, body {{ margin: 0; }}
#page-header {{ position: running(page-header); }}
#page-footer {{ position: running(page-footer); }}
/* HTML previews: the first page on a grey desk, header and footer inside the margins. */
@media screen {{
  html {{ padding: 24px; background: #e5e7eb; }}
  body {{
    box-sizing: border-box;
    width: {template.page_width};
    min-height: {template.page_height};
    margin: 0 auto;
    padding: 0 {template.margin_right}mm 0 {template.margin_left}mm;
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid #9ca3af;
  }}
  #page-header, #page-footer {{
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}
  #page-header {{ order: 0; min-height: {template.margin_top}mm; }}
  #page-content {{ order: 1; flex: 1 1 auto; }}
  #page-footer {{ order: 2; min-height: {template.margin_bottom}mm; }}
}}
</style>
</head>
<body>
<div id="page-header">{header}</div>
<div id="page-footer">{footer}</div>
<div id="page-content">{body}</div>
</body>
</html>"""


def render_document_html(template: DocumentTemplate, data: dict[str, Any], owner: User) -> str:
    """Render a template's parts with the given variables into the full document."""
    context = Context(data)
    context["page"] = template_page_context(template, "invoice")
    context["text_blocks"] = text_block_context(owner, context)
    body = {
        part: Template(getattr(template, f"{part}_html")).render(context)
        for part in ("header", "body", "footer")
    }
    # CSS is not HTML: a font like "Open Sans" must not arrive as &quot;Open Sans&quot;.
    context.autoescape = False
    css = Template(template.css).render(context)
    return build_pdf_html(template, css=css, **body)


def write_pdf(html: str, owner: User, **options: Any) -> bytes:
    """Render HTML to PDF, loading only the owner's own images (see OwnerResourceFetcher)."""
    from weasyprint import HTML  # deferred: native libs load lazily on Windows

    from .pdf_fetcher import OwnerResourceFetcher

    pdf: bytes = HTML(string=html, url_fetcher=OwnerResourceFetcher(owner)).write_pdf(**options)
    return pdf


def invoice_template(invoice: Invoice) -> DocumentTemplate:
    """The invoice's own template, else the one assigned to invoices, else the default."""
    template = invoice.template
    if template is None:
        company = getattr(invoice.owner, "company_settings", None)
        assignments = getattr(company, "template_assignments", {}) or {}
        tid = assignments.get("invoice")
        if tid:
            template = DocumentTemplate.objects.filter(
                id=tid,
                owner=invoice.owner,
            ).first()
    return template or ensure_default_template(invoice.owner)


# Documents use the configured language, not the viewer's UI language.
@override(settings.LANGUAGE_CODE)
def render_invoice_html(
    invoice: Invoice, template: DocumentTemplate | None = None, for_pdf: bool = False
) -> str:
    """Render the invoice's DB-stored template to a full HTML document."""
    if template is None:
        template = invoice_template(invoice)

    return render_document_html(template, default_template_context(invoice, for_pdf), invoice.owner)


def render_invoice_pdf(invoice: Invoice) -> bytes:
    """Render PDF. ZUGFeRD: PDF/A-3 with embedded XML; else plain PDF."""
    html = render_invoice_html(invoice, for_pdf=True)

    if invoice.e_invoice_format == Invoice.EInvoiceFormat.ZUGFERD:
        xml = build_xrechnung_xml(invoice)
        pdf = write_pdf(html, invoice.owner, pdf_variant="pdf/a-3u")
        # embeds factur-x.xml + adds the Factur-X XMP extension schema
        from drafthorse.pdf import attach_xml

        archived: bytes = attach_xml(pdf, xml)
        return archived
    return write_pdf(html, invoice.owner)
