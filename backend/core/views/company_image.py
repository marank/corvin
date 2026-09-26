from rest_framework.parsers import FormParser, MultiPartParser

from core.models import CompanyImage
from core.serializers import CompanyImageSerializer

from .base import OwnedViewSet


class CompanyImageViewSet(OwnedViewSet):
    queryset = CompanyImage.objects.all()
    serializer_class = CompanyImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["kind"]
    search_fields = ["key", "name"]
