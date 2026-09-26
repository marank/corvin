import hashlib

from django.core.files.base import ContentFile
from django.db import transaction

from core.models import Invoice, InvoiceDocument

from .erechnung import build_xrechnung_xml
from .pdf import render_invoice_pdf


@transaction.atomic
def archive_invoice(invoice: Invoice) -> list[InvoiceDocument]:
    """Render once and store immutable copies (GoBD).

    Called at finalize; subsequent downloads serve the archived files.
    """
    docs = []
    pdf_bytes = render_invoice_pdf(invoice)
    docs.append(_store(invoice, "pdf", pdf_bytes, ".pdf"))

    if invoice.e_invoice_format != Invoice.EInvoiceFormat.NONE:
        xml = build_xrechnung_xml(invoice)
        docs.append(_store(invoice, "xml", xml, ".xml"))

    return docs


def _store(invoice: Invoice, kind: str, content: bytes, ext: str) -> InvoiceDocument:
    digest = hashlib.sha256(content).hexdigest()
    doc, created = InvoiceDocument.objects.get_or_create(
        owner=invoice.owner, invoice=invoice, kind=kind,
        defaults={
            "file": ContentFile(content, name=f"{invoice.number}{ext}"),
            "sha256": digest,
        },
    )
    return doc
