from datetime import date
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Customer, NumberSequence
from core.services.numbering import next_number, render_number


@pytest.fixture
def client(user):
    value = APIClient()
    value.force_authenticate(user)
    return value


def test_render_number_resolvers_and_model_fields():
    customer = SimpleNamespace(
        number="1001", vat_id="DE123", name="Acme"
    )
    project = SimpleNamespace(customer=customer, number="P-1")
    result = render_number(
        "{year:4}/{year:2}/{month:2}/{customer.number}-"
        "{customer.vat_id}-{project.customer.name}-{counter:3}",
        1,
        {"customer": customer, "project": project},
        date(2026, 9, 25),
    )
    assert result == "2026/26/09/1001-DE123-Acme-001"


@pytest.mark.django_db
def test_start_and_customer_counter_scope(user, customer):
    settings = user.company_settings
    settings.numbering_schemes["project"] = {
        "format": "{customer.number}-{counter:3}",
        "scope": "customer",
        "start": 10,
    }
    settings.save(update_fields=["numbering_schemes"])
    customer.number = "1001"
    customer.save(update_fields=["number"])

    first = next_number(user, "project", {"customer": customer})
    second = next_number(user, "project", {"customer": customer})
    assert first == "1001-010"
    assert second == "1001-011"

    settings.numbering_schemes["project"]["start"] = 50
    settings.save(update_fields=["numbering_schemes"])
    assert next_number(user, "project", {"customer": customer}) == "1001-012"


@pytest.mark.django_db
def test_customer_year_scope_has_independent_annual_customer_counters(
    user, customer
):
    other = Customer.objects.create(owner=user, name="Other")
    settings = user.company_settings
    settings.numbering_schemes["project"] = {
        "format": "{year:4}/{counter:3}",
        "scope": ["customer", "year"],
        "start": 1,
    }
    settings.save(update_fields=["numbering_schemes"])

    assert next_number(user, "project", {"customer": customer}).endswith("/001")
    assert next_number(user, "project", {"customer": customer}).endswith("/002")
    assert next_number(user, "project", {"customer": other}).endswith("/001")
    year = timezone.localdate().year
    assert NumberSequence.objects.filter(
        owner=user, entity="project",
        scope_key=f"customer:{customer.id}:year:{year}",
    ).exists()


@pytest.mark.django_db
def test_api_assigns_numbers_to_all_configured_entities(client, customer, project):
    assert client.post("/api/v1/customers/", {"name": "Second"}).json()["number"]
    assert client.post("/api/v1/projects/", {
        "customer": str(customer.id), "name": "New Project",
    }).json()["number"]
    assert client.post("/api/v1/visits/", {
        "customer": str(customer.id), "date": "2026-09-25",
    }).json()["number"]
    assert client.post("/api/v1/tasks/", {
        "customer": str(customer.id), "title": "New Task",
    }).json()["number"]
    assert client.post("/api/v1/support-contracts/", {
        "customer": str(customer.id),
        "project": str(project.id),
        "name": "Silver",
        "included_hours": "2.00",
        "period": "monthly",
        "fixed_price": "200.00",
        "start_date": "2026-09-01",
        "next_billing_date": "2026-10-01",
    }).json()["number"]


@pytest.mark.django_db
def test_preview_does_not_increment_sequence(client, user):
    before = NumberSequence.objects.filter(owner=user).count()
    response = client.post("/api/v1/settings/preview-number/", {
        "entity": "invoice",
        "format": "{year:2}-{counter:3}",
        "scope": ["year"],
        "start": 42,
    }, format="json")
    assert response.status_code == 200
    assert response.json()["preview"] == f"{str(timezone.localdate().year)[-2:]}-042"
    assert NumberSequence.objects.filter(owner=user).count() == before


@pytest.mark.django_db
def test_invalid_numbering_scheme_is_rejected(client, user):
    schemes = user.company_settings.numbering_schemes
    schemes["invoice"]["scope"] = "invalid"
    response = client.put(
        "/api/v1/settings/", {"numbering_schemes": schemes}, format="json"
    )
    assert response.status_code == 400
