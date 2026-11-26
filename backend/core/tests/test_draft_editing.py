"""Editing a draft on the create page: loading it back and saving the page's state."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.models import Customer, HourlyRate, Invoice, TimeEntry
from core.services.contracts import generate_invoice


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def entries(user, customer, make_entry):
    HourlyRate.objects.create(
        owner=user, customer=customer, amount=Decimal(80), valid_from=date(2025, 1, 1)
    )
    return [
        make_entry(d=date(2026, 9, 1)),
        make_entry(d=date(2026, 9, 1), start="13:00", end="14:00"),
        make_entry(d=date(2026, 9, 2)),
    ]


def _ids(*entries):
    return [str(e.id) for e in entries]


TRAVEL = {"description": "Travel", "quantity": "1.00", "unit": "flat", "unit_price": "30.00"}


@pytest.fixture
def draft(client, customer, entries):
    """Grouped per day, the first day's text changed, plus an own line."""
    first_day, second_day = _ids(*entries[:2]), _ids(entries[2])
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {
            "customer_id": str(customer.id),
            "group_by": "day",
            "entry_lines": [
                {"entry_ids": first_day, "description": "Workshop"},
                {"entry_ids": second_day, "description": "02.09.2026"},
            ],
            "extra_lines": [TRAVEL],
        },
        format="json",
    )
    assert r.status_code == 201, r.json()
    return Invoice.objects.get(pk=r.json()["id"])


def _save(client, invoice, customer, **body):
    return client.put(
        f"/api/v1/invoices/{invoice.id}/draft/",
        {"customer_id": str(customer.id), **body},
        format="json",
    )


@pytest.mark.django_db
def test_draft_comes_back_as_the_page_holds_it(client, draft, entries):
    data = client.get(f"/api/v1/invoices/{draft.id}/draft/").json()
    assert data["group_by"] == "day"
    assert [e["id"] for e in data["entries"]] == _ids(*entries)
    # Only the text the user changed; the second day reads as generated.
    assert list(data["texts"].values()) == ["Workshop"]
    [key] = data["texts"]
    assert key.startswith("day:")
    assert data["own_lines"] == [TRAVEL]


@pytest.mark.django_db
def test_grouping_per_project_is_recognised(client, customer, entries):
    client.post(
        "/api/v1/invoices/consolidate/",
        {"customer_id": str(customer.id), "group_by": "project"},
        format="json",
    )
    invoice = Invoice.objects.get()
    data = client.get(f"/api/v1/invoices/{invoice.id}/draft/").json()
    assert data["group_by"] == "project"
    assert data["texts"] == {}


@pytest.mark.django_db
def test_saving_replaces_lines_and_frees_removed_entries(client, customer, draft, entries):
    number = draft.number
    r = _save(
        client,
        draft,
        customer,
        entry_lines=[{"entry_ids": _ids(*entries[:2]), "description": "Workshop, day 1"}],
        issue_date="2026-10-01",
        vat_rate="7",
        notes="Thanks!",
    )
    assert r.status_code == 200, r.json()
    draft.refresh_from_db()
    assert draft.number == number
    assert [i.description for i in draft.items.order_by("position")] == ["Workshop, day 1"]
    assert draft.subtotal == Decimal(240)
    assert draft.issue_date == date(2026, 10, 1)
    assert draft.vat_rate == Decimal(7)
    assert draft.notes == "Thanks!"
    removed = TimeEntry.objects.get(pk=entries[2].pk)
    assert removed.invoice is None
    assert removed.invoice_item is None


@pytest.mark.django_db
def test_saving_can_bill_entries_fetched_later(client, customer, draft, entries, make_entry):
    later = make_entry(d=date(2026, 9, 3))
    r = _save(
        client,
        draft,
        customer,
        entry_lines=[
            {"entry_ids": _ids(*entries), "description": "September"},
            {"entry_ids": _ids(later), "description": "03.09.2026"},
        ],
        extra_lines=[TRAVEL],
    )
    assert r.status_code == 200, r.json()
    assert TimeEntry.objects.filter(invoice=draft).count() == 4
    assert draft.items.count() == 3


@pytest.mark.django_db
def test_preview_of_a_draft_counts_its_entries_as_open(client, customer, draft, entries):
    body = {"customer_id": str(customer.id), "entry_ids": _ids(*entries), "group_by": "day"}
    r = client.post(f"/api/v1/invoices/{draft.id}/draft_preview/", body, format="json")
    assert r.json()["entry_count"] == 3
    r = client.post("/api/v1/invoices/consolidate_preview/", body, format="json")
    assert r.json()["entry_count"] == 0


@pytest.mark.django_db
def test_saving_needs_a_line(client, customer, draft):
    r = _save(client, draft, customer, entry_ids=[])
    assert r.status_code == 400
    assert draft.items.count() == 3


@pytest.mark.django_db
def test_only_drafts_of_the_same_customer_are_saved(client, user, customer, draft, entries):
    other = Customer.objects.create(owner=user, name="Beta AG")
    assert _save(client, draft, other, extra_lines=[TRAVEL]).status_code == 400

    Invoice.objects.filter(pk=draft.pk).update(status=Invoice.Status.ISSUED)
    assert _save(client, draft, customer, extra_lines=[TRAVEL]).status_code == 400
    assert TimeEntry.objects.filter(invoice=draft).count() == 3


@pytest.mark.django_db
def test_contract_entries_stay_with_their_invoice(client, customer, contract, make_entry):
    covered = make_entry(contract=contract, d=contract.current_period()[0])
    invoice = generate_invoice(contract)
    assert TimeEntry.objects.get(pk=covered.pk).invoice == invoice

    data = client.get(f"/api/v1/invoices/{invoice.id}/draft/").json()
    assert data["entries"] == []
    assert len(data["own_lines"]) == 1

    r = _save(client, invoice, customer, entry_ids=[], extra_lines=data["own_lines"])
    assert r.status_code == 200, r.json()
    assert TimeEntry.objects.get(pk=covered.pk).invoice == invoice


@pytest.mark.django_db
def test_saving_corrects_the_number_by_hand(client, customer, draft):
    assert _save(client, draft, customer, extra_lines=[TRAVEL], number="RE-7").status_code == 200
    draft.refresh_from_db()
    assert draft.number == "RE-7"

    Invoice.objects.create(
        owner=draft.owner, customer=customer, number="RE-8", issue_date=date(2026, 9, 1)
    )
    r = _save(client, draft, customer, extra_lines=[TRAVEL], number="RE-8")
    assert r.status_code == 400


@pytest.mark.django_db
def test_the_grouping_is_kept_where_lines_cannot_tell(client, customer, entries):
    # One entry per day: per entry and per day make the same lines, only the texts differ.
    one_per_day = _ids(entries[0], entries[2])
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {"customer_id": str(customer.id), "entry_ids": one_per_day, "group_by": "entry"},
        format="json",
    )
    invoice = Invoice.objects.get(pk=r.json()["id"])
    assert invoice.group_by == "entry"
    data = client.get(f"/api/v1/invoices/{invoice.id}/draft/").json()
    assert data["group_by"] == "entry"
    assert data["texts"] == {}

    # Saved again per day, the draft keeps that.
    r = _save(client, invoice, customer, entry_ids=one_per_day, group_by="day")
    invoice.refresh_from_db()
    assert invoice.group_by == "day"


@pytest.mark.django_db
def test_older_drafts_get_the_grouping_that_fits(client, draft):
    Invoice.objects.filter(pk=draft.pk).update(group_by="")
    data = client.get(f"/api/v1/invoices/{draft.id}/draft/").json()
    assert data["group_by"] == "day"
    assert list(data["texts"].values()) == ["Workshop"]


@pytest.mark.django_db
def test_invoices_without_entry_lines_have_no_grouping(client, customer, draft):
    _save(client, draft, customer, entry_ids=[], extra_lines=[TRAVEL], group_by="day")
    draft.refresh_from_db()
    assert draft.group_by == ""
