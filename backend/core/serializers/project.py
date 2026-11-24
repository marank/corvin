from decimal import Decimal

from rest_framework import serializers

from core.models import Project
from core.services.budgets import BudgetStats, budget_stats

from .base import LockableNumberSerializer


class ProjectSerializer(LockableNumberSerializer[Project]):
    owner_fk_fields = ("customer",)

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    used_hours = serializers.SerializerMethodField()
    used_amount = serializers.SerializerMethodField()
    budget_hours_percent = serializers.SerializerMethodField()
    budget_amount_percent = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "number",
            "number_locked",
            "customer",
            "customer_name",
            "name",
            "description",
            "status",
            "budget_hours",
            "budget_amount",
            "rounding_increment_minutes",
            "used_hours",
            "used_amount",
            "budget_hours_percent",
            "budget_amount_percent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def _stats(self, obj: Project) -> BudgetStats:
        stats: BudgetStats | None = getattr(obj, "_budget_stats", None)
        if stats is None:
            stats = budget_stats(obj)
            obj._budget_stats = stats  # type: ignore[attr-defined]  # per-instance cache
        return stats

    def get_used_hours(self, obj: Project) -> Decimal:
        return self._stats(obj)["used_hours"]

    def get_used_amount(self, obj: Project) -> Decimal:
        return self._stats(obj)["used_amount"]

    def get_budget_hours_percent(self, obj: Project) -> float | None:
        return self._stats(obj)["budget_hours_percent"]

    def get_budget_amount_percent(self, obj: Project) -> float | None:
        return self._stats(obj)["budget_amount_percent"]
