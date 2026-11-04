from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import HourlyRate, Invoice, TimeEntry


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def rate(user, customer):
    return HourlyRate.objects.create(
        owner=user, customer=customer, amount=Decimal("80"), valid_from=date(2025, 1, 1)
    )


@pytest.fixture
def two_entries(make_entry, rate):
    return [make_entry(d=date(2026, 9, 1)), make_entry(d=date(2026, 9, 2))]  # 2h each


def _consolidate(client, customer, **extra):
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {"customer_id": str(customer.id), **extra},
        format="json",
    )
    assert r.status_code == 201, r.json()
    return Invoice.objects.get(pk=r.json()["id"])


@pytest.mark.django_db
def test_preview_matches_consolidate_and_writes_nothing(client, customer, two_entries):
    payload = {"customer_id": str(customer.id), "group_by": "entry"}
    r = client.post("/api/v1/invoices/consolidate_preview/", payload, format="json")
    assert r.status_code == 200
    data = r.json()
    assert data["entry_count"] == 2
    assert Decimal(data["subtotal"]) == Decimal("320")
    assert Decimal(data["total"]) == Decimal("380.80")
    assert [Decimal(line["total"]) for line in data["lines"]] == [Decimal("160")] * 2
    assert not Invoice.objects.exists()
    assert not TimeEntry.objects.filter(invoice__isnull=False).exists()


@pytest.mark.django_db
def test_preview_reports_missing_rate(client, customer, make_entry):
    make_entry()
    r = client.post(
        "/api/v1/invoices/consolidate_preview/",
        {"customer_id": str(customer.id)},
        format="json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_consolidate_bills_only_selected_entries(client, customer, two_entries):
    first, second = two_entries
    invoice = _consolidate(client, customer, entry_ids=[str(first.id)])
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.invoice == invoice
    assert first.invoice_item == invoice.items.get()
    assert second.invoice is None
    assert invoice.subtotal == Decimal("160")


@pytest.mark.django_db
def test_draft_header_update_recalculates_totals(client, customer, two_entries):
    invoice = _consolidate(client, customer)
    r = client.patch(
        f"/api/v1/invoices/{invoice.id}/",
        {"vat_rate": "7", "issue_date": "2026-10-01", "notes": "Danke"},
        format="json",
    )
    assert r.status_code == 200
    invoice.refresh_from_db()
    assert invoice.vat_amount == Decimal("22.40")
    assert invoice.total == Decimal("342.40")
    assert invoice.notes == "Danke"


@pytest.mark.django_db
def test_draft_customer_cannot_change(client, user, customer, two_entries):
    invoice = _consolidate(client, customer)
    other = customer.__class__.objects.create(owner=user, name="Other")
    r = client.patch(f"/api/v1/invoices/{invoice.id}/", {"customer": str(other.id)}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_line_items_add_edit_delete(client, customer, two_entries):
    invoice = _consolidate(client, customer)
    first_item = invoice.items.order_by("position").first()

    r = client.post(
        "/api/v1/invoice-items/",
        {
            "invoice": str(invoice.id),
            "description": "Anfahrt",
            "quantity": "1",
            "unit": "flat",
            "unit_price": "40",
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["position"] == 3
    invoice.refresh_from_db()
    assert invoice.subtotal == Decimal("360")

    r = client.patch(
        f"/api/v1/invoice-items/{first_item.id}/", {"unit_price": "100"}, format="json"
    )
    assert r.status_code == 200
    invoice.refresh_from_db()
    assert invoice.subtotal == Decimal("400")

    released = TimeEntry.objects.get(invoice_item=first_item)
    assert client.delete(f"/api/v1/invoice-items/{first_item.id}/").status_code == 204
    released.refresh_from_db()
    assert released.invoice is None and released.invoice_item is None
    invoice.refresh_from_db()
    assert invoice.subtotal == Decimal("200")
    assert list(invoice.items.values_list("position", flat=True)) == [1, 2]


@pytest.mark.django_db
def test_line_items_of_finalized_invoice_are_locked(client, customer, two_entries):
    invoice = _consolidate(client, customer)
    invoice.status = Invoice.Status.ISSUED
    invoice.save()
    item = invoice.items.first()
    assert (
        client.patch(
            f"/api/v1/invoice-items/{item.id}/", {"unit_price": "1"}, format="json"
        ).status_code
        == 400
    )
    assert client.delete(f"/api/v1/invoice-items/{item.id}/").status_code == 400
    assert (
        client.post(
            "/api/v1/invoice-items/",
            {"invoice": str(invoice.id), "description": "x", "unit_price": "1"},
            format="json",
        ).status_code
        == 400
    )


@pytest.mark.django_db
def test_line_items_are_owner_scoped(customer, two_entries, client):
    invoice = _consolidate(client, customer)
    bob = APIClient()
    bob.force_authenticate(User.objects.create_user("bob", password="pw123456"))
    item = invoice.items.first()
    assert bob.get(f"/api/v1/invoice-items/{item.id}/").status_code == 404
    r = bob.post(
        "/api/v1/invoice-items/",
        {"invoice": str(invoice.id), "description": "x", "unit_price": "1"},
        format="json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_lines_are_chronological_regardless_of_creation_order(client, customer, make_entry, rate):
    make_entry(d=date(2026, 9, 2))
    make_entry(d=date(2026, 9, 1))
    invoice = _consolidate(client, customer)
    descriptions = list(invoice.items.order_by("position").values_list("description", flat=True))
    assert descriptions[0].startswith("01.09.2026")
    assert descriptions[1].startswith("02.09.2026")


@pytest.mark.django_db
def test_invoiced_time_entry_cannot_be_deleted(client, customer, two_entries):
    first, second = two_entries
    _consolidate(client, customer, entry_ids=[str(first.id)])
    assert client.delete(f"/api/v1/time-tracking/{first.id}/").status_code == 400
    assert TimeEntry.objects.filter(id=first.id).exists()
    assert client.delete(f"/api/v1/time-tracking/{second.id}/").status_code == 204


@pytest.mark.django_db
def test_line_texts_skip_repeated_project_and_use_language_code(client, customer, make_entry, rate):
    make_entry(description="Migration der Datenbank")
    make_entry(d=date(2026, 9, 2), description="Review")
    make_entry(d=date(2026, 9, 3))
    client.credentials(HTTP_ACCEPT_LANGUAGE="en")
    invoice = _consolidate(client, customer)
    assert [item.description for item in invoice.items.order_by("position")] == [
        "01.09.2026 — Migration der Datenbank",
        "02.09.2026 — Migration: Review",
        "03.09.2026 — Migration: Leistungen",
    ]


@pytest.mark.django_db
def test_email_draft_falls_back_to_default_in_language_code(client, customer, two_entries):
    invoice = _consolidate(client, customer)
    r = client.get(f"/api/v1/invoices/{invoice.id}/email_draft/", HTTP_ACCEPT_LANGUAGE="en")
    assert r.status_code == 200
    assert r.json()["subject"] == f"Rechnung {invoice.number}"
    assert r.json()["body"].startswith("Sehr geehrte")


@pytest.mark.django_db
def test_timer_messages_follow_accept_language(client):
    assert client.post("/api/v1/time-tracking/stop/", HTTP_ACCEPT_LANGUAGE="de").json() == {
        "detail": "Es läuft kein Timer."
    }


@pytest.mark.django_db
def test_receivable_filter_matches_dashboard(client, customer, user):
    today = date.today()
    common = {"owner": user, "customer": customer, "issue_date": today, "total": Decimal("10")}
    Invoice.objects.create(number="R1", status=Invoice.Status.ISSUED, due_date=today, **common)
    Invoice.objects.create(
        number="R2", status=Invoice.Status.SENT, due_date=date(2020, 1, 1), **common
    )
    Invoice.objects.create(number="R3", status=Invoice.Status.PAID, due_date=today, **common)
    Invoice.objects.create(number="R4", status=Invoice.Status.DRAFT, due_date=today, **common)

    def numbers(value):
        r = client.get(f"/api/v1/invoices/?receivable={value}&ordering=number")
        return [row["number"] for row in r.json()["results"]]

    assert numbers("open") == ["R1", "R2"]
    assert numbers("overdue") == ["R2"]
