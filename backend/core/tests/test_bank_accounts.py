from datetime import date

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import BankAccount, CompanySettings, Invoice
from core.services.pdf import render_invoice_html


@pytest.mark.django_db
def test_invoice_resolves_bank_account_overrides(user, customer):
    company_account = BankAccount.objects.create(
        owner=user,
        name="Company",
        account_holder="Alice",
        iban="DE001",
    )
    customer_account = BankAccount.objects.create(
        owner=user,
        name="Customer",
        account_holder="Alice",
        iban="DE002",
    )
    invoice_account = BankAccount.objects.create(
        owner=user,
        name="Invoice",
        account_holder="Alice",
        iban="DE003",
    )
    settings = user.company_settings
    settings.default_bank_account = company_account
    settings.save(update_fields=["default_bank_account"])
    invoice = Invoice.objects.create(
        owner=user,
        customer=customer,
        issue_date=date(2026, 1, 1),
    )

    assert invoice.bank_account == company_account
    customer.bank_account = customer_account
    customer.save(update_fields=["bank_account"])
    assert invoice.bank_account == customer_account
    invoice.bank_account_override = invoice_account
    invoice.save(update_fields=["bank_account_override"])
    assert invoice.bank_account == invoice_account


@pytest.mark.django_db
def test_bank_account_api_is_owner_scoped(user):
    other = User.objects.create_user("other")
    CompanySettings.objects.create(user=other)
    foreign = BankAccount.objects.create(
        owner=other,
        name="Foreign",
        account_holder="Other",
        iban="DE999",
    )
    client = APIClient()
    client.force_authenticate(user)

    assert client.get("/api/v1/bank-accounts/").json()["count"] == 0
    response = client.put(
        "/api/v1/settings/",
        {"default_bank_account": str(foreign.id)},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_invoice_template_exposes_resolved_bank_account(
    user,
    customer,
    invoice_template,
):
    account = BankAccount.objects.create(
        owner=user,
        name="Main",
        bank_name="Example Bank",
        account_holder="Alice Consulting",
        iban="DE123",
        bic="TESTBIC",
    )
    customer.bank_account = account
    customer.save(update_fields=["bank_account"])
    invoice = Invoice.objects.create(
        owner=user,
        customer=customer,
        issue_date=date(2026, 1, 1),
        template=invoice_template,
    )
    invoice_template.body_html = (
        "{{ invoice.bank_account.bank_name }}|"
        "{{ invoice.bank_account.account_holder }}|"
        "{{ invoice.bank_account.iban }}|{{ invoice.bank_account.bic }}"
    )
    invoice_template.css = (
        ":root { --page-margin-left: {{ page.margin_left }}mm; "
        "--page-width: {{ page.width }}; --font-size: {{ page.font_size }}pt; "
        "--font: {{ page.primary_font }}; --color: {{ page.primary_color }}; }"
    )
    invoice_template.save(update_fields=["body_html", "css"])

    html = render_invoice_html(invoice)

    assert "Example Bank|Alice Consulting|DE123|TESTBIC" in html
    assert "--page-margin-left: 25mm" in html
    assert "--page-width: 210mm" in html
    assert "--font-size: 10pt" in html
    assert "--font: Arial" in html
    assert "--color: #161616" in html
