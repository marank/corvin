from core.models import DocumentTemplate

from .base import OwnedSerializer, validate_template_syntax

TEMPLATE_FIELDS = ("body_html", "css", "header_html", "footer_html", "mail_subject", "mail_body")


class DocumentTemplateSerializer(OwnedSerializer):
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
            field: {"validators": [validate_template_syntax]} for field in TEMPLATE_FIELDS
        }
