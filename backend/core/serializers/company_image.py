from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework import serializers

from core.models import CompanyImage

from .base import OwnedSerializer


class CompanyImageSerializer(OwnedSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = CompanyImage
        fields = [
            "id",
            "kind",
            "key",
            "name",
            "image",
            "url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        url = reverse("company-image-file", args=[obj.pk])
        return request.build_absolute_uri(url) if request else url

    def validate(self, attrs):
        attrs = super().validate(attrs)
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        key = attrs.get("key", getattr(self.instance, "key", ""))
        if kind == CompanyImage.Kind.ADDITIONAL and not key:
            raise serializers.ValidationError({"key": _("A key is required.")})
        return attrs
