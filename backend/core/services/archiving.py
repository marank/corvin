import hashlib

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import transaction

from core.models import DocumentArchive, Invoice

from .erechnung import build_xrechnung_xml
from .pdf import render_invoice_pdf


@transaction.atomic
def archive_invoice(invoice: Invoice) -> list[DocumentArchive]:
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


def store_document(invoice: Invoice, kind: str, content: bytes, ext: str) -> DocumentArchive:
    """Archive a file of the invoice once; an existing one stays as it is (GoBD)."""
    return _store(invoice, kind, content, ext)


def _store(invoice: Invoice, kind: str, content: bytes, ext: str) -> DocumentArchive:
    digest = hashlib.sha256(content).hexdigest()
    ct = ContentType.objects.get_for_model(invoice)
    doc, created = DocumentArchive.objects.get_or_create(
        owner=invoice.owner,
        content_type=ct,
        object_id=invoice.id,
        kind=kind,
        defaults={
            "file": ContentFile(content, name=f"{invoice.number}{ext}"),
            "sha256": digest,
        },
    )
    return doc
