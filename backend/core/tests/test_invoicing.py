from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    BankAccount,
    CompanyImage,
    Contact,
    HourlyRate,
    Invoice,
    InvoiceMail,
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
def test_mark_sent_on_an_earlier_day(user, draft_invoice):
    Invoice.objects.filter(pk=draft_invoice.pk).update(
        status=Invoice.Status.ISSUED, issue_date=date(2026, 9, 1)
    )
    c = APIClient()
    c.force_authenticate(user)
    url = f"/api/v1/invoices/{draft_invoice.id}/mark_sent/"
    assert c.post(url, {"sent_on": "2026-08-31"}, format="json").status_code == 400
    tomorrow = timezone.localdate() + timedelta(days=1)
    assert c.post(url, {"sent_on": tomorrow.isoformat()}, format="json").status_code == 400

    r = c.post(url, {"sent_on": "2026-09-03"}, format="json")
    assert r.status_code == 200
    draft_invoice.refresh_from_db()
    assert draft_invoice.status == Invoice.Status.SENT
    assert draft_invoice.sent_at is not None
    assert timezone.localdate(draft_invoice.sent_at) == date(2026, 9, 3)


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
def no_queue(settings):
    """Jobs run in-process after the commit, as natively, whatever the test database."""
    settings.JOB_QUEUE = False


@pytest.fixture
def issued_invoice(user, draft_invoice):
    c = APIClient()
    c.force_authenticate(user)
    assert c.post(f"/api/v1/invoices/{draft_invoice.id}/finalize/").status_code == 200
    draft_invoice.refresh_from_db()
    return draft_invoice


@pytest.mark.django_db
def test_send_email_sends_pdf_after_commit_and_marks_sent(
    no_queue, user, issued_invoice, mailoutbox, django_capture_on_commit_callbacks
):
    c = APIClient()
    c.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        r = c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {"to": ["billing@acme.test"], "subject": "Ihre Rechnung"},
            format="json",
        )
    assert r.status_code == 202
    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    assert mail.to == ["billing@acme.test"]
    # The subject as the user confirmed it; the text from the invoice mail template, as
    # HTML with a plain-text part.
    assert mail.subject == "Ihre Rechnung"
    assert f"Rechnung {issued_invoice.number}" in mail.body
    [(html, mimetype)] = mail.alternatives
    assert mimetype == "text/html"
    assert f"Rechnung {issued_invoice.number}" in html
    name, content, mimetype = mail.attachments[0]
    assert name == f"{issued_invoice.number}.pdf"
    assert mimetype == "application/pdf"
    assert content.startswith(b"%PDF")
    issued_invoice.refresh_from_db()
    assert issued_invoice.status == Invoice.Status.SENT
    assert issued_invoice.sent_at is not None


@pytest.mark.django_db
def test_mails_show_company_images_inline(
    no_queue, user, issued_invoice, mailoutbox, django_capture_on_commit_callbacks
):
    from core.tests.test_company_images import image_file

    CompanyImage.objects.create(owner=user, kind="logo_light", image=image_file())
    c = APIClient()
    c.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {"to": ["billing@acme.test"]},
            format="json",
        )
    message = mailoutbox[0].message()
    html = next(p for p in message.walk() if p.get_content_type() == "text/html")
    assert 'src="cid:logo_light"' in html.get_content()
    related = next(p for p in message.walk() if p.get_content_type() == "multipart/related")
    image = next(p for p in related.iter_parts() if p.get_content_maintype() == "image")
    assert image["Content-ID"] == "<logo_light>"


@pytest.mark.django_db
def test_xrechnung_mails_carry_the_xml(
    no_queue, user, draft_invoice, mailoutbox, django_capture_on_commit_callbacks
):
    draft_invoice.e_invoice_format = Invoice.EInvoiceFormat.XRECHNUNG
    draft_invoice.save(update_fields=["e_invoice_format"])
    c = APIClient()
    c.force_authenticate(user)
    assert c.post(f"/api/v1/invoices/{draft_invoice.id}/finalize/").status_code == 200
    with django_capture_on_commit_callbacks(execute=True):
        c.post(
            f"/api/v1/invoices/{draft_invoice.id}/send_email/",
            {"to": ["billing@acme.test"]},
            format="json",
        )
    names = [name for name, _content, _mime in mailoutbox[0].attachments]
    assert names == [f"{draft_invoice.number}.pdf", f"{draft_invoice.number}.xml"]


@pytest.mark.django_db
def test_payment_reminders_leave_the_status(
    no_queue, user, issued_invoice, mailoutbox, django_capture_on_commit_callbacks
):
    c = APIClient()
    c.force_authenticate(user)
    draft = c.get(f"/api/v1/invoices/{issued_invoice.id}/email_draft/?kind=payment_reminder")
    assert draft.json()["subject"] == f"Zahlungserinnerung: Rechnung {issued_invoice.number}"
    with django_capture_on_commit_callbacks(execute=True):
        r = c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {"to": ["billing@acme.test"], "kind": "payment_reminder"},
            format="json",
        )
    assert r.status_code == 202
    assert mailoutbox[0].subject.startswith("Zahlungserinnerung")
    issued_invoice.refresh_from_db()
    assert issued_invoice.status == Invoice.Status.ISSUED
    assert c.get(f"/api/v1/invoices/{issued_invoice.id}/email_draft/?kind=x").status_code == 400


@pytest.fixture
def two_contacts(user, issued_invoice):
    erika = Contact.objects.create(
        owner=user,
        customer=issued_invoice.customer,
        first_name="Erika",
        last_name="Muster",
        email="erika@acme.test",
        salutation_name="Frau Muster",
    )
    max_ = Contact.objects.create(
        owner=user,
        customer=issued_invoice.customer,
        first_name="Max",
        last_name="Other",
        email="max@acme.test",
    )
    issued_invoice.contacts.set([erika, max_])
    return erika, max_


def _draft(client, invoice, *to):
    query = "&".join(f"to={address}" for address in to)
    return client.get(f"/api/v1/invoices/{invoice.id}/email_draft/?{query}").json()


@pytest.mark.django_db
def test_mails_greet_everyone_they_go_to(user, issued_invoice, two_contacts):
    c = APIClient()
    c.force_authenticate(user)
    draft = _draft(c, issued_invoice)
    assert draft["to"] == ["erika@acme.test", "max@acme.test"]
    assert "<p>Guten Tag Frau Muster und Max Other,</p>" in draft["html"]
    # Only who it goes to, in that order; unknown addresses add no name.
    assert "<p>Guten Tag Max Other,</p>" in _draft(c, issued_invoice, "max@acme.test")["html"]
    assert "<p>Guten Tag,</p>" in _draft(c, issued_invoice, "office@acme.test")["html"]


@pytest.mark.django_db
def test_templates_greet_each_recipient_as_they_like(user, issued_invoice, two_contacts):
    from core.services.mail_templates import mail_template_for

    template = mail_template_for(user, "invoice")
    template.html = (
        "{% block anrede %}<p>{% for r in recipients %}Hallo {{ r.name }}"
        "{% if not forloop.last %}, {% endif %}{% endfor %},</p>{% endblock %}"
    )
    template.save()
    c = APIClient()
    c.force_authenticate(user)
    html = _draft(c, issued_invoice, "max@acme.test", "erika@acme.test")["html"]
    assert "<p>Hallo Max Other, Hallo Frau Muster,</p>" in html


@pytest.mark.django_db
def test_mails_go_to_several_addresses(
    no_queue, user, issued_invoice, two_contacts, mailoutbox, django_capture_on_commit_callbacks
):
    c = APIClient()
    c.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        r = c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {"to": ["erika@acme.test", "max@acme.test"]},
            format="json",
        )
    assert r.status_code == 202
    assert mailoutbox[0].to == ["erika@acme.test", "max@acme.test"]
    assert "Guten Tag Frau Muster und Max Other," in mailoutbox[0].body
    assert (
        c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/", {"to": []}, format="json"
        ).status_code
        == 400
    )


def test_names_are_joined_in_the_documents_language():
    from django.utils.translation import override

    from core.services.mailer import join_names

    assert join_names([]) == ""
    assert join_names(["Erika"]) == "Erika"
    with override("de"):
        assert join_names(["Erika", "Max", "Tom"]) == "Erika, Max und Tom"
    with override("en"):
        assert join_names(["Erika", "Max"]) == "Erika and Max"


@pytest.mark.django_db
def test_send_email_sends_nothing_before_commit(no_queue, user, issued_invoice, mailoutbox):
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(
        f"/api/v1/invoices/{issued_invoice.id}/send_email/",
        {"to": ["billing@acme.test"]},
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
            {"to": ["billing@acme.test"]},
            format="json",
        )
    assert r.status_code == 202
    app.configure_task.assert_called_once_with(
        name="core.tasks.send_invoice_mail", queueing_lock=None
    )
    kwargs = app.configure_task.return_value.defer.call_args.kwargs
    # Rendered now from the template and recorded: the job sends exactly this.
    mail = InvoiceMail.objects.get(pk=kwargs["mail_id"])
    assert mail.invoice == issued_invoice
    assert mail.to == ["billing@acme.test"]
    assert mail.subject == f"Rechnung {issued_invoice.number}"
    assert issued_invoice.number in mail.html
    assert issued_invoice.number in mail.text
    assert mail.kind == "invoice"
    assert mail.status == InvoiceMail.Status.QUEUED
    assert mail.attachments == [f"{issued_invoice.number}.pdf"]


@pytest.mark.django_db
def test_the_history_shows_what_went_to_whom(
    no_queue, user, issued_invoice, mailoutbox, django_capture_on_commit_callbacks
):
    c = APIClient()
    c.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {"to": ["billing@acme.test"], "subject": "Ihre Rechnung"},
            format="json",
        )
        c.post(
            f"/api/v1/invoices/{issued_invoice.id}/send_email/",
            {"to": ["billing@acme.test"], "kind": "payment_reminder"},
            format="json",
        )
    history = c.get(f"/api/v1/invoices/{issued_invoice.id}/mails/").json()
    assert [(m["kind"], m["status"]) for m in history] == [
        ("payment_reminder", "sent"),
        ("invoice", "sent"),
    ]
    assert history[1]["subject"] == "Ihre Rechnung"
    assert history[1]["to"] == ["billing@acme.test"]
    assert history[1]["sent_at"]
    assert "html" not in history[1]

    detail = c.get(f"/api/v1/invoices/{issued_invoice.id}/mails/{history[1]['id']}/").json()
    assert issued_invoice.number in detail["html"]
    missing = c.get(f"/api/v1/invoices/{issued_invoice.id}/mails/{issued_invoice.id}/")
    assert missing.status_code == 404


@pytest.mark.django_db
def test_a_failed_attempt_is_noted_and_retried(user, issued_invoice):
    from core.services.mailer import queue_invoice_email, send_invoice_mail

    with mock.patch("core.services.mailer.defer"):
        queue_invoice_email(issued_invoice, ["billing@acme.test"])
    mail = InvoiceMail.objects.get()
    with (
        mock.patch("core.services.mailer.HtmlMail.send", side_effect=OSError("SMTP down")),
        pytest.raises(OSError, match="SMTP down"),
    ):
        send_invoice_mail(str(mail.pk))
    mail.refresh_from_db()
    assert mail.status == InvoiceMail.Status.QUEUED
    assert mail.error == "SMTP down"
    issued_invoice.refresh_from_db()
    assert issued_invoice.status == Invoice.Status.ISSUED

    with mock.patch("core.services.mailer.HtmlMail.send") as send:
        send_invoice_mail(str(mail.pk))
        send_invoice_mail(str(mail.pk))  # a retry after it went out: nothing twice
    assert send.call_count == 1
    mail.refresh_from_db()
    assert mail.status == InvoiceMail.Status.SENT
    assert mail.error == ""


@pytest.mark.django_db
def test_send_email_rejects_invalid_address(no_queue, user, issued_invoice, mailoutbox):
    c = APIClient()
    c.force_authenticate(user)
    r = c.post(
        f"/api/v1/invoices/{issued_invoice.id}/send_email/", {"to": ["no-address"]}, format="json"
    )
    assert r.status_code == 400
    assert "to" in r.json()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "state", [Invoice.Status.DRAFT, Invoice.Status.CANCELLED, Invoice.Status.PAID]
)
def test_send_email_refuses_invoices_that_are_not_finalized(
    no_queue, user, draft_invoice, state, mailoutbox, django_capture_on_commit_callbacks
):
    draft_invoice.status = state
    draft_invoice.save(update_fields=["status"])
    c = APIClient()
    c.force_authenticate(user)
    with django_capture_on_commit_callbacks(execute=True):
        r = c.post(
            f"/api/v1/invoices/{draft_invoice.id}/send_email/",
            {"to": ["billing@acme.test"]},
            format="json",
            HTTP_ACCEPT_LANGUAGE="en",
        )
    assert r.status_code == 400
    assert r.json()["detail"] == ["Only finalized invoices can be sent."]
    assert mailoutbox == []
    # Nothing was archived: a draft stays editable.
    assert not draft_invoice.documents.exists()
    draft_invoice.refresh_from_db()
    assert draft_invoice.status == state
