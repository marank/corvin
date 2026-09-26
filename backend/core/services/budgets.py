from decimal import Decimal

from core.models import Project

from .rates import resolve_rate


def budget_stats(project: Project) -> dict:
    """Used hours/amount + burn-down percentages for a project."""
    entries = project.time_entries.filter(end_time__isnull=False)
    used_minutes = sum(e.duration_minutes for e in entries)
    used_hours = Decimal(used_minutes) / 60
    amount = Decimal("0")
    for e in entries.select_related("project__customer"):
        rate = resolve_rate(
            owner=project.owner,
            customer=project.customer,
            project=project,
            on_date=e.date,
        ) or Decimal("0")
        amount += Decimal(e.duration_minutes) / 60 * rate
    return {
        "used_hours": used_hours.quantize(Decimal("0.01")),
        "used_amount": amount.quantize(Decimal("0.01")),
        "budget_hours_percent": (
            round(float(used_hours / project.budget_hours * 100), 1)
            if project.budget_hours
            else None
        ),
        "budget_amount_percent": (
            round(float(amount / project.budget_amount * 100), 1)
            if project.budget_amount
            else None
        ),
    }
