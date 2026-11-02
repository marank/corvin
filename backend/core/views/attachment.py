from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from core.models import Attachment
from core.serializers import AttachmentSerializer

from .base import OwnedViewSet, serve_file

ATTACHABLE_MODELS = [
    "customer",
    "project",
    "onsitevisit",
    "invoice",
    "supportcontract",
]


class AttachmentViewSet(OwnedViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["content_type", "object_id"]

    @action(detail=False, methods=["get"])
    def content_types(self, request):
        return Response(
            {
                m: ContentType.objects.get(app_label="core", model=m).id
                for m in ATTACHABLE_MODELS
            }
        )

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        attachment = self.get_object()
        return serve_file(attachment.file, attachment.name)
