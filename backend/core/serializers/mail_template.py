from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.template import TemplateSyntaxError
from rest_framework import serializers

from core.models import MailTemplate
from core.services.mail_templates import (
    assigned_kinds,
    block_template,
    slot_names,
    validate_mail_template,
)

from .base import OwnedSerializer


class MailTemplateSerializer(OwnedSerializer[MailTemplate]):
    owner_fk_fields = ("base",)

    # The blocks this template offers to templates building on it.
    slot_names = serializers.SerializerMethodField()
    # Templates building on it, and the mail kinds it is assigned to (both block deleting).
    derived_count = serializers.SerializerMethodField()
    assigned_kinds = serializers.SerializerMethodField()

    class Meta:
        model = MailTemplate
        fields = [
            "id",
            "name",
            "subject",
            "base",
            "html",
            "slot_names",
            "derived_count",
            "assigned_kinds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_slot_names(self, obj: MailTemplate) -> list[str]:
        try:
            return slot_names(obj)
        except TemplateSyntaxError, DjangoValidationError:  # broken code: no slots
            return []

    def get_derived_count(self, obj: MailTemplate) -> int:
        return obj.derived.count()

    def get_assigned_kinds(self, obj: MailTemplate) -> list[str]:
        return assigned_kinds(obj)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        candidate = MailTemplate(
            **({"pk": self.instance.pk} if self.instance else {}),
            **{
                field: attrs.get(field, getattr(self.instance, field, default))
                for field, default in (("subject", ""), ("html", ""))
            },
            base=attrs.get("base", getattr(self.instance, "base", None)),
        )
        try:
            validate_mail_template(candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, "error_dict") else e.messages
            ) from e
        return attrs

    def create(self, validated_data: dict[str, Any]) -> MailTemplate:
        # A new template on a base starts with the base's blocks to fill in.
        base = validated_data.get("base")
        if base is not None and not validated_data.get("html", "").strip():
            validated_data["html"] = block_template(base)
        return super().create(validated_data)
