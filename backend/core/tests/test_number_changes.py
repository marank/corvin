from datetime import date

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from rest_framework.test import APIClient

from core.models import Customer, DocumentArchive, Invoice, OnSiteVisit, Project, Task
from core.services.numbering import next_number


@pytest.fixture
def client(user):
    value = APIClient()
    value.force_authenticate(user)
    return value


def make_invoice(user, customer, status=Invoice.Status.DRAFT, **kw):
    return Invoice.objects.create(
        owner=user,
        customer=customer,
        number=kw.pop("number", "RE-1"),
        issue_date=date(2026, 9, 1),
        status=status,
        **kw,
    )


@pytest.mark.django_db
def test_customer_number_can_be_changed_without_finalized_invoice(client, user, customer):
    make_invoice(user, customer)  # a draft does not lock
    r = client.patch(f"/api/v1/customers/{customer.id}/", {"number": " K-42 "}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["number"] == "K-42"
    assert r.json()["number_locked"] is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status", [Invoice.Status.ISSUED, Invoice.Status.SENT, Invoice.Status.PAID]
)
def test_finalized_invoice_locks_customer_project_and_contract(
    client, user, customer, project, contract, status
):
    make_invoice(user, customer, status, project=project, contract=contract)
    for url, obj in [
        ("customers", customer),
        ("projects", project),
        ("support-contracts", contract),
    ]:
        assert client.get(f"/api/v1/{url}/{obj.id}/").json()["number_locked"] is True
        r = client.patch(f"/api/v1/{url}/{obj.id}/", {"number": "NEW-1"}, format="json")
        assert r.status_code == 400
        assert "number" in r.json()
    # Unchanged numbers still pass, so the rest of the record stays editable.
    r = client.patch(
        f"/api/v1/customers/{customer.id}/",
        {"number": customer.number, "name": "Renamed"},
        format="json",
    )
    assert r.status_code == 200, r.json()


@pytest.mark.django_db
def test_cancelled_invoice_locks_only_once_archived(client, user, customer):
    invoice = make_invoice(user, customer, Invoice.Status.CANCELLED)
    assert client.get(f"/api/v1/customers/{customer.id}/").json()["number_locked"] is False
    DocumentArchive.objects.create(
        owner=user,
        content_type=ContentType.objects.get_for_model(Invoice),
        object_id=invoice.id,
        kind="pdf",
        file=ContentFile(b"%PDF", name="RE-1.pdf"),
        sha256="0" * 64,
    )
    assert client.get(f"/api/v1/customers/{customer.id}/").json()["number_locked"] is True


@pytest.mark.django_db
def test_number_must_be_unique_and_not_empty(client, user, customer):
    customer.number = "K-1000"
    customer.save()
    Customer.objects.create(owner=user, name="Other", number="K-1")
    r = client.patch(f"/api/v1/customers/{customer.id}/", {"number": "K-1"}, format="json")
    assert r.status_code == 400
    r = client.patch(f"/api/v1/customers/{customer.id}/", {"number": "  "}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_number_sent_on_create_is_ignored(client, user):
    r = client.post("/api/v1/customers/", {"name": "New", "number": "MINE"}, format="json")
    assert r.status_code == 201, r.json()
    assert r.json()["number"] != "MINE"


@pytest.mark.django_db
def test_visit_and_task_numbers_never_lock(client, user, customer, project):
    make_invoice(user, customer, Invoice.Status.ISSUED, project=project)
    visit = OnSiteVisit.objects.create(
        owner=user, customer=customer, project=project, date=date(2026, 9, 1), number="B-1"
    )
    task = Task.objects.create(owner=user, customer=customer, title="Do it", number="T-1")
    r = client.patch(f"/api/v1/visits/{visit.id}/", {"number": "B-9"}, format="json")
    assert r.status_code == 200, r.json()
    r = client.patch(f"/api/v1/tasks/{task.id}/", {"number": "T-9"}, format="json")
    assert r.status_code == 200, r.json()


@pytest.mark.django_db
def test_draft_invoice_number_editable_finalized_not(client, user, customer):
    draft = make_invoice(user, customer, number="RE-1")
    r = client.patch(f"/api/v1/invoices/{draft.id}/", {"number": "RE-7"}, format="json")
    assert r.status_code == 200, r.json()
    issued = make_invoice(user, customer, Invoice.Status.ISSUED, number="RE-2")
    r = client.patch(f"/api/v1/invoices/{issued.id}/", {"number": "RE-8"}, format="json")
    assert r.status_code == 400
    issued.refresh_from_db()
    assert issued.number == "RE-2"


@pytest.mark.django_db
def test_next_number_skips_numbers_given_by_hand(user, customer):
    settings = user.company_settings
    settings.numbering_schemes["project"] = {"format": "P-{counter}", "scope": [], "start": 1}
    settings.save(update_fields=["numbering_schemes"])
    Project.objects.create(owner=user, customer=customer, name="A", number="P-1")
    Project.objects.create(owner=user, customer=customer, name="B", number="P-2")
    assert next_number(user, "project") == "P-3"
    assert next_number(user, "project") == "P-4"


@pytest.mark.django_db
def test_next_number_without_counter_does_not_loop(user, customer):
    settings = user.company_settings
    settings.numbering_schemes["project"] = {"format": "FIXED", "scope": [], "start": 1}
    settings.save(update_fields=["numbering_schemes"])
    Project.objects.create(owner=user, customer=customer, name="A", number="FIXED")
    assert next_number(user, "project") == "FIXED"
