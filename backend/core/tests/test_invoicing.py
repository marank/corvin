from datetime import date, datetime
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    BankAccount,
    HourlyRate,
    Invoice,
    TimeEntry,
)
from core.services.consolidation import consolidate


@pytest.fixture
def draft_invoice(user, customer, project, invoice_template):
    company = user.company_settings
    company.default_bank_account = BankAccount.objects.create(
        owner=user, name="Geschäftskonto", account_holder="Alice", iban="DE89370400440532013000"
    )
    company.save()
    HourlyRate.objects.create(
        owner=user,
        customer=customer,
        amount=Decimal(80),
        valid_from=date(2025, 1, 1),
    )
    tz = timezone.get_current_timezone()
    TimeEntry.objects.create(
        owner=user,
        customer=customer,
        project=project,
        start_datetime=datetime(2026, 9, 1, 9, 0, tzinfo=tz),
        end_datetime=datetime(2026, 9, 1, 11, 0, tzinfo=tz),
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
    assert doc.sha256
    assert doc.file.size > 1000
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


@pytest.mark.django_db
def test_finalize_requires_bank_account(user, draft_invoice):
    company = user.company_settings
    company.default_bank_account = None
    company.save()
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(f"/api/v1/invoices/{draft_invoice.id}/finalize/")
    assert r.status_code == 400
    draft_invoice.refresh_from_db()
    assert draft_invoice.status == Invoice.Status.DRAFT


@pytest.fixture
def issued_invoice(user, draft_invoice):
    c = APIClient()
    c.force_authenticate(user)
    assert c.post(f"/api/v1/invoices/{draft_invoice.id}/finalize/").status_code == 200
    draft_invoice.refresh_from_db()
    return draft_invoice


@pytest.mark.django_db
def test_send_email_sends_pdf_after_commit_and_marks_sent(
    user, issued_invoice, mailoutbox, django_capture_on_commit_callbacks
):
    c = APIClient()
    c.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        r = c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {
                "to": "billing@acme.test",
                "subject": "Rechnung {{ invoice.number }}",
                "body": "Hallo",
            },
            format="json",
        )
    assert r.status_code == 202
    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    assert mail.to == ["billing@acme.test"]
    # Rendered when the user sent it, not later in the job.
    assert mail.subject == f"Rechnung {issued_invoice.number}"
    name, content, mimetype = mail.attachments[0]
    assert name == f"{issued_invoice.number}.pdf"
    assert mimetype == "application/pdf"
    assert content.startswith(b"%PDF")
    issued_invoice.refresh_from_db()
    assert issued_invoice.status == Invoice.Status.SENT
    assert issued_invoice.sent_at is not None


@pytest.mark.django_db
def test_send_email_sends_nothing_before_commit(user, issued_invoice, mailoutbox):
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(
        f"/api/v1/invoices/{issued_invoice.id}/send_email/",
        {"to": "billing@acme.test"},
        format="json",
    )
    assert r.status_code == 202
    # The test's transaction never commits, so the job never runs: no mail, still issued.
    assert mailoutbox == []
    issued_invoice.refresh_from_db()
    assert issued_invoice.status == Invoice.Status.ISSUED


@pytest.mark.django_db
def test_send_email_with_queue_defers_job_with_rendered_text(user, issued_invoice, settings):
    settings.JOB_QUEUE = True
    c = APIClient()
    c.force_authenticate(user)
    with mock.patch("core.jobs.app") as app:
        r = c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {"to": "billing@acme.test", "subject": "Nr. {{ invoice.number }}"},
            format="json",
        )
    assert r.status_code == 202
    app.configure_task.assert_called_once_with(
        name="core.tasks.send_invoice_email", queueing_lock=None
    )
    kwargs = app.configure_task.return_value.defer.call_args.kwargs
    assert kwargs["invoice_id"] == str(issued_invoice.id)
    assert kwargs["to"] == "billing@acme.test"
    assert kwargs["subject"] == f"Nr. {issued_invoice.number}"
    assert kwargs["body"]  # the template's or the default text, never empty


@pytest.mark.django_db
def test_send_email_rejects_invalid_address(user, issued_invoice, mailoutbox):
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(
        f"/api/v1/invoices/{issued_invoice.id}/send_email/", {"to": "no-address"}, format="json"
    )
    assert r.status_code == 400
    assert "to" in r.json()
