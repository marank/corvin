from typing import Any

from django.utils.translation import gettext as _
from rest_framework import serializers

from core.models import TimeEntry, TimeEntryBreak

from .base import OwnedSerializer


class TimeEntryBreakSerializer(serializers.ModelSerializer[TimeEntryBreak]):
    class Meta:
        model = TimeEntryBreak
        fields = ["id", "start_datetime", "end_datetime"]
        read_only_fields = ["id"]


class TimeEntrySerializer(OwnedSerializer[TimeEntry]):
    owner_fk_fields = ("customer", "project", "visit", "contract")

    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    contract_name = serializers.CharField(source="contract.name", read_only=True, default=None)
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default=None)
    hours = serializers.FloatField(read_only=True)
    is_running = serializers.BooleanField(read_only=True)
    breaks = TimeEntryBreakSerializer(many=True, required=False)
    break_minutes = serializers.SerializerMethodField(read_only=True)
    is_paused = serializers.SerializerMethodField(read_only=True)

    def get_break_minutes(self, obj: TimeEntry) -> int:
        return obj._break_minutes()

    def get_is_paused(self, obj: TimeEntry) -> bool:
        return obj.breaks.filter(end_datetime__isnull=True).exists()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        visit = attrs.get("visit", getattr(self.instance, "visit", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if visit and customer and visit.customer_id != customer.id:
            raise serializers.ValidationError(
                {"visit": _("The visit belongs to another customer.")}
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> TimeEntry:
        breaks_data = validated_data.pop("breaks", [])
        instance = super().create(validated_data)
        if breaks_data:
            self._sync_breaks(instance, breaks_data)
            instance.save()
        return instance

    def update(self, instance: TimeEntry, validated_data: dict[str, Any]) -> TimeEntry:
        breaks_data = validated_data.pop("breaks", None)
        instance = super().update(instance, validated_data)
        if breaks_data is not None:
            self._sync_breaks(instance, breaks_data)
        instance.save()
        return instance

    @staticmethod
    def _sync_breaks(instance: TimeEntry, breaks_data: list[dict[str, Any]]) -> None:
        existing = {str(b.id): b for b in instance.breaks.all()}
        kept_ids = set()
        for b_data in breaks_data:
            bid = b_data.get("id")
            if bid and bid in existing:
                b = existing[bid]
                b.start_datetime = b_data.get("start_datetime", b.start_datetime)
                b.end_datetime = b_data.get("end_datetime", b.end_datetime)
                b.save()
                kept_ids.add(bid)
            else:
                TimeEntryBreak.objects.create(
                    owner=instance.owner,
                    time_entry=instance,
                    start_datetime=b_data["start_datetime"],
                    end_datetime=b_data.get("end_datetime"),
                )
        for bid, b in existing.items():
            if bid not in kept_ids:
                b.delete()

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "customer",
            "customer_name",
            "project",
            "project_name",
            "visit",
            "contract",
            "contract_name",
            "invoice_number",
            "start_datetime",
            "end_datetime",
            "normalized_start_datetime",
            "normalized_end_datetime",
            "breaks",
            "break_minutes",
            "duration_minutes",
            "hours",
            "is_running",
            "is_paused",
            "description",
            "report",
            "billable",
            "invoice",
            "created_at",
            "updated_at",
        ]
        # Invoicing links entries to invoices (creating or editing one), never this API.
        read_only_fields = ["duration_minutes", "invoice", "created_at", "updated_at"]
