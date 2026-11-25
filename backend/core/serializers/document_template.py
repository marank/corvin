from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from core.models import DocumentTemplate

from .base import OwnedSerializer, validate_template_syntax

COLOR_FIELDS = (
    "primary_color",
    "secondary_color",
    "tertiary_color",
    "background_color",
    "text_color",
)
FONT_FIELDS = ("primary_font", "secondary_font")
# The values land verbatim in the template's CSS ({{ page.primary_color }}).
validate_color = RegexValidator(
    r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]+|(rgb|rgba|hsl|hsla)\([0-9.,%/\s]+\))$",
    _("Enter a CSS color, e.g. #1f2937."),
)
validate_font = RegexValidator(
    r"^[^;{}<>\\]+$", _("Font names must not contain ; { } < > or backslashes.")
)
TEMPLATE_FIELDS = ("body_html", "css", "header_html", "footer_html", "mail_subject", "mail_body")


class DocumentTemplateSerializer(OwnedSerializer[DocumentTemplate]):
    class Meta:
        model = DocumentTemplate
        fields = [
            "id",
            "name",
            "page_size",
            "margin_top",
            "margin_right",
            "margin_bottom",
            "margin_left",
            "header_height",
            "footer_height",
            "font_size",
            "primary_font",
            "secondary_font",
            "primary_color",
            "secondary_color",
            "tertiary_color",
            "background_color",
            "text_color",
            "body_html",
            "css",
            "header_html",
            "footer_html",
            "mail_subject",
            "mail_body",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {
            **{field: {"validators": [validate_template_syntax]} for field in TEMPLATE_FIELDS},
            **{field: {"validators": [validate_color]} for field in COLOR_FIELDS},
            **{field: {"validators": [validate_font]} for field in FONT_FIELDS},
        }
