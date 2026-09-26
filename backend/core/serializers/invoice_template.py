from core.models import InvoiceTemplate

from .base import OwnedSerializer


class InvoiceTemplateSerializer(OwnedSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = [
            "id", "name", "page_size",
            "margin_top", "margin_right", "margin_bottom", "margin_left",
            "body_html", "css", "header_html", "footer_html",
            "mail_subject", "mail_body", "is_default",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
