from rest_framework import serializers

from core.models import Attachment

from .base import OwnedSerializer


class AttachmentSerializer(OwnedSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id", "file", "url", "name", "uploaded_at",
            "content_type", "object_id",
        ]
        read_only_fields = ["name", "uploaded_at"]

    def get_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url
