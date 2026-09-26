from core.models import TextBlock

from .base import OwnedSerializer


class TextBlockSerializer(OwnedSerializer):
    class Meta:
        model = TextBlock
        fields = [
            "id", "name", "key", "content",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
