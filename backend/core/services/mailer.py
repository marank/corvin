from django.conf import settings
from django.core.mail import EmailMessage
from django.template import Context, Template
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from core.jobs import defer
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


def queue_invoice_email(invoice: Invoice, to: str, subject: str, body: str) -> None:
    """Send the invoice by email in the background (job ``send_invoice_email``).

    Subject and body are rendered now, so the job sends exactly what the user confirmed;
    the PDF is archived now if it isn't yet, so errors show up in the request. The invoice
    becomes "sent" once the mail is out.
    """
    subject, body = render_invoice_email(invoice, subject, body)
    if not invoice.documents.filter(kind="pdf").exists():
        archive_invoice(invoice)
    defer(
        "core.tasks.send_invoice_email",
        invoice_id=str(invoice.id),
        to=to,
        subject=subject,
        body=body,
    )


def send_invoice_email(invoice_id: str, to: str, subject: str, body: str) -> None:
    """Send the archived invoice PDF by email and mark the invoice as sent."""
    invoice = Invoice.objects.get(pk=invoice_id)
    doc = invoice.documents.get(kind="pdf")
    with doc.file.open("rb") as file:
        pdf_bytes = file.read()

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
