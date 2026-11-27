"""Trips to on-site visits on invoices: flat or per km, offered while open, linked once billed."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.models import Invoice, OnSiteVisit, TravelRate


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def visit(user, customer, project):
    return OnSiteVisit.objects.create(
        owner=user, number="V-0001", customer=customer, project=project, date=date(2026, 9, 1)
    )


def _rate(user, kind="flat", amount="45", **kw):
    return TravelRate.objects.create(
        owner=user, kind=kind, amount=Decimal(amount), valid_from=date(2026, 1, 1), **kw
    )


def _preview(client, customer, *trips):
    return client.post(
        "/api/v1/invoices/consolidate_preview/",
        {"customer_id": str(customer.id), "entry_ids": [], "travel": list(trips)},
        format="json",
    )


def _billable(client, customer, **params):
    query = "&".join(f"{k}={v}" for k, v in {"customer": customer.id, **params}.items())
    return [v["id"] for v in client.get(f"/api/v1/visits/billable-travel/?{query}").json()]


@pytest.mark.django_db
def test_flat_rate_bills_one_trip(client, user, customer, visit):
    _rate(user)
    r = _preview(client, customer, {"visit_id": str(visit.id)})
    assert r.status_code == 200, r.json()
    [line] = r.json()["lines"]
    assert line["description"] == "Anfahrt 01.09.2026 (V-0001)"
    assert (line["quantity"], line["unit"], line["unit_price"]) == ("1.00", "flat", "45.00")
    assert line["key"] == f"travel:{visit.id}"
    assert line["visit_id"] == str(visit.id)


@pytest.mark.django_db
def test_per_km_counts_the_distance_there_and_back(client, user, customer, visit):
    _rate(user, kind="km", amount="0.50")
    customer.travel_distance_km = Decimal(23)
    customer.save()
    [line] = _preview(client, customer, {"visit_id": str(visit.id)}).json()["lines"]
    assert (line["quantity"], line["unit"], line["total"]) == ("46.00", "km", "23.00")

    # The visit's own distance wins; one way when the rate says so.
    visit.distance_km = Decimal(30)
    visit.save()
    TravelRate.objects.update(round_trip=False)
    [line] = _preview(client, customer, {"visit_id": str(visit.id)}).json()["lines"]
    assert line["quantity"] == "30.00"


@pytest.mark.django_db
def test_customer_rate_beats_the_default_and_texts_can_be_changed(client, user, customer, visit):
    _rate(user)
    _rate(user, amount="60", customer=customer)
    r = _preview(client, customer, {"visit_id": str(visit.id), "description": "Fahrt"})
    [line] = r.json()["lines"]
    assert (line["unit_price"], line["description"]) == ("60.00", "Fahrt")
    assert line["default_description"] == "Anfahrt 01.09.2026 (V-0001)"


@pytest.mark.django_db
def test_missing_rate_or_distance_is_refused(client, user, customer, visit):
    r = _preview(client, customer, {"visit_id": str(visit.id)})
    assert r.status_code == 400
    _rate(user, kind="km", amount="0.50")
    r = _preview(client, customer, {"visit_id": str(visit.id)})
    assert r.status_code == 400
    assert "01.09.2026" in str(r.json())


@pytest.mark.django_db
def test_only_open_uncovered_trips_are_offered(client, user, customer, project, visit, contract):
    _rate(user)
    off = OnSiteVisit.objects.create(
        owner=user, customer=customer, date=date(2026, 9, 2), bill_travel=False
    )
    assert _billable(client, customer) == [str(visit.id)]
    assert _billable(client, customer, date_from="2026-09-02") == []
    assert off.bill_travel is False

    contract.travel_included = True
    contract.save()
    assert _billable(client, customer) == []
    assert _preview(client, customer, {"visit_id": str(visit.id)}).status_code == 400


@pytest.mark.django_db
def test_billing_links_the_trip_and_deleting_the_line_releases_it(client, user, customer, visit):
    _rate(user)
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {"customer_id": str(customer.id), "entry_ids": [], "travel": [{"visit_id": str(visit.id)}]},
        format="json",
    )
    assert r.status_code == 201, r.json()
    invoice = Invoice.objects.get(pk=r.json()["id"])
    visit.refresh_from_db()
    assert visit.invoice == invoice
    assert client.get(f"/api/v1/visits/{visit.id}/").json()["invoice_number"] == invoice.number
    assert _billable(client, customer) == []
    assert _billable(client, customer, invoice=invoice.id) == [str(visit.id)]

    # Twice on one invoice, or on a second one, is refused.
    again = _preview(client, customer, {"visit_id": str(visit.id)})
    assert again.status_code == 400

    item = invoice.items.get()
    assert client.delete(f"/api/v1/invoice-items/{item.id}/").status_code == 204
    visit.refresh_from_db()
    assert visit.invoice is None
    assert _billable(client, customer) == [str(visit.id)]


@pytest.mark.django_db
def test_draft_keeps_its_trips_and_releases_dropped_ones(client, user, customer, visit):
    _rate(user)
    second = OnSiteVisit.objects.create(owner=user, customer=customer, date=date(2026, 9, 3))
    trips = [{"visit_id": str(visit.id), "description": "Fahrt"}, {"visit_id": str(second.id)}]
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {"customer_id": str(customer.id), "entry_ids": [], "travel": trips},
        format="json",
    )
    invoice_id = r.json()["id"]
    state = client.get(f"/api/v1/invoices/{invoice_id}/draft/").json()
    assert [t["id"] for t in state["trips"]] == [str(visit.id), str(second.id)]
    assert state["trip_texts"] == {f"travel:{visit.id}": "Fahrt"}

    r = client.put(
        f"/api/v1/invoices/{invoice_id}/draft/",
        {"customer_id": str(customer.id), "entry_ids": [], "travel": [trips[1]]},
        format="json",
    )
    assert r.status_code == 200, r.json()
    visit.refresh_from_db()
    second.refresh_from_db()
    assert visit.invoice is None
    assert str(second.invoice_id) == invoice_id


@pytest.mark.django_db
def test_xrechnung_names_kilometres(client, user, customer, visit):
    from core.services.erechnung import UNIT_CODES

    assert UNIT_CODES["km"] == "KMT"


@pytest.mark.django_db
def test_travel_terms_name_the_rate_and_contract_coverage(client, user, customer, contract):
    url = f"/api/v1/visits/travel-terms/?customer={customer.id}&date=2026-09-01"
    assert client.get(url).json() == {
        "rate": None,
        "included": False,
        "customer_distance_km": None,
    }
    _rate(user, kind="km", amount="0.50", round_trip=False)
    contract.travel_included = True
    contract.save()
    assert client.get(url).json() == {
        "rate": {"kind": "km", "amount": "0.50", "round_trip": False},
        "included": True,
        "customer_distance_km": None,
    }


@pytest.mark.django_db
def test_the_visits_own_price_beats_the_rate(client, user, customer, visit):
    visit.distance_km = Decimal(10)
    visit.travel_price = Decimal("0.40")
    visit.save()
    # Without a rate: per km, there and back.
    [line] = _preview(client, customer, {"visit_id": str(visit.id)}).json()["lines"]
    assert (line["quantity"], line["unit"], line["unit_price"]) == ("20.00", "km", "0.40")

    _rate(user, amount="45")
    [line] = _preview(client, customer, {"visit_id": str(visit.id)}).json()["lines"]
    assert (line["quantity"], line["unit"], line["unit_price"]) == ("1.00", "flat", "0.40")
