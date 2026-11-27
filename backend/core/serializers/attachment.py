from django.urls import reverse
from rest_framework import serializers

from core.models import Attachment
from core.services.file_preview import PreviewKind, preview_kind

from .base import OwnedSerializer


class AttachmentSerializer(OwnedSerializer[Attachment]):
    url = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "file",
            "url",
            "name",
            "size",
            "preview",
            "uploaded_at",
            "content_type",
            "object_id",
        ]
        read_only_fields = ["name", "uploaded_at"]

    def get_url(self, obj: Attachment) -> str:
        # Relative: the browser resolves it against the address Corvin was opened under;
        # behind nginx the request's Host has no port, so an absolute URL would point elsewhere.
        return reverse("attachment-file", args=[obj.pk])

    def get_size(self, obj: Attachment) -> int | None:
        try:
            return int(obj.file.size)
        except OSError, ValueError:
            return None

    def get_preview(self, obj: Attachment) -> PreviewKind | None:
        return preview_kind(obj.name, self.get_size(obj))
