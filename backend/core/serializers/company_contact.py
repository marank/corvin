from rest_framework import serializers

from core.models import CompanyContact

from .base import OwnedSerializer


class CompanyContactSerializer(OwnedSerializer):
    name = serializers.CharField(read_only=True)

    class Meta:
        model = CompanyContact
        fields = [
            "id", "first_name", "last_name", "name", "role", "email", "phone",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
