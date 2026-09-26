from django.db import models

from .base import OwnedModel


class InvoiceTemplate(OwnedModel):
    class PageSize(models.TextChoices):
        A4 = "A4", "DIN A4"
        LETTER = "LETTER", "US Letter"

    name = models.CharField(max_length=255)
    page_size = models.CharField(
        max_length=10, choices=PageSize.choices, default=PageSize.A4
    )
    margin_top = models.PositiveIntegerField(default=20, help_text="mm")
    margin_right = models.PositiveIntegerField(default=20, help_text="mm")
    margin_bottom = models.PositiveIntegerField(default=20, help_text="mm")
    margin_left = models.PositiveIntegerField(default=25, help_text="mm")
    body_html = models.TextField(
        help_text="Django template markup: {{ invoice.number }}, "
                  "{% for item in items %}..."
    )
    css = models.TextField(blank=True)
    header_html = models.TextField(blank=True)
    footer_html = models.TextField(blank=True)
    mail_subject = models.CharField(
        max_length=255, blank=True,
        default="Invoice {{ invoice.number }}",
    )
    mail_body = models.TextField(
        blank=True, default="Dear customer,\n\nplease find attached your invoice."
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            type(self).objects.filter(owner=self.owner).exclude(pk=self.pk).update(
                is_default=False
            )

    def __str__(self):
        return self.name
