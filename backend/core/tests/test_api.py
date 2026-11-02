from datetime import date, datetime, timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    CompanySettings,
    Contact,
    Customer,
    HourlyRate,
    TimeEntry,
)


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.mark.django_db
def test_me_requires_auth():
    c = APIClient()
    assert c.get("/api/v1/auth/me").status_code == 401


@pytest.mark.django_db
def test_register_and_login(user):
    c = APIClient()
    r = c.post("/api/v1/auth/login", {"username": "alice", "password": "testpass123"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


@pytest.mark.django_db
def test_owner_isolation(user, customer):
    other = User.objects.create_user("bob", password="pw123456")
    CompanySettings.objects.create(user=other, company_name="Bob")
    c = APIClient()
    c.force_authenticate(other)
    r = c.get("/api/v1/customers/")
    assert r.json()["results"] == []


@pytest.mark.django_db
def test_customer_pagination_and_ordering(client, user):
    Customer.objects.bulk_create(
        [
            Customer(owner=user, number=f"K-{index:03d}", name=f"Customer {index:03d}")
            for index in range(55)
        ]
    )

    first_page = client.get("/api/v1/customers/?ordering=number")
    assert first_page.status_code == 200
    assert first_page.json()["count"] == 55
    assert len(first_page.json()["results"]) == 50
    assert first_page.json()["results"][0]["number"] == "K-000"

    second_page = client.get("/api/v1/customers/?page=2&page_size=10&ordering=-number")
    assert second_page.status_code == 200
    assert len(second_page.json()["results"]) == 10
    assert second_page.json()["results"][0]["number"] == "K-044"

    capped = client.get("/api/v1/customers/?page_size=10000")
    assert len(capped.json()["results"]) == 55

    assert client.get("/api/v1/customers/?page=99").status_code == 404


@pytest.mark.django_db
def test_customer_ordering_by_annotations(client, user, customer, project):
    other = Customer.objects.create(owner=user, number="K-999", name="Zeta")
    tz = timezone.get_current_timezone()
    TimeEntry.objects.create(
        owner=user,
        customer=other,
        start_datetime=timezone.make_aware(datetime(2026, 9, 1, 9, 0), tz),
        end_datetime=timezone.make_aware(datetime(2026, 9, 1, 12, 0), tz),
    )

    by_projects = client.get("/api/v1/customers/?ordering=-project_count").json()
    assert by_projects["results"][0]["id"] == str(customer.id)
    assert by_projects["count"] == 2

    by_hours = client.get("/api/v1/customers/?ordering=-uninvoiced_hours").json()
    assert by_hours["results"][0]["id"] == str(other.id)
    assert by_hours["count"] == 2

    ignored = client.get("/api/v1/customers/?ordering=is_active")
    assert ignored.status_code == 200


@pytest.mark.django_db
def test_time_entry_date_range_filter(client, user, customer):
    tz = timezone.get_current_timezone()
    for day in (1, 15, 30):
        TimeEntry.objects.create(
            owner=user,
            customer=customer,
            start_datetime=timezone.make_aware(datetime(2026, 9, day, 9, 0), tz),
            end_datetime=timezone.make_aware(datetime(2026, 9, day, 10, 0), tz),
        )
    r = client.get(
        "/api/v1/time-tracking/?start_datetime__date__gte=2026-09-15"
        "&start_datetime__date__lte=2026-09-30"
    )
    assert r.status_code == 200
    assert r.json()["count"] == 2


@pytest.mark.django_db
def test_time_entry_summary(client, user, customer):
    tz = timezone.get_current_timezone()
    for day in range(1, 4):
        TimeEntry.objects.create(
            owner=user,
            customer=customer,
            start_datetime=timezone.make_aware(datetime(2026, 9, day, 9, 0), tz),
            end_datetime=timezone.make_aware(datetime(2026, 9, day, 11, 0), tz),
        )
    TimeEntry.objects.create(
        owner=user,
        customer=customer,
        start_datetime=timezone.make_aware(datetime(2026, 9, 4, 9, 0), tz),
    )
    r = client.get(
        f"/api/v1/time-tracking/summary/?customer={customer.id}"
        "&end_datetime__isnull=false&start_datetime__date__gte=2026-09-02"
    )
    assert r.status_code == 200
    assert r.json() == {"count": 2, "total_minutes": 240}


@pytest.mark.django_db
def test_timer_flow(client, customer, project):
    r = client.post(
        "/api/v1/time-tracking/start/",
        {
            "customer": str(customer.id),
            "project": str(project.id),
            "description": "debugging",
        },
    )
    assert r.status_code == 201
    r2 = client.post("/api/v1/time-tracking/stop/")
    assert r2.status_code == 200
    assert r2.json()["is_running"] is False
    # customer-only timer (no project) works too
    r3 = client.post("/api/v1/time-tracking/start/", {"customer": str(customer.id)})
    assert r3.status_code == 201


@pytest.mark.django_db
def test_consolidate_endpoint(client, user, customer, project):
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount="80",
        valid_from=date(2025, 1, 1),
    )
    tz = timezone.get_current_timezone()
    TimeEntry.objects.create(
        owner=user,
        customer=customer,
        project=project,
        start_datetime=timezone.make_aware(datetime(2026, 9, 1, 9, 0), tz),
        end_datetime=timezone.make_aware(datetime(2026, 9, 1, 11, 0), tz),
    )
    r = client.post(
        "/api/v1/invoices/consolidate/", {"customer_id": customer.id, "group_by": "project"}
    )
    assert r.status_code == 201
    assert r.json()["subtotal"] == "160.00"


@pytest.mark.django_db
def test_consolidate_validation_error_returns_400(client, customer):
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {
            "customer_id": str(customer.id),
            "group_by": "entry",
        },
    )
    assert r.status_code == 400
    assert "No billable" in r.json()["detail"][0]


@pytest.mark.django_db
def test_manual_only_invoice(client, customer):
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {
            "customer_id": str(customer.id),
            "group_by": "entry",
            "extra_lines": [
                {
                    "description": "Hardware",
                    "quantity": "2.00",
                    "unit": "piece",
                    "unit_price": "25.00",
                }
            ],
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["subtotal"] == "50.00"
    assert r.json()["items"][0]["description"] == "Hardware"


@pytest.mark.django_db
def test_invoice_contacts_default_and_override(client, user, customer):
    default = Contact.objects.create(
        owner=user,
        customer=customer,
        first_name="Default",
        is_invoice_contact=True,
    )
    Contact.objects.create(
        owner=user,
        customer=customer,
        first_name="Optional",
    )
    payload = {
        "customer_id": str(customer.id),
        "group_by": "entry",
        "extra_lines": [
            {
                "description": "Service",
                "quantity": "1.00",
                "unit": "flat",
                "unit_price": "100.00",
            }
        ],
    }
    response = client.post("/api/v1/invoices/consolidate/", payload, format="json")
    assert response.status_code == 201
    assert [contact["id"] for contact in response.json()["contacts"]] == [str(default.id)]

    payload["contact_ids"] = []
    response = client.post("/api/v1/invoices/consolidate/", payload, format="json")
    assert response.status_code == 201
    assert response.json()["contacts"] == []


@pytest.mark.django_db
def test_invoice_uses_vat_setting_and_customer_payment_terms(client, user, customer):
    settings = user.company_settings
    settings.vat_enabled = False
    settings.payment_terms_days = 30
    settings.currency = "USD"
    settings.save(update_fields=["vat_enabled", "payment_terms_days", "currency"])
    customer.payment_terms_days = 7
    customer.save(update_fields=["payment_terms_days"])

    r = client.post(
        "/api/v1/invoices/consolidate/",
        {
            "customer_id": str(customer.id),
            "group_by": "entry",
            "extra_lines": [
                {
                    "description": "Service",
                    "quantity": "1.00",
                    "unit": "flat",
                    "unit_price": "100.00",
                }
            ],
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["vat_rate"] == "0.00"
    assert r.json()["vat_amount"] == "0.00"
    assert r.json()["total"] == "100.00"
    assert r.json()["currency"] == "USD"
    assert r.json()["due_date"] == str(date.today() + timedelta(days=7))


@pytest.mark.django_db
def test_invoice_uses_default_payment_terms(client, user, customer):
    settings = user.company_settings
    settings.payment_terms_days = 30
    settings.save(update_fields=["payment_terms_days"])

    r = client.post(
        "/api/v1/invoices/consolidate/",
        {
            "customer_id": str(customer.id),
            "group_by": "entry",
            "extra_lines": [
                {
                    "description": "Service",
                    "quantity": "1.00",
                    "unit": "flat",
                    "unit_price": "100.00",
                }
            ],
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["due_date"] == str(date.today() + timedelta(days=30))


@pytest.mark.django_db
def test_password_change(client, user):
    r = client.post(
        "/api/v1/auth/password/change",
        {"old_password": "testpass123", "new_password": "newpass1234"},
    )
    assert r.status_code == 204
    user.refresh_from_db()
    assert user.check_password("newpass1234")


@pytest.mark.django_db
def test_customer_address_crud(client, customer):
    r = client.post(
        "/api/v1/addresses/",
        {
            "customer": str(customer.id),
            "label": "Office",
            "street": "Nebenstr. 2",
            "postal_code": "80331",
            "city": "München",
            "is_primary": True,
        },
    )
    assert r.status_code == 201
    addr_id = r.json()["id"]

    # multiple addresses allowed
    r = client.post(
        "/api/v1/addresses/",
        {
            "customer": str(customer.id),
            "street": "Weg 3",
            "postal_code": "10115",
            "city": "Berlin",
        },
    )
    assert r.status_code == 201

    r = client.get(f"/api/v1/addresses/?customer={customer.id}")
    assert len(r.json()["results"]) == 3  # fixture HQ + 2 new

    # setting a new primary clears the old one
    customer.refresh_from_db()
    assert str(customer.primary_address.id) == addr_id

    r = client.delete(f"/api/v1/addresses/{addr_id}/")
    assert r.status_code == 204


@pytest.mark.django_db
def test_contact_first_last_name(client, customer):
    r = client.post(
        "/api/v1/contacts/",
        {
            "customer": str(customer.id),
            "first_name": "Max",
            "last_name": "Mustermann",
            "role": "CTO",
            "email": "max@acme.test",
        },
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Max Mustermann"


@pytest.mark.django_db
def test_customer_website_vat_id(client, customer):
    r = client.patch(
        f"/api/v1/customers/{customer.id}/",
        {
            "website": "https://acme.example",
            "vat_id": "DE987654321",
        },
    )
    assert r.status_code == 200
    assert r.json()["website"] == "https://acme.example"
    assert r.json()["vat_id"] == "DE987654321"
    assert r.json()["primary_address"]["city"] == "Hamburg"


@pytest.mark.django_db
def test_address_owner_isolation(user, customer):
    other = User.objects.create_user("bob", password="pw123456")
    CompanySettings.objects.create(user=other, company_name="Bob")
    c = APIClient()
    c.force_authenticate(other)
    r = c.get(f"/api/v1/addresses/?customer={customer.id}")
    assert r.json()["results"] == []
    # bob cannot attach an address to alice's customer
    r = c.post(
        "/api/v1/addresses/",
        {
            "customer": str(customer.id),
            "street": "X",
            "postal_code": "1",
            "city": "Y",
        },
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_company_contact_crud(client):
    response = client.post(
        "/api/v1/company-contacts/",
        {
            "first_name": "Alice",
            "last_name": "Admin",
            "role": "Management",
            "email": "alice@example.com",
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Alice Admin"
    contact_id = response.json()["id"]

    response = client.put(
        f"/api/v1/company-contacts/{contact_id}/",
        {
            "first_name": "Alice",
            "last_name": "Admin",
            "role": "Director",
            "email": "alice@example.com",
        },
    )
    assert response.status_code == 200
    assert response.json()["role"] == "Director"

    response = client.delete(f"/api/v1/company-contacts/{contact_id}/")
    assert response.status_code == 204


@pytest.mark.django_db
def test_settings_singleton(client):
    r = client.get("/api/v1/settings/")
    assert r.status_code == 200
    assert r.json()["company_name"] == "Alice Consulting"
    assert r.json()["date_format"] == "DD.MM.YYYY"
    assert r.json()["time_format"] == "HH:mm"
    assert r.json()["decimal_separator"] == ","
    assert r.json()["thousands_separator"] == "."
    assert r.json()["currency"] == "EUR"
    assert r.json()["currency_display"] == "symbol"
    assert r.json()["currency_position"] == "after"
    assert r.json()["currency_space"] is True
    schemes = r.json()["numbering_schemes"]
    schemes["invoice"]["format"] = "INV-{counter:4}"
    r2 = client.put("/api/v1/settings/", {"numbering_schemes": schemes}, format="json")
    assert r2.json()["numbering_schemes"]["invoice"]["format"] == "INV-{counter:4}"
