from django.db import models

from .base import OwnedModel

PAGE_DIMENSIONS = {
    "A3": ("297mm", "420mm"),
    "A4": ("210mm", "297mm"),
    "A5": ("148mm", "210mm"),
    "LETTER": ("8.5in", "11in"),
    "LEGAL": ("8.5in", "14in"),
    "TABLOID": ("11in", "17in"),
}


class DocumentTemplate(OwnedModel):
    class PageSize(models.TextChoices):
        A3 = "A3", "DIN A3"
        A4 = "A4", "DIN A4"
        A5 = "A5", "DIN A5"
        LETTER = "LETTER", "US Letter"
        LEGAL = "LEGAL", "US Legal"
        TABLOID = "TABLOID", "US Tabloid"

    name = models.CharField(max_length=255)
    page_size = models.CharField(max_length=10, choices=PageSize.choices, default=PageSize.A4)
    margin_top = models.PositiveIntegerField(default=20, help_text="mm")
    margin_right = models.PositiveIntegerField(default=20, help_text="mm")
    margin_bottom = models.PositiveIntegerField(default=20, help_text="mm")
    margin_left = models.PositiveIntegerField(default=25, help_text="mm")
    # Room header and footer get inside the margins; the content flows in between.
    header_height = models.PositiveIntegerField(default=0, help_text="mm")
    footer_height = models.PositiveIntegerField(default=0, help_text="mm")
    font_size = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    primary_font = models.CharField(max_length=255, default="Arial")
    secondary_font = models.CharField(max_length=255, default="Helvetica")
    primary_color = models.CharField(max_length=20, default="#161616")
    secondary_color = models.CharField(max_length=20, default="#555555")
    tertiary_color = models.CharField(max_length=20, default="#999999")
    background_color = models.CharField(max_length=20, default="#ffffff")
    text_color = models.CharField(max_length=20, default="#161616")
    body_html = models.TextField(
        blank=True,
        help_text="Django template markup: {{ invoice.number }}, {% for item in items %}...",
    )
    css = models.TextField(blank=True)
    header_html = models.TextField(blank=True)
    footer_html = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    @property
    def page_width(self) -> str:
        return PAGE_DIMENSIONS[self.page_size][0]

    @property
    def page_height(self) -> str:
        return PAGE_DIMENSIONS[self.page_size][1]

    def __str__(self) -> str:
        return self.name
