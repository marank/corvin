"""Invoices written elsewhere, uploaded with the time entries they billed."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import Invoice, TimeEntry

PDF = b"%PDF-1.4 external invoice"
XML = b"<?xml version='1.0'?><Invoice/>"


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def _upload(client, customer, **extra):
    data = {
        "customer_id": str(customer.id),
        "number": "IN-2026-17",
        "issue_date": "2026-10-01",
        "net": "100.00",
        "vat_rate": "19",
        "pdf": SimpleUploadedFile("in.pdf", PDF, content_type="application/pdf"),
        **extra,
    }
    return client.post("/api/v1/invoices/import_external/", data, format="multipart")


@pytest.mark.django_db
def test_an_external_invoice_is_recorded_as_issued(client, customer, project, make_entry):
    entries = [make_entry(d=date(2026, 9, 1)), make_entry(d=date(2026, 9, 2))]
    other = make_entry(d=date(2026, 9, 3))
    r = _upload(
        client,
        customer,
        entry_ids=[str(e.id) for e in entries],
        xml=SimpleUploadedFile("in.xml", XML, content_type="application/xml"),
    )
    assert r.status_code == 201, r.json()
    invoice = Invoice.objects.get(pk=r.json()["id"])
    assert invoice.is_external
    assert invoice.status == Invoice.Status.ISSUED
    assert invoice.number == "IN-2026-17"
    assert (invoice.subtotal, invoice.vat_amount, invoice.total) == (
        Decimal(100),
        Decimal(19),
        Decimal(119),
    )
    # Billed: off the open entries, on its line, project taken from them.
    assert set(TimeEntry.objects.filter(invoice=invoice)) == set(entries)
    assert TimeEntry.objects.get(pk=other.pk).invoice is None
    assert set(invoice.items.get().time_entries.all()) == set(entries)
    assert invoice.project == project
    assert invoice.e_invoice_format == Invoice.EInvoiceFormat.XRECHNUNG
    assert r.json()["has_time_entries"] is True

    # The uploaded files are the originals.
    pdf = client.get(f"/api/v1/invoices/{invoice.id}/pdf/?inline=1")
    assert b"".join(pdf.streaming_content) == PDF
    assert "attachment" not in pdf["Content-Disposition"]
    assert client.get(f"/api/v1/invoices/{invoice.id}/xrechnung/").content == XML


@pytest.mark.django_db
def test_without_vat_the_amount_is_all(client, user, customer):
    user.company_settings.vat_enabled = False
    user.company_settings.save()
    r = _upload(client, customer, net="250.00", vat_rate="19")
    invoice = Invoice.objects.get(pk=r.json()["id"])
    assert (invoice.vat_rate, invoice.total) == (Decimal(0), Decimal(250))
    assert invoice.e_invoice_format == Invoice.EInvoiceFormat.NONE


@pytest.mark.django_db
def test_due_date_defaults_to_the_payment_terms(client, customer):
    r = _upload(client, customer)
    assert r.json()["due_date"] == "2026-10-15"
    r = _upload(client, customer, number="IN-2", due_date="2026-11-30")
    assert r.json()["due_date"] == "2026-11-30"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("extra", "field"),
    [
        ({"pdf": SimpleUploadedFile("x.pdf", b"not a pdf")}, "pdf"),
        ({"xml": SimpleUploadedFile("x.xml", b"%PDF")}, "xml"),
        ({"number": "TAKEN"}, "number"),
    ],
)
def test_bad_uploads_are_refused(client, user, customer, extra, field):
    Invoice.objects.create(
        owner=user, customer=customer, number="TAKEN", issue_date=date(2026, 9, 1)
    )
    r = _upload(client, customer, **extra)
    assert r.status_code == 400
    assert field in r.json()
    assert Invoice.objects.count() == 1


@pytest.mark.django_db
def test_entries_billed_already_are_refused(client, customer, make_entry):
    entry = make_entry()
    assert _upload(client, customer, entry_ids=[str(entry.id)]).status_code == 201
    r = _upload(client, customer, number="IN-2", entry_ids=[str(entry.id)])
    assert r.status_code == 400
    assert "entry_ids" in r.json()


@pytest.mark.django_db
def test_projects_of_other_customers_are_refused(client, user, customer):
    from core.models import Customer, Project

    other = Customer.objects.create(owner=user, name="Beta AG")
    theirs = Project.objects.create(owner=user, customer=other, name="Fremd")
    assert _upload(client, customer, project_id=str(theirs.id)).status_code == 400
