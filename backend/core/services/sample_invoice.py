from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import Invoice

from .pdf import document_context


def _sample_bank_account(owner):
    company = getattr(owner, "company_settings", None)
    if company and company.default_bank_account:
        return company.default_bank_account
    return SimpleNamespace(
        name="Geschäftskonto",
        bank_name="Musterbank",
        account_holder="Musterfirma GmbH",
        iban="DE02120300000000202051",
        bic="BYLADEM1001",
    )


def sample_template_context(owner, for_pdf=False) -> dict:
    """The designer's preview data: the same variables as a real invoice, with sample values."""
    items = [
        SimpleNamespace(
            position=position,
            description=description,
            quantity=quantity,
            unit="hours",
            unit_price=price,
            total=quantity * price,
        )
        for position, (description, quantity, price) in enumerate(
            [
                (_("Consulting"), Decimal("8"), Decimal("85")),
                (_("On-site support"), Decimal("4"), Decimal("95")),
            ],
            start=1,
        )
    ]
    subtotal = sum(item.total for item in items)
    vat_amount = subtotal * Decimal("0.19")
    today = timezone.localdate()
    customer = SimpleNamespace(
        number="K-1001",
        name="Musterkunde GmbH",
        email="buchhaltung@musterkunde.example",
        phone="+49 30 1234567",
        website="https://musterkunde.example",
        vat_id="DE999999999",
        buyer_reference="04011000-12345-67",
        street="Musterstraße 1",
        postal_code="10115",
        city="Berlin",
        country="Deutschland",
    )
    invoice = SimpleNamespace(
        number="RE-2026-0042",
        issue_date=today,
        due_date=today + timedelta(days=14),
        status=Invoice.Status.DRAFT,
        subtotal=subtotal,
        vat_rate=Decimal("19"),
        vat_amount=vat_amount,
        total=subtotal + vat_amount,
        currency="EUR",
        amount_paid=Decimal("0"),
        remaining=subtotal + vat_amount,
        notes="",
        customer=customer,
        project=SimpleNamespace(number="P-2026-007", name="Netzwerk-Erneuerung"),
        contract=SimpleNamespace(number="V-2026-003", name="Wartungsvertrag Server"),
        bank_account=_sample_bank_account(owner),
    )
    contacts = [
        SimpleNamespace(
            name="Erika Musterfrau",
            role="Einkauf",
            email="erika@musterkunde.example",
            phone="+49 30 1234568",
        ),
        SimpleNamespace(
            name="Max Mustermann",
            role="IT-Leitung",
            email="max@musterkunde.example",
            phone="+49 30 1234569",
        ),
    ]
    return document_context(
        invoice, owner=owner, items=items, payments=[], contacts=contacts, for_pdf=for_pdf
    )
