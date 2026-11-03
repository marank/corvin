from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from core.models import HourlyRate, Invoice
from core.services.consolidation import consolidate


@pytest.fixture
def rate(user, customer):
    return HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal("80"),
        valid_from=date(2025, 1, 1),
    )


@pytest.mark.django_db
def test_consolidate_group_by_entry(user, customer, project, rate, make_entry):
    make_entry(d=date(2026, 9, 1))  # 2h
    make_entry(d=date(2026, 9, 2))  # 2h
    inv = consolidate(owner=user, customer=customer, group_by="entry")
    assert inv.items.count() == 2
    assert inv.subtotal == Decimal("320")
    assert inv.status == Invoice.Status.DRAFT
    assert inv.number.startswith("RE-")


@pytest.mark.django_db
def test_consolidate_group_by_day(user, customer, project, rate, make_entry):
    make_entry(d=date(2026, 9, 1))
    make_entry(d=date(2026, 9, 1), start="13:00", end="14:00")  # +1h
    inv = consolidate(owner=user, customer=customer, group_by="day")
    assert inv.items.count() == 1
    assert inv.items.first().quantity == Decimal("3.00")


@pytest.mark.django_db
def test_double_invoicing_guard(user, customer, project, rate, make_entry):
    make_entry()
    consolidate(owner=user, customer=customer)
    with pytest.raises(ValidationError):
        consolidate(owner=user, customer=customer)


@pytest.mark.django_db
def test_rounding(user, customer, project, rate, make_entry):
    customer.rounding_increment_minutes = 30
    customer.save()
    make_entry(start="09:00", end="09:40")  # 40 min -> rounds to 60
    inv = consolidate(owner=user, customer=customer)
    assert inv.items.first().quantity == Decimal("1.00")
    assert inv.subtotal == Decimal("80")


@pytest.mark.django_db
def test_rate_change_over_boundary(user, customer, project, make_entry):
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal("80"),
        valid_from=date(2025, 1, 1),
    )
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal("85"),
        valid_from=date(2026, 1, 1),
    )
    make_entry(d=date(2025, 12, 31))  # 2h @ 80
    make_entry(d=date(2026, 1, 1))  # 2h @ 85
    inv = consolidate(owner=user, customer=customer, group_by="entry")
    totals = sorted(i.total for i in inv.items.all())
    assert totals == [Decimal("160"), Decimal("170")]


@pytest.mark.django_db
def test_entry_after_local_midnight_uses_local_date(user, customer, project, make_entry):
    # 00:30 in Berlin is still Dec 31 in UTC; rate and description must use Jan 1.
    HourlyRate.objects.create(
        owner=user, customer=customer, amount=Decimal("80"), valid_from=date(2025, 1, 1)
    )
    HourlyRate.objects.create(
        owner=user, customer=customer, amount=Decimal("85"), valid_from=date(2026, 1, 1)
    )
    make_entry(d=date(2026, 1, 1), start="00:30", end="01:30")
    inv = consolidate(owner=user, customer=customer, group_by="entry")
    item = inv.items.get()
    assert item.unit_price == Decimal("85")
    assert item.description.startswith("01.01.2026 — ")


@pytest.mark.django_db
def test_contract_entries_excluded(user, customer, project, contract, rate, make_entry):
    make_entry(contract=contract)  # covered — excluded
    make_entry(start="13:00", end="14:00")  # normal — invoiced
    inv = consolidate(owner=user, customer=customer)
    assert inv.items.count() == 1
    assert inv.items.first().quantity == Decimal("1.00")
