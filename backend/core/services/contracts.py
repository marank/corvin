from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import Invoice, InvoiceLineItem, SupportContract, TimeEntry
from core.models.support_contract import add_periods

from .numbering import next_invoice_number
from .rates import resolve_rate

PERIOD_LABELS = {
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "yearly": "Yearly",
}


def contract_usage(contract: SupportContract) -> dict:
    """Used/included/overage hours of the current billing period."""
    start, end = contract.current_period()
    qs = TimeEntry.objects.filter(
        contract=contract, date__gte=start, date__lt=end, end_time__isnull=False
    )
    minutes = sum(e.duration_minutes for e in qs)
    used = Decimal(minutes) / 60
    included = contract.included_hours
    return {
        "period_start": start,
        "period_end": end,
        "used_hours": used.quantize(Decimal("0.01")),
        "included_hours": included,
        "overage_hours": max(used - included, Decimal("0")).quantize(
            Decimal("0.01")
        ),
    }


def generate_invoice(contract: SupportContract) -> Invoice:
    """Create the draft invoice for the contract's current period."""
    owner = contract.owner
    start, end = contract.current_period()
    usage = contract_usage(contract)

    company = getattr(owner, "company_settings", None)
    invoice = Invoice.objects.create(
        owner=owner,
        number=next_invoice_number(
            owner, company.invoice_prefix if company else "RE"
        ),
        customer=contract.customer,
        project=contract.project,
        contract=contract,
        issue_date=timezone.localdate(),
        vat_rate=company.default_vat_rate if company else Decimal("19"),
        template=contract.template,
    )

    label = PERIOD_LABELS[contract.period]
    InvoiceLineItem.objects.create(
        owner=owner,
        invoice=invoice,
        position=1,
        description=(
            f"{contract.name} — {label} support "
            f"({start} – {end})"
        ),
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
            ) or Decimal("0")
        InvoiceLineItem.objects.create(
            owner=owner,
            invoice=invoice,
            position=2,
            description=(
                f"{contract.name} — additional hours beyond "
                f"{contract.included_hours}h"
            ),
            quantity=usage["overage_hours"],
            unit=InvoiceLineItem.Unit.HOURS,
            unit_price=rate,
        )

    # link covered entries to the generated invoice for traceability
    TimeEntry.objects.filter(
        contract=contract, date__gte=start, date__lt=end,
        end_time__isnull=False, invoice__isnull=True,
    ).update(invoice=invoice)

    invoice.recalc_totals()
    return invoice


@transaction.atomic
def process_due(owner=None, today: date | None = None) -> list[Invoice]:
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
            contract.next_billing_date = add_periods(
                contract.next_billing_date, contract.period
            )
            contract.save(update_fields=["next_billing_date", "updated_at"])
            if contract.end_date and contract.next_billing_date > contract.end_date:
                contract.active = False
                contract.save(update_fields=["active", "updated_at"])
                break
    return invoices
