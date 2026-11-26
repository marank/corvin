"""Invoice mails: rendered from the e-mail template assigned to their kind, sent as HTML
with a plain-text part, the archived invoice attached and company images inline."""

import email.policy
import mimetypes
from dataclasses import dataclass
from email.message import EmailMessage
from email.policy import Policy
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template import Context
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from core.jobs import defer
from core.models import CompanyImage, Invoice, MailTemplate

from .archiving import archive_invoice
from .mail_templates import RenderedMail, mail_template_for, render_mail
from .pdf import default_template_context, text_block_context

# Mails about an invoice the customer has: only finalized ones, whose PDF never changes.
SENDABLE = (Invoice.Status.ISSUED, Invoice.Status.SENT)


def join_names(names: list[str]) -> str:
    """ "Erika", "Erika und Max", "Erika, Max und Tom" (in LANGUAGE_CODE)."""
    if len(names) < 2:
        return "".join(names)
    return _("%(names)s and %(last)s") % {"names": ", ".join(names[:-1]), "last": names[-1]}


def recipient_contacts(contacts: list[Any], to: list[str] | None) -> list[Any]:
    """The contacts a mail greets: those it goes to (by address, in the order given), or
    without addresses yet, the ones with an address."""
    if to is None:
        return [contact for contact in contacts if contact.email]
    by_email = {contact.email.lower(): contact for contact in contacts if contact.email}
    return [by_email[address.lower()] for address in to if address.lower() in by_email]


def mail_context(
    owner: User, data: dict[str, Any], contacts: list[Any], to: list[str] | None = None
) -> dict[str, Any]:
    """What a mail template sees: the document variables (`data`), the text blocks, and for
    the greeting the recipients (`recipients`: name as greeted, contact), their names
    joined (`names`) and the first one (`contact`)."""
    greeted = recipient_contacts(contacts, to)
    names = [getattr(c, "salutation_name", "") or c.name for c in greeted]
    data = {
        **data,
        "recipients": [
            {"name": name, "contact": c} for name, c in zip(names, greeted, strict=True)
        ],
        "names": join_names(names),
        "contact": greeted[0] if greeted else None,
    }
    data["text_blocks"] = text_block_context(owner, Context(data))
    return data


def invoice_mail_context(invoice: Invoice, to: list[str] | None = None) -> dict[str, Any]:
    # Anyone of the customer may be greeted, invoice contact or not.
    contacts = list(invoice.contacts.all())
    others = invoice.customer.contacts.exclude(pk__in=[c.pk for c in contacts])
    return mail_context(invoice.owner, default_template_context(invoice), [*contacts, *others], to)


def default_recipients(invoice: Invoice) -> list[str]:
    """Who an invoice mail goes to unless the user changes it: the invoice contacts with
    an address, else the customer's address."""
    addresses = [c.email for c in invoice.contacts.all() if c.email]
    return addresses or ([invoice.customer.email] if invoice.customer.email else [])


@override(settings.LANGUAGE_CODE)
def render_invoice_mail(
    invoice: Invoice,
    kind: str = MailTemplate.Kind.INVOICE,
    *,
    to: list[str] | None = None,
    inline_images: bool = True,
) -> RenderedMail:
    """The mail of a kind about the invoice to these addresses (None: the default ones),
    from the template assigned to the kind."""
    template = mail_template_for(invoice.owner, kind)
    to = default_recipients(invoice) if to is None else to
    return render_mail(template, invoice_mail_context(invoice, to), inline_images=inline_images)


def queue_invoice_email(
    invoice: Invoice, to: list[str], subject: str = "", kind: str = MailTemplate.Kind.INVOICE
) -> None:
    """Send a mail about the invoice in the background (job ``send_invoice_email``).

    It is rendered now, so the job sends exactly what the user confirmed (an empty subject:
    the template's); the archived PDF is attached (archived now if an older invoice has none
    yet), so errors show up in the request. An invoice mail makes the invoice "sent".
    """
    if invoice.status not in SENDABLE:
        raise ValidationError(_("Only finalized invoices can be sent."))
    mail = render_invoice_mail(invoice, kind, to=to)
    if not invoice.documents.filter(kind="pdf").exists():
        archive_invoice(invoice)
    defer(
        "core.tasks.send_invoice_email",
        invoice_id=str(invoice.id),
        to=to,
        subject=subject or mail.subject,
        html=mail.html,
        text=mail.text,
        images=mail.images,
        kind=kind,
    )


def _attachments(invoice: Invoice) -> list[tuple[str, bytes, str]]:
    """The archived PDF; for XRechnung the XML too, which is the invoice there (ZUGFeRD
    carries it inside the PDF)."""
    kinds = ["pdf"]
    if invoice.e_invoice_format == Invoice.EInvoiceFormat.XRECHNUNG:
        kinds.append("xml")
    files = []
    for doc in invoice.documents.filter(kind__in=kinds).order_by("kind"):
        with doc.file.open("rb") as file:
            content = file.read()
        mime = "application/pdf" if doc.kind == "pdf" else "application/xml"
        files.append((f"{invoice.number}.{doc.kind}", content, mime))
    return files


@dataclass
class InlineImage:
    cid: str
    content: bytes
    subtype: str
    filename: str


def _inline_image(image: CompanyImage) -> InlineImage:
    name = image.image.name or image.key
    with image.image.open("rb") as file:
        content = file.read()
    mime, _encoding = mimetypes.guess_type(name)
    return InlineImage(
        cid=image.key,
        content=content,
        subtype=(mime or "image/png").split("/", 1)[1],
        filename=Path(name).name,
    )


class HtmlMail(EmailMultiAlternatives):
    """A mail whose HTML part shows images sent along with it (cid:<key>): each goes into
    a multipart/related part next to the HTML, where mail programs look for them."""

    def __init__(self, *args: Any, inline_images: list[InlineImage], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.inline_images = inline_images

    def message(self, *, policy: Policy | None = email.policy.default) -> EmailMessage:
        msg = super().message(policy=policy)
        html = next((p for p in msg.walk() if p.get_content_type() == "text/html"), None)
        if html is not None:
            for image in self.inline_images:
                html.add_related(
                    image.content,
                    maintype="image",
                    subtype=image.subtype,
                    cid=f"<{image.cid}>",
                    disposition="inline",
                    filename=image.filename,
                )
        return msg


def send_invoice_email(
    invoice_id: str,
    to: list[str] | str,
    subject: str,
    html: str = "",
    text: str = "",
    images: list[str] | None = None,
    kind: str = MailTemplate.Kind.INVOICE,
    body: str = "",
) -> None:
    """Send a rendered mail about the invoice. `body`: plain text queued before mails
    were HTML."""
    invoice = Invoice.objects.get(pk=invoice_id)
    inline = CompanyImage.objects.filter(owner=invoice.owner, key__in=images or [])
    mail = HtmlMail(
        subject=subject,
        body=text or body,
        # A single address: queued before mails went to several.
        to=[to] if isinstance(to, str) else to,
        inline_images=[_inline_image(image) for image in inline] if html else [],
    )
    if html:
        mail.attach_alternative(html, "text/html")
    for filename, content, mime in _attachments(invoice):
        mail.attach(filename, content, mime)
    mail.send()

    if kind == MailTemplate.Kind.INVOICE:
        invoice.status = Invoice.Status.SENT
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=["status", "sent_at", "updated_at"])
