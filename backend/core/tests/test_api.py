from datetime import date, time

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import (
    CompanySettings,
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
    r = c.post("/api/v1/auth/login", {
        "username": "alice", "password": "testpass123"
    })
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
def test_timer_flow(client, project):
    r = client.post("/api/v1/time-entries/start_timer/", {
        "project": project.id, "description": "debugging"
    })
    assert r.status_code == 201
    entry_id = r.json()["id"]
    r2 = client.post(f"/api/v1/time-entries/{entry_id}/stop/")
    assert r2.status_code == 200
    assert r2.json()["is_running"] is False
    # second timer while stopped works
    r3 = client.post("/api/v1/time-entries/start_timer/",
                     {"project": project.id})
    assert r3.status_code == 201


@pytest.mark.django_db
def test_consolidate_endpoint(client, user, customer, project):
    HourlyRate.objects.create(
        owner=user, customer=customer, amount="80",
        valid_from=date(2025, 1, 1),
    )
    TimeEntry.objects.create(
        owner=user, project=project, date=date(2026, 9, 1),
        start_time=time(9), end_time=time(11),
    )
    r = client.post("/api/v1/invoices/consolidate/", {
        "customer_id": customer.id, "group_by": "project"
    })
    assert r.status_code == 201
    assert r.json()["subtotal"] == "160.00"


@pytest.mark.django_db
def test_password_change(client, user):
    r = client.post("/api/v1/auth/password/change", {
        "old_password": "testpass123", "new_password": "newpass1234"
    })
    assert r.status_code == 204
    user.refresh_from_db()
    assert user.check_password("newpass1234")


@pytest.mark.django_db
def test_settings_singleton(client):
    r = client.get("/api/v1/settings/")
    assert r.status_code == 200
    assert r.json()["company_name"] == "Alice Consulting"
    r2 = client.put("/api/v1/settings/", {"invoice_prefix": "INV"})
    assert r2.json()["invoice_prefix"] == "INV"
