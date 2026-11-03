import mimetypes

from django.db import transaction
from django.db.models import ProtectedError
from django.http import FileResponse, Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError


class OwnedViewSet(viewsets.ModelViewSet):
    """Scopes all queries to the requesting user."""

    # Shown when an on_delete=PROTECT relation blocks a delete; override per resource.
    protected_message = _("This entry is still used by other records and cannot be deleted.")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_destroy(self, instance):
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


def serve_file(field_file, filename: str) -> FileResponse:
    """Stream an uploaded file after the caller has checked ownership."""
    if not field_file:
        raise Http404
    content_type, _ = mimetypes.guess_type(filename)
    return FileResponse(
        field_file.open("rb"),
        filename=filename,
        as_attachment=content_type not in INLINE_CONTENT_TYPES,
    )
