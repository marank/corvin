from datetime import date
from decimal import Decimal

import pytest

from core.models import HourlyRate, Project
from core.services.rates import resolve_rate


@pytest.mark.django_db
def test_default_rate(user, customer, project):
    HourlyRate.objects.create(owner=user, amount=Decimal(80), valid_from=date(2025, 1, 1))
    assert resolve_rate(
        owner=user, customer=customer, project=project, on_date=date(2026, 6, 1)
    ) == Decimal(80)


@pytest.mark.django_db
def test_boundary_rate_increase(user, customer, project):
    """80 €/h until year end, 85 €/h from Jan 1 — boundary inclusive."""
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal(80),
        valid_from=date(2025, 1, 1),
    )
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal(85),
        valid_from=date(2026, 1, 1),
    )
    assert resolve_rate(
        owner=user,
        customer=customer,
        project=project,
        on_date=date(2025, 12, 31),
    ) == Decimal(80)
    assert resolve_rate(
        owner=user,
        customer=customer,
        project=project,
        on_date=date(2026, 1, 1),
    ) == Decimal(85)


@pytest.mark.django_db
def test_specificity_project_over_customer_over_default(user, customer, project):
    HourlyRate.objects.create(owner=user, amount=Decimal(70), valid_from=date(2025, 1, 1))
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal(80),
        valid_from=date(2025, 1, 1),
    )
    HourlyRate.objects.create(
        owner=user,
        project=project,
        amount=Decimal(95),
        valid_from=date(2025, 6, 1),
    )
    assert resolve_rate(
        owner=user,
        customer=customer,
        project=project,
        on_date=date(2026, 1, 1),
    ) == Decimal(95)
    other = Project.objects.create(owner=user, customer=customer, name="Other")
    assert resolve_rate(
        owner=user,
        customer=customer,
        project=other,
        on_date=date(2026, 1, 1),
    ) == Decimal(80)
