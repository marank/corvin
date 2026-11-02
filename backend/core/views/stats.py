from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Invoice, Project, SupportContract, TimeEntry
from core.services.contracts import contract_usage


class DashboardStatsView(APIView):
    def get(self, request):
        user = request.user
        today = timezone.localdate()
        year_ago = today - timedelta(days=365)

        entries = TimeEntry.objects.filter(owner=user, end_datetime__isnull=False)
        invoices = Invoice.objects.filter(owner=user).exclude(status=Invoice.Status.CANCELLED)

        revenue_by_month = (
            invoices.filter(issue_date__gte=year_ago)
            .annotate(month=TruncMonth("issue_date"))
            .values("month")
            .annotate(total=Sum("total"))
            .order_by("month")
        )

        hours_by_customer = (
            entries.values("customer__name")
            .annotate(hours=Sum("duration_minutes") / 60.0)
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

        contracts = []
        for c in SupportContract.objects.filter(owner=user, active=True):
            contracts.append({"id": c.id, "name": c.name, **contract_usage(c)})

        budget_warnings = []
        for p in Project.objects.filter(owner=user).exclude(
            budget_hours__isnull=True, budget_amount__isnull=True
        ):
            from core.services.budgets import budget_stats

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
