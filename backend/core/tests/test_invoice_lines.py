"""Creating an invoice from picked entries: the lines as the user worded them, the general
fields of the create page, the customer's e-invoice default and the time report."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import DocumentTemplate, HourlyRate, Invoice, Project, TimeEntry
from core.services.contracts import generate_invoice


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def rate(user, customer):
    return HourlyRate.objects.create(
        owner=user, customer=customer, amount=Decimal(80), valid_from=date(2025, 1, 1)
    )


@pytest.fixture
def entries(make_entry, rate):
    return [make_entry(d=date(2026, 9, 1)), make_entry(d=date(2026, 9, 2))]  # 2h each


def _post(client, action, customer, **extra):
    return client.post(
        f"/api/v1/invoices/{action}/",
        {"customer_id": str(customer.id), **extra},
        format="json",
    )


def _consolidate(client, customer, **extra):
    r = _post(client, "consolidate", customer, **extra)
    assert r.status_code == 201, r.json()
    return Invoice.objects.get(pk=r.json()["id"])


def _ids(*entries):
    return [str(e.id) for e in entries]


@pytest.mark.django_db
def test_preview_lines_carry_their_entries_and_context(client, customer, entries):
    r = _post(client, "consolidate_preview", customer, entry_ids=_ids(*entries), group_by="day")
    assert r.status_code == 200
    lines = r.json()["lines"]
    assert [line["entry_ids"] for line in lines] == [_ids(entries[0]), _ids(entries[1])]
    first = lines[0]
    # Per day: the date alone; the details go to the time report.
    assert first["description"] == first["default_description"] == "01.09.2026"
    assert first["key"].startswith("day:")
    assert first["project_name"] == "Migration"
    assert first["date_from"] == first["date_to"] == "2026-09-01"


@pytest.mark.django_db
def test_per_project_lines_read_the_project_name(client, customer, entries):
    r = _post(client, "consolidate_preview", customer, group_by="project")
    [line] = r.json()["lines"]
    assert line["description"] == "Migration"
    assert line["date_from"] == "2026-09-01"
    assert line["date_to"] == "2026-09-02"


@pytest.mark.django_db
def test_lines_bill_the_entries_under_the_users_text(client, customer, entries):
    invoice = _consolidate(
        client,
        customer,
        entry_ids=_ids(*entries),
        entry_lines=[{"entry_ids": _ids(*entries), "description": "Migration, phase 1"}],
        extra_lines=[{"description": "Travel", "quantity": 1, "unit": "flat", "unit_price": 30}],
    )
    entry_line, travel = invoice.items.order_by("position")
    assert entry_line.description == "Migration, phase 1"
    assert entry_line.quantity == Decimal(4)
    assert set(entry_line.time_entries.all()) == set(entries)
    assert travel.description == "Travel"
    assert invoice.subtotal == Decimal(350)


@pytest.mark.django_db
@pytest.mark.parametrize("twice", [True, False])
def test_lines_refuse_entries_twice_or_not_open(client, customer, entries, twice):
    first, second = entries
    if not twice:
        _consolidate(client, customer, entry_ids=_ids(second))
    lines = [{"entry_ids": _ids(first), "description": "a"}]
    lines.append({"entry_ids": _ids(first if twice else second), "description": "b"})
    r = _post(client, "consolidate", customer, entry_lines=lines)
    assert r.status_code == 400
    assert Invoice.objects.count() == (0 if twice else 1)


@pytest.mark.django_db
def test_invoice_takes_the_project_all_lines_share(client, user, customer, entries, make_entry):
    assert _consolidate(client, customer, entry_ids=_ids(*entries)).project == entries[0].project

    other = Project.objects.create(owner=user, customer=customer, name="Hosting")
    mixed = [make_entry(d=date(2026, 9, 3)), make_entry(d=date(2026, 9, 4), project=other)]
    assert _consolidate(client, customer, entry_ids=_ids(*mixed)).project is None


@pytest.mark.django_db
def test_general_fields_are_taken_over(client, user, customer, entries):
    template = DocumentTemplate.objects.create(owner=user, name="Plain")
    invoice = _consolidate(
        client,
        customer,
        issue_date="2026-10-01",
        due_date="2026-10-31",
        vat_rate="7",
        template_id=str(template.id),
        notes="Thanks!",
    )
    assert invoice.issue_date == date(2026, 10, 1)
    assert invoice.due_date == date(2026, 10, 31)
    assert invoice.vat_rate == Decimal(7)
    assert invoice.template == template
    assert invoice.notes == "Thanks!"


@pytest.mark.django_db
def test_due_date_follows_issue_date_and_customer_terms(client, customer, entries):
    customer.payment_terms_days = 30
    customer.save()
    invoice = _consolidate(client, customer, issue_date="2026-10-01")
    assert invoice.due_date == date(2026, 10, 31)


@pytest.mark.django_db
def test_preview_uses_the_vat_rate_given(client, customer, entries):
    r = _post(client, "consolidate_preview", customer, vat_rate="7")
    assert Decimal(r.json()["vat_amount"]) == Decimal("22.40")


@pytest.mark.django_db
def test_foreign_template_is_refused(client, customer, entries):
    stranger = User.objects.create_user("mallory", password="testpass123")
    template = DocumentTemplate.objects.create(owner=stranger, name="Theirs")
    r = _post(client, "consolidate", customer, template_id=str(template.id))
    assert r.status_code == 400
    assert "template_id" in r.json()


@pytest.mark.django_db
def test_e_invoice_format_defaults_to_the_customers(client, customer, entries, contract):
    customer.e_invoice_format = "xrechnung"
    customer.save()
    assert _consolidate(client, customer, entry_ids=_ids(entries[0])).e_invoice_format == (
        "xrechnung"
    )
    chosen = _consolidate(client, customer, entry_ids=_ids(entries[1]), e_invoice_format="none")
    assert chosen.e_invoice_format == "none"

    r = client.post(
        "/api/v1/invoices/",
        {"customer": str(customer.id), "issue_date": "2026-10-01", "due_date": "2026-10-15"},
        format="json",
    )
    assert r.status_code == 201, r.json()
    assert r.json()["e_invoice_format"] == "xrechnung"

    contract.refresh_from_db()
    assert generate_invoice(contract).e_invoice_format == "xrechnung"


@pytest.mark.django_db
def test_time_report_lists_the_billed_entries(client, customer, entries):
    invoice = _consolidate(client, customer, entry_ids=_ids(*entries))
    data = client.get(f"/api/v1/invoices/{invoice.id}/").json()
    assert data["has_time_entries"] is True

    r = client.get(f"/api/v1/invoices/{invoice.id}/time-report/")
    assert r.status_code == 200
    assert r["Content-Type"] == "application/pdf"
    assert "attachment" in r["Content-Disposition"]
    assert b"".join(r.streaming_content if r.streaming else [r.content]).startswith(b"%PDF")


@pytest.mark.django_db
def test_time_report_context_sums_per_line(user, customer, entries):
    from core.services.consolidation import consolidate
    from core.services.time_report import time_report_context

    invoice = consolidate(owner=user, customer=customer, group_by="project")
    context = time_report_context(invoice)
    [line] = context["lines"]
    assert line["duration"] == "4:00 h"
    assert [e["description"] for e in line["entries"]] == ["", ""]
    assert context["total"] == "4:00 h"
    assert TimeEntry.objects.filter(invoice=invoice).count() == 2


@pytest.mark.django_db
def test_invoices_without_entries_have_no_time_report(client, customer):
    r = client.post(
        "/api/v1/invoices/",
        {"customer": str(customer.id), "issue_date": "2026-10-01", "due_date": "2026-10-15"},
        format="json",
    )
    assert r.json()["has_time_entries"] is False
    listed = client.get("/api/v1/invoices/").json()["results"]
    assert listed[0]["has_time_entries"] is False


@pytest.mark.django_db
def test_lines_say_which_entries_they_bill(client, customer, entries):
    invoice = _consolidate(client, customer, entry_ids=_ids(*entries), group_by="entry")
    data = client.get(f"/api/v1/invoices/{invoice.id}/").json()
    assert [item["time_entry_ids"] for item in data["items"]] == [[i] for i in _ids(*entries)]

    listed = client.get(f"/api/v1/invoices/{invoice.id}/time-entries/").json()
    assert [e["id"] for e in listed] == _ids(*entries)
    assert all(e["invoice"] == str(invoice.id) for e in listed)


@pytest.mark.django_db
def test_entries_are_not_linked_through_the_time_api(client, customer, entries):
    invoice = _consolidate(client, customer, entry_ids=_ids(entries[0]))
    open_entry = entries[1]
    r = client.patch(
        f"/api/v1/time-tracking/{open_entry.id}/", {"invoice": str(invoice.id)}, format="json"
    )
    assert r.status_code == 200
    open_entry.refresh_from_db()
    assert open_entry.invoice is None


@pytest.mark.django_db
def test_time_list_names_the_invoice_an_entry_is_billed_on(client, customer, entries):
    invoice = _consolidate(client, customer, entry_ids=_ids(entries[0]))
    Invoice.objects.filter(pk=invoice.pk).update(number="RE-2026-0042")
    rows = {e["id"]: e for e in client.get("/api/v1/time-tracking/").json()["results"]}
    assert rows[str(entries[0].id)]["invoice_number"] == "RE-2026-0042"
    assert rows[str(entries[1].id)]["invoice_number"] is None
