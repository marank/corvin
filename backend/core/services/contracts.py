from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.models import Invoice, InvoiceLineItem, SupportContract, TimeEntry
from core.models.support_contract import add_periods

from .numbering import next_number
from .rates import resolve_rate

PERIOD_LABELS = {
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "yearly": "Yearly",
}


def contract_usage(contract: SupportContract) -> dict[str, Any]:
    """Used/included/overage hours of the current billing period."""
    start, end = contract.current_period()
    qs = TimeEntry.objects.filter(
        contract=contract,
        start_datetime__date__gte=start,
        start_datetime__date__lt=end,
        end_datetime__isnull=False,
    )
    minutes = sum(e.duration_minutes for e in qs)
    used = Decimal(minutes) / 60
    included = contract.included_hours
    return {
        "period_start": start,
        "period_end": end,
        "used_hours": used.quantize(Decimal("0.01")),
        "included_hours": included,
        "overage_hours": max(used - included, Decimal(0)).quantize(Decimal("0.01")),
    }


@transaction.atomic
def generate_invoice(contract: SupportContract) -> Invoice:
    """Create the draft invoice for the contract's current period."""
    owner = contract.owner
    start, end = contract.current_period()
    usage = contract_usage(contract)

    company = getattr(owner, "company_settings", None)
    issue_date = timezone.localdate()
    payment_terms_days = (
        contract.customer.payment_terms_days
        if contract.customer.payment_terms_days is not None
        else company.payment_terms_days
        if company
        else 14
    )
    vat_rate = (
        company.default_vat_rate
        if company and company.vat_enabled
        else Decimal(0)
        if company
        else Decimal(19)
    )
    invoice = Invoice.objects.create(
        owner=owner,
        number=next_number(
            owner,
            "invoice",
            {
                "customer": contract.customer,
                "project": contract.project,
                "contract": contract,
                "invoice": SimpleNamespace(
                    customer=contract.customer,
                    project=contract.project,
                    contract=contract,
                    issue_date=issue_date,
                ),
            },
        ),
        customer=contract.customer,
        project=contract.project,
        contract=contract,
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=payment_terms_days),
        vat_rate=vat_rate,
        currency=company.currency if company else "EUR",
        template=contract.template,
    )

    invoice.contacts.set(contract.customer.contacts.filter(is_invoice_contact=True))

    label = PERIOD_LABELS[contract.period]
    InvoiceLineItem.objects.create(
        owner=owner,
        invoice=invoice,
        position=1,
        description=(f"{contract.name} — {label} support ({start} – {end})"),
        quantity=1,
        unit=InvoiceLineItem.Unit.FLAT,
        unit_price=contract.fixed_price,
    )

    if contract.bill_overage and usage["overage_hours"] > 0:
        rate = contract.overage_rate
        if rate is None:
            rate = resolve_rate(
                owner=owner,
                customer=contract.customer,
                project=contract.project,
                on_date=end,
            ) or Decimal(0)
        InvoiceLineItem.objects.create(
            owner=owner,
            invoice=invoice,
            position=2,
            description=(f"{contract.name} — additional hours beyond {contract.included_hours}h"),
            quantity=usage["overage_hours"],
            unit=InvoiceLineItem.Unit.HOURS,
            unit_price=rate,
        )

    # link covered entries to the generated invoice for traceability
    TimeEntry.objects.filter(
        contract=contract,
        start_datetime__date__gte=start,
        start_datetime__date__lt=end,
        end_datetime__isnull=False,
        invoice__isnull=True,
    ).update(invoice=invoice)

    invoice.recalc_totals()
    return invoice


@transaction.atomic
def process_due(owner: User | None = None, today: date | None = None) -> list[Invoice]:
    """Generate invoices for all due, active contracts."""
    today = today or timezone.localdate()
    qs = SupportContract.objects.filter(active=True, next_billing_date__lte=today)
    if owner is not None:
        qs = qs.filter(owner=owner)
    invoices = []
    for contract in qs.select_related("customer", "project", "owner"):
        while contract.next_billing_date <= today and (
            contract.end_date is None or contract.next_billing_date <= contract.end_date
        ):
            invoices.append(generate_invoice(contract))
            contract.next_billing_date = add_periods(contract.next_billing_date, contract.period)
            contract.save(update_fields=["next_billing_date", "updated_at"])
            if contract.end_date and contract.next_billing_date > contract.end_date:
                contract.active = False
                contract.save(update_fields=["active", "updated_at"])
                break
    return invoices
