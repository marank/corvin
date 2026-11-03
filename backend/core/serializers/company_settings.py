from django.utils.translation import gettext as _
from rest_framework import serializers

from core.models import BankAccount, CompanySettings, DocumentTemplate
from core.models.company_settings import NUMBERING_SCHEMES
from core.services.numbering import normalize_scope

REPORT_TYPES = [
    "invoice",
    "credit_note",
    "quote",
    "order",
    "delivery_note",
    "timesheet",
]


class CompanySettingsSerializer(serializers.ModelSerializer):
    decimal_separator = serializers.CharField(max_length=1, trim_whitespace=False)
    thousands_separator = serializers.CharField(max_length=1, trim_whitespace=False)
    default_bank_account = serializers.PrimaryKeyRelatedField(
        queryset=BankAccount.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = CompanySettings
        exclude = ["id", "user"]

    def validate(self, attrs):
        instance = self.instance
        decimal = attrs.get("decimal_separator", getattr(instance, "decimal_separator", ","))
        thousands = attrs.get("thousands_separator", getattr(instance, "thousands_separator", "."))
        bank_account = attrs.get("default_bank_account")
        if bank_account and bank_account.owner_id != instance.user_id:
            raise serializers.ValidationError({"default_bank_account": _("Invalid bank account.")})
        if decimal == thousands:
            raise serializers.ValidationError(
                {"thousands_separator": _("Must differ from decimal separator.")}
            )
        currency = attrs.get("currency")
        if currency is not None:
            attrs["currency"] = currency.upper()
        for field in (
            "time_rounding_start_minutes",
            "time_rounding_end_minutes",
        ):
            value = attrs.get(field)
            if value is not None and value < 1:
                raise serializers.ValidationError({field: _("Must be a positive integer.")})
        return attrs

    def validate_currency(self, value):
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError(_("Use a three-letter ISO currency code."))
        return value.upper()

    def validate_numbering_schemes(self, value):
        unknown = set(value) - set(NUMBERING_SCHEMES)
        if unknown:
            raise serializers.ValidationError(
                _("Unknown entities: %(names)s.") % {"names": ", ".join(sorted(unknown))}
            )
        result = {}
        for entity, default in NUMBERING_SCHEMES.items():
            scheme = {**default, **value.get(entity, {})}
            raw_scope = scheme["scope"]
            valid_legacy = {
                "global",
                "year",
                "customer",
                "customer_year",
                "project",
                "project_year",
            }
            if not isinstance(raw_scope, list) and raw_scope not in valid_legacy:
                raise serializers.ValidationError({entity: {"scope": _("Invalid counter scope.")}})
            if isinstance(raw_scope, list) and any(
                item not in {"year", "customer", "project"} for item in raw_scope
            ):
                raise serializers.ValidationError({entity: {"scope": _("Invalid counter scope.")}})
            scheme["scope"] = normalize_scope(raw_scope)
            if not isinstance(scheme["format"], str) or not scheme["format"]:
                raise serializers.ValidationError({entity: {"format": _("A format is required.")}})
            if len(scheme["format"]) > 200:
                raise serializers.ValidationError(
                    {entity: {"format": _("Maximum length is 200 characters.")}}
                )
            if not isinstance(scheme["start"], int) or scheme["start"] < 1:
                raise serializers.ValidationError(
                    {entity: {"start": _("Must be a positive integer.")}}
                )
            result[entity] = scheme
        return result

    def validate_template_assignments(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Must be an object."))
        unknown = set(value) - set(REPORT_TYPES)
        if unknown:
            raise serializers.ValidationError(
                _("Unknown report types: %(names)s.") % {"names": ", ".join(sorted(unknown))}
            )
        user = self.instance.user
        for report_type, template_id in value.items():
            if template_id is None:
                continue
            if not DocumentTemplate.objects.filter(
                id=template_id,
                owner=user,
            ).exists():
                raise serializers.ValidationError({report_type: _("Invalid template.")})
        return value
