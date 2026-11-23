from datetime import timedelta
from typing import Any

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Invoice, Project, SupportContract, TimeEntry
from core.request_helpers import request_user
from core.services.budgets import budget_stats
from core.services.contracts import contract_usage

_TOTAL = {"total": serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)}
_DASHBOARD = inline_serializer(
    "DashboardStats",
    {
        "revenue_by_month": inline_serializer(
            "MonthRevenue", {"month": serializers.DateField(), **_TOTAL}, many=True
        ),
        "hours_by_customer": inline_serializer(
            "CustomerHours",
            {"customer__name": serializers.CharField(), "hours": serializers.FloatField()},
            many=True,
        ),
        "uninvoiced_hours": serializers.FloatField(),
        "week_hours": serializers.FloatField(),
        "open_invoices": inline_serializer(
            "InvoiceSum", {**_TOTAL, "count": serializers.IntegerField()}
        ),
        "overdue": inline_serializer("OverdueSum", {**_TOTAL, "count": serializers.IntegerField()}),
        # Keys from services.contracts.contract_usage / services.budgets.budget_stats.
        "contracts": serializers.ListField(child=serializers.DictField()),
        "budget_warnings": serializers.ListField(child=serializers.DictField()),
        "timer_running": serializers.UUIDField(allow_null=True),
    },
)


class DashboardStatsView(APIView):
    @extend_schema(responses=_DASHBOARD)
    def get(self, request: Request) -> Response:
        user = request_user(request)
        today = timezone.localdate()
        year_ago = today - timedelta(days=365)

        entries = TimeEntry.objects.filter(owner=user, end_datetime__isnull=False)
        # drafts aren't revenue or receivables yet
        invoices = Invoice.objects.filter(owner=user).exclude(
            status__in=[Invoice.Status.CANCELLED, Invoice.Status.DRAFT]
        )

        revenue_by_month = (
            invoices.filter(issue_date__gte=year_ago)
            .annotate(month=TruncMonth("issue_date"))
            .values("month")
            .annotate(total=Sum("total"))
            .order_by("month")
        )

        hours_by_customer = (
            entries.values("customer__name")
            # django-stubs: "hours" clashes with the TimeEntry.hours property, though values()
            # rows are plain dicts and Django allows it.
            .annotate(hours=Sum("duration_minutes") / 60.0)  # type: ignore[no-redef, misc]  # see above
            .order_by("-hours")[:10]
        )

        uninvoiced = entries.filter(
            billable=True, invoice__isnull=True, contract__isnull=True
        ).aggregate(hours=Sum("duration_minutes"))

        week_start = today - timedelta(days=today.weekday())
        week_hours = entries.filter(start_datetime__date__gte=week_start).aggregate(
            hours=Sum("duration_minutes")
        )

        open_invoices = invoices.exclude(status=Invoice.Status.PAID).aggregate(
            total=Sum("total"), count=Count("id")
        )
        overdue = (
            invoices.filter(due_date__lt=today)
            .exclude(status=Invoice.Status.PAID)
            .aggregate(total=Sum("total"), count=Count("id"))
        )

        contracts: list[dict[str, Any]] = [
            {"id": c.id, "name": c.name, **contract_usage(c)}
            for c in SupportContract.objects.filter(owner=user, active=True)
        ]

        budget_warnings: list[dict[str, Any]] = []
        for p in Project.objects.filter(owner=user).exclude(
            budget_hours__isnull=True, budget_amount__isnull=True
        ):
            s = budget_stats(p)
            if (s["budget_hours_percent"] or 0) >= 80 or (s["budget_amount_percent"] or 0) >= 80:
                budget_warnings.append(
                    {"id": p.id, "name": p.name, "customer": p.customer.name, **s}
                )

        running = TimeEntry.objects.filter(owner=user, end_datetime__isnull=True).first()

        return Response(
            {
                "revenue_by_month": list(revenue_by_month),
                "hours_by_customer": list(hours_by_customer),
                "uninvoiced_hours": ((uninvoiced["hours"] or 0) / 60),
                "week_hours": (week_hours["hours"] or 0) / 60,
                "open_invoices": open_invoices,
                "overdue": overdue,
                "contracts": contracts,
                "budget_warnings": budget_warnings,
                "timer_running": running.id if running else None,
            }
        )
