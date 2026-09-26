from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import CompanySettings
from core.serializers import CompanySettingsSerializer


class CompanySettingsView(APIView):
    """Singleton per user — GET/PUT /settings/."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        obj, _ = CompanySettings.objects.get_or_create(user=request.user)
        return Response(CompanySettingsSerializer(obj).data)

    def put(self, request):
        obj, _ = CompanySettings.objects.get_or_create(user=request.user)
        ser = CompanySettingsSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)
