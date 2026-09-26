from rest_framework import serializers

from core.models import CompanyImage

from .base import OwnedSerializer


class CompanyImageSerializer(OwnedSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = CompanyImage
        fields = [
            "id", "kind", "key", "name", "image", "url",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    def validate(self, attrs):
        attrs = super().validate(attrs)
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        key = attrs.get("key", getattr(self.instance, "key", ""))
        if kind == CompanyImage.Kind.ADDITIONAL and not key:
            raise serializers.ValidationError({"key": "A key is required."})
        return attrs
