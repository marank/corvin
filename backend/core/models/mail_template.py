from django.db import models

from .base import OwnedModel


class MailTemplate(OwnedModel):
    """An e-mail as HTML with template variables.

    Without a base it is the whole mail; its `{% block name %}` tags are blocks other
    templates can fill. With a base its HTML is only blocks, overriding the base's;
    blocks it leaves out (or fills with `{{ block.super }}`) keep the base's content.
    """

    class Kind(models.TextChoices):
        INVOICE = "invoice", "Invoice"
        PAYMENT_REMINDER = "payment_reminder", "Payment reminder"

    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    base = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="derived"
    )
    html = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
