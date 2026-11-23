from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from core.models import Customer, HourlyRate, Project


def resolve_rate(
    *, owner: User, customer: Customer, project: Project | None, on_date: date
) -> Decimal | None:
    """Resolve the effective hourly rate for a date.

    Specificity: project > customer > company default.
    Within a scope the row with the latest valid_from <= on_date wins.
    """
    qs = HourlyRate.objects.filter(owner=owner, valid_from__lte=on_date).order_by("-valid_from")
    if project is not None:
        rate = qs.filter(project=project).first()
        if rate:
            return rate.amount
    rate = qs.filter(customer=customer, project__isnull=True).first()
    if rate:
        return rate.amount
    rate = qs.filter(customer__isnull=True, project__isnull=True).first()
    return rate.amount if rate else None


def round_up_minutes(minutes: int, increment: int | None) -> int:
    """Round minutes up to the given increment (e.g. 15)."""
    if not increment:
        return minutes
    return increment * -(-minutes // increment)


def rounding_increment(customer: Customer, project: Project | None) -> int | None:
    if project and project.rounding_increment_minutes:
        return project.rounding_increment_minutes
    return customer.rounding_increment_minutes
