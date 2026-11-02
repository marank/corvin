from django.core.mail import EmailMessage
from django.template import Context, Template
from django.utils import timezone

from core.models import Invoice

from .archiving import archive_invoice


def send_invoice_email(invoice: Invoice, to: str, subject: str, body: str) -> None:
    """Send the invoice PDF (or archived copy) by email."""
    template = invoice.template
    context = Context(
        {
            "invoice": invoice,
            "customer": invoice.customer,
            "company": getattr(invoice.owner, "company_settings", None),
        }
    )
    subject = Template(subject or (template.mail_subject if template else "")).render(context)
    body = Template(body or (template.mail_body if template else "")).render(context)

    doc = invoice.documents.filter(kind="pdf").first()
    pdf_bytes = doc.file.read() if doc else archive_invoice(invoice)[0].file.read()

    mail = EmailMessage(
        subject=subject,
        body=body,
        to=[to],
        attachments=[(f"{invoice.number}.pdf", pdf_bytes, "application/pdf")],
    )
    mail.send()

    invoice.status = Invoice.Status.SENT
    invoice.sent_at = timezone.now()
    invoice.save(update_fields=["status", "sent_at", "updated_at"])
