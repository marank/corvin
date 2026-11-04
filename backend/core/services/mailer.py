from django.conf import settings
from django.core.mail import EmailMessage
from django.template import Context, Template
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from core.models import Invoice

from .archiving import archive_invoice
from .pdf import invoice_template


@override(settings.LANGUAGE_CODE)
def render_invoice_email(invoice: Invoice, subject: str = "", body: str = "") -> tuple[str, str]:
    """Subject and body as sent: the given text, else the template's, else a default."""
    template = invoice_template(invoice)
    context = Context(
        {
            "invoice": invoice,
            "customer": invoice.customer,
            "company": getattr(invoice.owner, "company_settings", None),
        }
    )
    subject = subject or template.mail_subject or _("Invoice {{ invoice.number }}")
    body = body or template.mail_body or _("Dear customer,\n\nplease find attached your invoice.")
    return Template(subject).render(context), Template(body).render(context)


def send_invoice_email(invoice: Invoice, to: str, subject: str, body: str) -> None:
    """Send the invoice PDF (or archived copy) by email."""
    subject, body = render_invoice_email(invoice, subject, body)

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
