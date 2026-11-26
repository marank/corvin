from typing import Any

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import override
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import MailTemplate
from core.request_helpers import request_user
from core.serializers import MailTemplateSerializer
from core.services.mail_templates import (
    assigned_kinds,
    ensure_mail_templates,
    render_mail,
)
from core.services.mailer import mail_context
from core.services.sample_invoice import sample_template_context

from .base import OwnedViewSet

PREVIEW = inline_serializer(
    "MailPreview", {"subject": serializers.CharField(), "html": serializers.CharField()}
)


class MailTemplateViewSet(OwnedViewSet[MailTemplate]):
    queryset = MailTemplate.objects.select_related("base")
    serializer_class = MailTemplateSerializer
    search_fields = ["name", "subject"]
    ordering_fields = ["name", "created_at"]

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ensure_mail_templates(request_user(request))
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance: MailTemplate) -> None:
        if assigned_kinds(instance):
            raise ValidationError(_("The template is assigned to a mail kind."))
        derived = list(instance.derived.values_list("name", flat=True))
        if derived:
            raise ValidationError(
                _("Templates build on it: %(names)s.") % {"names": ", ".join(derived)}
            )
        super().perform_destroy(instance)

    @extend_schema(request=None, responses={201: MailTemplateSerializer})
    @action(detail=True, methods=["post"])
    def duplicate(self, request: Request, pk: str | None = None) -> Response:
        template = self.get_object()
        copy = MailTemplate.objects.create(
            owner=template.owner,
            name=_("%(name)s (copy)") % {"name": template.name},
            subject=template.subject,
            base=template.base,
            html=template.html,
        )
        data = self.get_serializer(copy).data
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(request=MailTemplateSerializer, responses=PREVIEW)
    @action(detail=True, methods=["get", "post"])
    @override(settings.LANGUAGE_CODE)
    def preview(self, request: Request, pk: str | None = None) -> Response:
        """The mail with sample data; a POST previews unsaved changes without storing them."""
        template = self.get_object()
        if request.method == "POST":
            serializer = self.get_serializer(template, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            for field, value in serializer.validated_data.items():
                setattr(template, field, value)
        owner = request_user(request)
        sample = sample_template_context(owner)
        data = mail_context(owner, sample, sample["invoice_contacts"])
        mail = render_mail(template, data, inline_images=False)
        return Response({"subject": mail.subject, "html": mail.html})
