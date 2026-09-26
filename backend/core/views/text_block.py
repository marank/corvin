from core.models import TextBlock
from core.serializers import TextBlockSerializer

from .base import OwnedViewSet


class TextBlockViewSet(OwnedViewSet):
    queryset = TextBlock.objects.all()
    serializer_class = TextBlockSerializer
    search_fields = ["name", "key", "content"]
    ordering_fields = ["name", "key", "created_at"]
