import mimetypes
from typing import Any

from django.db import transaction
from django.db.models import ProtectedError, QuerySet
from django.db.models.fields.files import FieldFile
from django.http import FileResponse, Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from core.models.base import OwnedModel


class OwnedViewSet[M: OwnedModel](viewsets.ModelViewSet[M]):
    """Scopes all queries to the requesting user."""

    # Shown when an on_delete=PROTECT relation blocks a delete; override per resource.
    protected_message = _("This entry is still used by other records and cannot be deleted.")

    @transaction.atomic
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().create(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[M]:
        if getattr(self, "swagger_fake_view", False):
            # The OpenAPI export inspects the view without a signed-in user.
            return super().get_queryset().none()
        return super().get_queryset().filter(owner=self.request.user)

    def perform_destroy(self, instance: M) -> None:
        try:
            super().perform_destroy(instance)
        except ProtectedError as e:
            raise ValidationError(self.protected_message) from e


# Served inline (viewable in the browser); everything else is forced to download
# so user-uploaded HTML/SVG can never run as same-origin content.
INLINE_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}


def serve_file(field_file: FieldFile, filename: str) -> FileResponse:
    """Stream an uploaded file after the caller has checked ownership."""
    if not field_file:
        raise Http404
    content_type, _ = mimetypes.guess_type(filename)
    return FileResponse(
        field_file.open("rb"),
        filename=filename,
        as_attachment=content_type not in INLINE_CONTENT_TYPES,
    )
