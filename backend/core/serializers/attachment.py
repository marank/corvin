from django.urls import reverse
from rest_framework import serializers

from core.models import Attachment

from .base import OwnedSerializer


class AttachmentSerializer(OwnedSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "file",
            "url",
            "name",
            "uploaded_at",
            "content_type",
            "object_id",
        ]
        read_only_fields = ["name", "uploaded_at"]

    def get_url(self, obj):
        request = self.context.get("request")
        url = reverse("attachment-file", args=[obj.pk])
        return request.build_absolute_uri(url) if request else url
