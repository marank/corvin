from datetime import date, time
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.models import (
    HourlyRate,
    Invoice,
    InvoiceDocument,
    TimeEntry,
)
from core.services.consolidation import consolidate


@pytest.fixture
def draft_invoice(user, customer, project, invoice_template):
    HourlyRate.objects.create(
        owner=user, customer=customer, amount=Decimal("80"),
        valid_from=date(2025, 1, 1),
    )
    TimeEntry.objects.create(
        owner=user, project=project, date=date(2026, 9, 1),
        start_time=time(9), end_time=time(11),
    )
    return consolidate(owner=user, customer=customer)


@pytest.mark.django_db
def test_finalize_archives_pdf(user, draft_invoice):
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(f"/api/v1/invoices/{draft_invoice.id}/finalize/")
    assert r.status_code == 200
    draft_invoice.refresh_from_db()
    assert draft_invoice.status == Invoice.Status.ISSUED
    doc = InvoiceDocument.objects.get(invoice=draft_invoice, kind="pdf")
    assert doc.sha256 and doc.file.size > 1000
    # PDF download serves the archived file
    r2 = c.get(f"/api/v1/invoices/{draft_invoice.id}/pdf/")
    assert r2.status_code == 200


@pytest.mark.django_db
def test_draft_pdf_renders_live(user, draft_invoice):
    c = APIClient()
    c.force_authenticate(user)
    r = c.get(f"/api/v1/invoices/{draft_invoice.id}/pdf/")
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_partial_payments(user, draft_invoice):
    c = APIClient()
    c.force_authenticate(user)
    c.post(f"/api/v1/invoices/{draft_invoice.id}/finalize/")
    total = draft_invoice.total
    c.post("/api/v1/payments/", {
        "invoice": draft_invoice.id, "date": "2026-09-20",
        "amount": str(total / 2), "note": "half",
    })
    draft_invoice.refresh_from_db()
    assert draft_invoice.partially_paid
    assert draft_invoice.status != Invoice.Status.PAID
    c.post("/api/v1/payments/", {
        "invoice": draft_invoice.id, "date": "2026-09-21",
        "amount": str(total - total / 2),
    })
    draft_invoice.refresh_from_db()
    assert draft_invoice.status == Invoice.Status.PAID


@pytest.mark.django_db
def test_xrechnung_download(user, draft_invoice):
    draft_invoice.e_invoice_format = "xrechnung"
    draft_invoice.save()
    c = APIClient()
    c.force_authenticate(user)
    r = c.get(f"/api/v1/invoices/{draft_invoice.id}/xrechnung/")
    assert r.status_code == 200
    assert b"RE-" in r.content
