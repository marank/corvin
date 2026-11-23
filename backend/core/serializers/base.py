from typing import Any

from django.db.models import Model, QuerySet
from django.template import Template, TemplateSyntaxError
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.fields import Field

from core.models.base import OwnedModel


def validate_template_syntax(value: str) -> None:
    """Reject markup that would only fail later, when an invoice or mail is rendered."""
    try:
        Template(value)
    except TemplateSyntaxError as e:
        raise serializers.ValidationError(_("Invalid template: %(error)s") % {"error": e}) from e


class OwnedSerializer[M: OwnedModel](serializers.ModelSerializer[M]):
    """Sets owner from the request and scopes FK fields to the owner."""

    owner_fk_fields: tuple[str, ...] = ()

    def create(self, validated_data: dict[str, Any]) -> M:
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)

    def get_fields(self) -> dict[str, Field[Any, Any, Any, Any]]:
        fields = super().get_fields()
        for name in self.owner_fk_fields:
            field = fields.get(name)
            if field is not None and hasattr(field, "queryset"):
                field.queryset = self.owned(field.queryset)
        return fields

    def owned[Q: Model](self, queryset: QuerySet[Q]) -> QuerySet[Q]:
        """The requesting user's objects; none without a user (the OpenAPI export)."""
        user = self.context["request"].user
        return queryset.filter(owner=user) if user.is_authenticated else queryset.none()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        obj = self.instance
        merged = {**{f: getattr(obj, f, None) for f in self.Meta.fields}, **attrs} if obj else attrs
        # enforce same-owner integrity on FK fields
        for name in self.owner_fk_fields:
            rel = merged.get(name)
            if (
                rel is not None
                and getattr(rel, "owner_id", None) != self.context["request"].user.id
            ):
                raise serializers.ValidationError({name: _("Invalid object.")})
        return attrs
