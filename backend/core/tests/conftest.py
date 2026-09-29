from datetime import date, time
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from core.models import (
    Address,
    CompanySettings,
    Customer,
    InvoiceTemplate,
    Project,
    SupportContract,
    TimeEntry,
)


@pytest.fixture
def user(db):
    u = User.objects.create_user("alice", password="testpass123")
    CompanySettings.objects.create(
        user=u,
        company_name="Alice Consulting",
        street="Hauptstr. 1",
        postal_code="10115",
        city="Berlin",
        vat_id="DE123456789",
        iban="DE89370400440532013000",
    )
    return u


@pytest.fixture
def customer(user):
    c = Customer.objects.create(
        owner=user,
        name="Acme GmbH",
        buyer_reference="04011000-12345",
    )
    Address.objects.create(
        owner=user,
        customer=c,
        label="HQ",
        street="Industrieweg 5",
        postal_code="20095",
        city="Hamburg",
        is_primary=True,
    )
    return c


@pytest.fixture
def project(user, customer):
    return Project.objects.create(
        owner=user, customer=customer, name="Migration"
    )


@pytest.fixture
def make_entry(user, project):
    def _make(d=date(2026, 9, 1), start="09:00", end="11:00", **kw):
        h1, m1 = map(int, start.split(":"))
        h2, m2 = map(int, end.split(":"))
        return TimeEntry.objects.create(
            owner=user,
            customer=kw.pop("customer", project.customer),
            project=project,
            date=d,
            start_time=time(h1, m1),
            end_time=time(h2, m2),
            **kw,
        )

    return _make


@pytest.fixture
def invoice_template(user):
    return InvoiceTemplate.objects.create(
        owner=user,
        name="Default",
        body_html=(
            "<h1>Rechnung {{ invoice.number }}</h1>"
            "<p>{{ customer.name }}</p>"
            "{% for i in items %}<p>{{ i.description }} "
            "{{ i.quantity }} x {{ i.unit_price }}</p>{% endfor %}"
            "<p>Total: {{ invoice.total }} {{ invoice.currency }}</p>"
        ),
        css="body{font-family:sans-serif}",
    )


@pytest.fixture
def contract(user, customer, project):
    return SupportContract.objects.create(
        owner=user,
        customer=customer,
        name="Gold Support",
        included_hours=Decimal("10"),
        period="monthly",
        fixed_price=Decimal("750"),
        bill_overage=True,
        start_date=date(2026, 9, 1),
        next_billing_date=date(2026, 10, 1),
    )
