from datetime import date, datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    HourlyRate,
    Invoice,
    TimeEntry,
)
from core.services.consolidation import consolidate


@pytest.fixture
def draft_invoice(user, customer, project, invoice_template):
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal("80"),
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
    return consolidate(owner=user, customer=customer)


@pytest.mark.django_db
def test_finalize_archives_pdf(user, draft_invoice):
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(f"/api/v1/invoices/{draft_invoice.id}/finalize/")
    assert r.status_code == 200
    draft_invoice.refresh_from_db()
    assert draft_invoice.status == Invoice.Status.ISSUED
    doc = draft_invoice.documents.filter(kind="pdf").first()
    assert doc is not None
    assert doc.sha256 and doc.file.size > 1000
    # PDF download serves the archived file
    r2 = c.get(f"/api/v1/invoices/{draft_invoice.id}/pdf/")
    assert r2.status_code == 200


@pytest.mark.django_db
def test_mark_sent_updates_status_and_timestamp(user, draft_invoice):
    draft_invoice.status = Invoice.Status.ISSUED
    draft_invoice.save(update_fields=["status"])
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(f"/api/v1/invoices/{draft_invoice.id}/mark_sent/")
    assert r.status_code == 200
    assert r.json()["status"] == Invoice.Status.SENT
    assert r.json()["sent_at"] is not None


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
    c.post(
        "/api/v1/payments/",
        {
            "invoice": draft_invoice.id,
            "date": "2026-09-20",
            "amount": str(total / 2),
            "note": "half",
        },
    )
    draft_invoice.refresh_from_db()
    assert draft_invoice.partially_paid
    assert draft_invoice.status != Invoice.Status.PAID
    c.post(
        "/api/v1/payments/",
        {
            "invoice": draft_invoice.id,
            "date": "2026-09-21",
            "amount": str(total - total / 2),
        },
    )
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
