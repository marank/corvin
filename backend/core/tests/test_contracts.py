from datetime import date, datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.services.contracts import contract_usage, process_due


@pytest.mark.django_db
def test_usage_counts_only_contract_entries(user, contract, make_entry):
    make_entry(d=date(2026, 9, 5), contract=contract)       # 2h covered
    make_entry(d=date(2026, 9, 6))                          # 2h not covered
    usage = contract_usage(contract)
    assert usage["used_hours"] == Decimal("2.00")
    assert usage["included_hours"] == Decimal("10")
    assert usage["overage_hours"] == Decimal("0")


@pytest.mark.django_db
def test_overage(user, contract, make_entry):
    for day in range(1, 7):  # 6 × 2h = 12h covered, 10 included → 2 over
        make_entry(d=date(2026, 9, day), contract=contract)
    usage = contract_usage(contract)
    assert usage["overage_hours"] == Decimal("2.00")


@pytest.mark.django_db
def test_process_due_generates_and_advances(user, contract, make_entry):
    for day in range(1, 7):
        make_entry(d=date(2026, 9, day), contract=contract)
    invoices = process_due(today=date(2026, 10, 2))
    assert len(invoices) == 1
    inv = invoices[0]
    contract.refresh_from_db()
    assert contract.next_billing_date == date(2026, 11, 1)
    # fixed line + overage line (overage_rate unset → resolved rate None → 0)
    assert inv.items.count() == 2
    assert inv.items.first().unit_price == Decimal("750")


@pytest.mark.django_db
def test_flat_contract_no_hours(user, customer, contract):
    contract.included_hours = 0
    contract.bill_overage = False
    contract.save()
    invoices = process_due(today=date(2026, 10, 2))
    assert invoices[0].items.count() == 1
    assert invoices[0].items.first().total == Decimal("750")


@pytest.mark.django_db
def test_wrong_customer_contract_rejected(user, customer, contract):

    from core.models import Customer, Project, TimeEntry

    other = Customer.objects.create(owner=user, name="Other GmbH")
    other_project = Project.objects.create(
        owner=user, customer=other, name="Other"
    )
    with pytest.raises(ValidationError):
        tz = timezone.get_current_timezone()
        TimeEntry.objects.create(
            owner=user, customer=customer, project=other_project,
            contract=contract,
            start_datetime=timezone.make_aware(datetime(2026, 9, 1, 9, 0), tz),
            end_datetime=timezone.make_aware(datetime(2026, 9, 1, 10, 0), tz),
        )
