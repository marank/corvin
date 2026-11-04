from django.template import Template, TemplateSyntaxError
from django.utils.translation import gettext as _
from rest_framework import serializers


def validate_template_syntax(value: str) -> str:
    """Reject markup that would only fail later, when an invoice or mail is rendered."""
    try:
        Template(value)
    except TemplateSyntaxError as e:
        raise serializers.ValidationError(_("Invalid template: %(error)s") % {"error": e}) from e
    return value


class OwnedSerializer(serializers.ModelSerializer):
    """Sets owner from the request and scopes FK fields to the owner."""

    owner_fk_fields: tuple[str, ...] = ()

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)

    def get_fields(self):
        fields = super().get_fields()
        user = self.context["request"].user
        for name in self.owner_fk_fields:
            field = fields.get(name)
            if field is not None and hasattr(field, "queryset"):
                field.queryset = field.queryset.filter(owner=user)
        return fields

    def validate(self, attrs):
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
