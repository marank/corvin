import json

from django.conf import settings
from django.http import HttpResponse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import override
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import DocumentTemplate
from core.serializers import DocumentTemplateSerializer
from core.services.pdf import render_document_html, write_pdf
from core.services.sample_invoice import sample_template_context
from core.services.templates import ensure_default_template, forget_template_assignments

from .base import OwnedViewSet


class DocumentTemplateViewSet(OwnedViewSet):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "page_size", "created_at"]

    def list(self, request, *args, **kwargs):
        ensure_default_template(request.user)
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance):
        forget_template_assignments(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"], url_path="export")
    def export_template(self, request, pk=None):
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
    def import_template(self, request):
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

    def _preview_html(self, request, template, for_pdf=False):
        """The template rendered with sample data; images from disk for PDFs, else via the API."""
        data = sample_template_context(request.user, for_pdf)
        if not for_pdf:
            data["images"] = {
                key: request.build_absolute_uri(url) for key, url in data["images"].items()
            }
        return render_document_html(template, data, request.user)

    def _preview_template(self, request):
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
    def preview(self, request, pk=None):
        """Render the template with sample data (HTML)."""
        html = self._preview_html(request, self._preview_template(request))
        return HttpResponse(html, content_type="text/html")

    @action(detail=True, methods=["get", "post"], url_path="preview-pdf")
    @override(settings.LANGUAGE_CODE)
    def preview_pdf(self, request, pk=None):
        """Render the template with sample data as a PDF (inline)."""
        html = self._preview_html(request, self._preview_template(request), for_pdf=True)
        return HttpResponse(
            write_pdf(html, request.user),
            content_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
