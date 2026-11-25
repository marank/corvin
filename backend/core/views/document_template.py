import json
from typing import Any

from django.conf import settings
from django.http import HttpResponse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import override
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import DocumentTemplate
from core.request_helpers import request_user
from core.serializers import DocumentTemplateSerializer
from core.services.pdf import render_document_html, write_document_pdf
from core.services.sample_invoice import sample_template_context
from core.services.templates import ensure_default_template, forget_template_assignments

from .base import OwnedViewSet


class DocumentTemplateViewSet(OwnedViewSet[DocumentTemplate]):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "page_size", "created_at"]

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ensure_default_template(request_user(request))
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance: DocumentTemplate) -> None:
        # The list would recreate the default right away, so the delete would seem to fail.
        if (
            not DocumentTemplate.objects.filter(owner=instance.owner)
            .exclude(pk=instance.pk)
            .exists()
        ):
            raise ValidationError(_("The last template cannot be deleted."))
        forget_template_assignments(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"], url_path="export")
    def export_template(self, request: Request, pk: str | None = None) -> HttpResponse:
        template = self.get_object()
        data = DocumentTemplateSerializer(template, context={"request": request}).data
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)
        payload = {
            "format": "corvin.document-template",
            "version": 1,
            "template": data,
        }
        filename = slugify(template.name) or "document-template"
        return HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

    @action(detail=False, methods=["post"], url_path="import")
    def import_template(self, request: Request) -> Response:
        payload = request.data
        if not isinstance(payload, dict):
            return Response(
                {"detail": _("Invalid template file.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            payload.get("format") != "corvin.document-template"
            or payload.get("version") != 1
            or not isinstance(payload.get("template"), dict)
        ):
            return Response(
                {"detail": _("Unsupported template format or version.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = {**payload["template"]}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return Response(
            self.get_serializer(template).data,
            status=status.HTTP_201_CREATED,
        )

    def _preview_data(self, request: Request, for_pdf: bool = False) -> dict[str, Any]:
        """Sample data; images from disk for PDFs, else via the API."""
        data = sample_template_context(request_user(request), for_pdf)
        if not for_pdf:
            data["images"] = {
                key: request.build_absolute_uri(url) for key, url in data["images"].items()
            }
        return data

    def _preview_template(self, request: Request) -> DocumentTemplate:
        """The stored template; a POST previews unsaved designer changes without storing them."""
        template = self.get_object()
        if request.method == "POST":
            serializer = self.get_serializer(template, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            for field, value in serializer.validated_data.items():
                setattr(template, field, value)
        return template

    @xframe_options_exempt
    @action(detail=True, methods=["get", "post"])
    @override(settings.LANGUAGE_CODE)
    def preview(self, request: Request, pk: str | None = None) -> HttpResponse:
        """Render the template with sample data (HTML)."""
        template = self._preview_template(request)
        html = render_document_html(template, self._preview_data(request), request_user(request))
        return HttpResponse(html, content_type="text/html")

    @action(detail=True, methods=["get", "post"], url_path="preview-pdf")
    @override(settings.LANGUAGE_CODE)
    def preview_pdf(self, request: Request, pk: str | None = None) -> HttpResponse:
        """Render the template with sample data as a PDF (inline)."""
        template = self._preview_template(request)
        data = self._preview_data(request, for_pdf=True)
        return HttpResponse(
            write_document_pdf(template, data, request_user(request)),
            content_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
