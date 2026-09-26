from rest_framework import serializers

from core.models import CompanySettings


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        exclude = ["id", "user"]
