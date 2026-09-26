from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import (
    Customer,
    Invoice,
    InvoiceLineItem,
    Project,
    TimeEntry,
)

from .numbering import next_invoice_number
from .rates import resolve_rate, round_up_minutes, rounding_increment


def _line_for_entries(owner, entries, description: str) -> dict:
    """One line item from a group of entries: round each entry, apply
    each entry's own effective-dated rate, average the unit price."""
    total_minutes = 0
    total_amount = Decimal("0")
    customer = entries[0].project.customer
    for e in entries:
        minutes = round_up_minutes(
            e.duration_minutes,
            rounding_increment(customer, e.project),
        )
        rate = resolve_rate(
            owner=owner, customer=customer, project=e.project, on_date=e.date
        )
        if rate is None:
            raise ValidationError(
                f"No hourly rate found for {customer.name} on {e.date}."
            )
        total_minutes += minutes
        total_amount += Decimal(minutes) / 60 * rate
    quantity = (Decimal(total_minutes) / 60).quantize(Decimal("0.01"))
    unit_price = (
        (total_amount / quantity).quantize(Decimal("0.01"))
        if quantity
        else Decimal("0")
    )
    return {
        "description": description,
        "quantity": quantity,
        "unit": InvoiceLineItem.Unit.HOURS,
        "unit_price": unit_price,
    }


@transaction.atomic
def consolidate(
    *,
    owner,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    group_by: str = "entry",
    vat_rate: Decimal | None = None,
    template=None,
    e_invoice_format: str = Invoice.EInvoiceFormat.NONE,
) -> Invoice:
    qs = TimeEntry.objects.filter(
        owner=owner,
        project__customer=customer,
        billable=True,
        invoice__isnull=True,
        contract__isnull=True,  # contract-covered entries bill via the contract
        end_time__isnull=False,  # running timers excluded
    ).select_related("project", "project__customer")
    if project:
        qs = qs.filter(project=project)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    entries = list(qs.order_by("date", "start_time"))
    if not entries:
        raise ValidationError("No billable, uninvoiced time entries found.")

    # group entries into line items
    groups: dict[tuple, list[TimeEntry]] = defaultdict(list)
    if group_by == "entry":
        for e in entries:
            groups[(e.id,)].append(e)
    elif group_by == "day":
        for e in entries:
            groups[(e.project_id, e.date)].append(e)
    elif group_by == "project":
        for e in entries:
            groups[(e.project_id,)].append(e)
    else:
        raise ValidationError(f"Unknown group_by: {group_by}")

    company = getattr(owner, "company_settings", None)
    prefix = company.invoice_prefix if company else "RE"

    invoice = Invoice.objects.create(
        owner=owner,
        number=next_invoice_number(owner, prefix),
        customer=customer,
        project=project,
        issue_date=timezone.localdate(),
        vat_rate=vat_rate if vat_rate is not None else (
            company.default_vat_rate if company else Decimal("19")
        ),
        e_invoice_format=e_invoice_format,
        template=template,
    )

    for position, (_, group) in enumerate(sorted(groups.items(), key=lambda g: g[0]), start=1):
        first = group[0]
        if group_by == "entry":
            desc = f"{first.date} — {first.project.name}: {first.description or 'Services'}"
        elif group_by == "day":
            desc = f"{first.date} — {first.project.name}"
        else:
            desc = f"{first.project.name} — consulting services"
        line = _line_for_entries(owner, group, desc)
        InvoiceLineItem.objects.create(
            owner=owner, invoice=invoice, position=position, **line
        )

    invoice.recalc_totals()
    qs.update(invoice=invoice)
    return invoice
