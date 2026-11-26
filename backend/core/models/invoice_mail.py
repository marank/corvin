from django.db import models

from .base import OwnedModel
from .invoice import Invoice
from .mail_template import MailTemplate


class InvoiceMail(OwnedModel):
    """A mail about an invoice as it was sent (or is waiting to be): the history of what
    went to whom. Rendered when the user sent it; the job sends exactly this."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="mails")
    kind = models.CharField(max_length=20, choices=MailTemplate.Kind.choices)
    to = models.JSONField(default=list)
    subject = models.CharField(max_length=255)
    html = models.TextField(blank=True)
    text = models.TextField(blank=True)
    # Keys of the company images shown inline, and the names of the attached files.
    images = models.JSONField(default=list, blank=True)
    attachments = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    sent_at = models.DateTimeField(null=True, blank=True)
    # The last failed attempt (the queue retries); empty once sent.
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.invoice} → {', '.join(self.to)} ({self.kind})"
