from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request

from core.models import CompanyImage
from core.serializers import CompanyImageSerializer

from .base import OwnedViewSet, serve_file


class CompanyImageViewSet(OwnedViewSet[CompanyImage]):
    queryset = CompanyImage.objects.all()
    serializer_class = CompanyImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["kind"]
    search_fields = ["key", "name"]

    @action(detail=True, methods=["get"])
    def file(self, request: Request, pk: str | None = None) -> FileResponse:
        image = self.get_object()
        return serve_file(image.image, (image.image.name or "").rsplit("/", 1)[-1])
