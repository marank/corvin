from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .base import OwnedModel


class DocumentArchive(OwnedModel):
    """Immutable archived document written at document finalize (GoBD)."""

    class Kind(models.TextChoices):
        PDF = "pdf", "PDF"
        XML = "xml", "XML (e-invoice)"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(upload_to="document_archives/%Y/%m/")
    sha256 = models.CharField(max_length=64)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "kind"], name="unique_doc_kind_per_object"
            )
        ]

    def __str__(self) -> str:
        return f"{self.content_object} ({self.kind})"
