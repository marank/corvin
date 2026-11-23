from core.models import TextBlock

from .base import OwnedSerializer, validate_template_syntax


class TextBlockSerializer(OwnedSerializer[TextBlock]):
    class Meta:
        model = TextBlock
        fields = [
            "id",
            "name",
            "key",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"content": {"validators": [validate_template_syntax]}}
