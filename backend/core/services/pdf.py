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
        "header_height": template.header_height,
        "footer_height": template.footer_height,
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
        "app_url": settings.PUBLIC_URL,
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
    real invoice rendering and template preview. The template's margins frame the
    whole page. Header and footer repeat on every page inside them, in the room the
    template gives them (header_height, footer_height); the content flows in between
    over as many pages as it needs. A part may reach into the margins on purpose, e.g.
    a footer background pulled to the page edges with negative margins.
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{css}
@page {{
  size: {template.page_width} {template.page_height};
  margin: {template.margin_top + template.header_height}mm {template.margin_right}mm
    {template.margin_bottom + template.footer_height}mm {template.margin_left}mm;
  @top-center {{ content: element(page-header); width: 100%; vertical-align: bottom; }}
  @bottom-center {{ content: element(page-footer); width: 100%; vertical-align: top; }}
}}
html, body {{ margin: 0; }}
#page-header {{ position: running(page-header); }}
#page-footer {{ position: running(page-footer); }}
/* The current page number in any element with class="page-number". */
.page-number::after {{ content: counter(page); }}
/* HTML previews: the first page on a grey desk, header and footer inside the margins. */
@media screen {{
  html {{ padding: 24px; background: #e5e7eb; }}
  body {{
    box-sizing: border-box;
    width: {template.page_width};
    min-height: {template.page_height};
    margin: 0 auto;
    padding: {template.margin_top}mm {template.margin_right}mm {template.margin_bottom}mm {template.margin_left}mm;
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid #9ca3af;
  }}
  #page-header {{ order: 0; min-height: {template.header_height}mm; }}
  #page-content {{ order: 1; flex: 1 1 auto; }}
  #page-footer {{ order: 2; min-height: {template.footer_height}mm; }}
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


def uses_page_count(template: DocumentTemplate, owner: User) -> bool:
    """Whether the template or the owner's text blocks mention `page_count`.

    A plain text search: a mention in a comment only costs an extra layout.
    """
    parts = (template.header_html, template.body_html, template.footer_html, template.css)
    return any("page_count" in part for part in parts) or (
        TextBlock.objects.filter(owner=owner, content__contains="page_count").exists()
    )


def write_document_pdf(
    template: DocumentTemplate, data: dict[str, Any], owner: User, **options: Any
) -> bytes:
    """Render a document to PDF.

    Templates get `page_count`, e.g. for "Seite 2 von 3" with class="page-number". It is
    only known after laying the document out, so a document with more than one page whose
    template or text blocks use `page_count` is laid out a second time with it (it is 1
    before, so text shown only for more pages cannot change the page breaks). Templates
    without it, and single pages, are laid out once.
    """
    from weasyprint import HTML  # deferred: native libs load lazily on Windows

    from .pdf_fetcher import OwnerResourceFetcher

    fetcher = OwnerResourceFetcher(owner)

    def layout(page_count: int) -> Any:
        data["page_count"] = page_count
        html = render_document_html(template, data, owner)
        return HTML(string=html, url_fetcher=fetcher).render()

    document = layout(1)
    if len(document.pages) > 1 and uses_page_count(template, owner):
        document = layout(len(document.pages))
    pdf: bytes = document.write_pdf(**options)
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


@override(settings.LANGUAGE_CODE)
def render_invoice_pdf(invoice: Invoice) -> bytes:
    """Render PDF. ZUGFeRD: PDF/A-3 with embedded XML; else plain PDF."""
    template = invoice_template(invoice)
    data = default_template_context(invoice, for_pdf=True)

    if invoice.e_invoice_format == Invoice.EInvoiceFormat.ZUGFERD:
        xml = build_xrechnung_xml(invoice)
        pdf = write_document_pdf(template, data, invoice.owner, pdf_variant="pdf/a-3u")
        # embeds factur-x.xml + adds the Factur-X XMP extension schema
        from drafthorse.pdf import attach_xml

        archived: bytes = attach_xml(pdf, xml)
        return archived
    return write_document_pdf(template, data, invoice.owner)
