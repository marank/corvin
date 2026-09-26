from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

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

from .numbering import next_number
from .rates import resolve_rate, round_up_minutes, rounding_increment


def _line_for_entries(owner, entries, description: str) -> dict:
    """One line item from a group of entries: round each entry, apply
    each entry's own effective-dated rate, average the unit price."""
    total_minutes = 0
    total_amount = Decimal("0")
    customer = entries[0].customer
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
    contacts=None,
    bank_account=None,
    e_invoice_format: str = Invoice.EInvoiceFormat.NONE,
    extra_lines: list[dict] | None = None,
) -> Invoice:
    qs = TimeEntry.objects.filter(
        owner=owner,
        customer=customer,
        billable=True,
        invoice__isnull=True,
        contract__isnull=True,  # contract-covered entries bill via the contract
        end_time__isnull=False,  # running timers excluded
    ).select_related("customer", "project")
    if project:
        qs = qs.filter(project=project)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    entries = list(qs.order_by("date", "start_time"))
    if not entries and not extra_lines:
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
    issue_date = timezone.localdate()
    payment_terms_days = (
        customer.payment_terms_days
        if customer.payment_terms_days is not None
        else company.payment_terms_days if company else 14
    )
    default_vat_rate = (
        company.default_vat_rate
        if company and company.vat_enabled
        else Decimal("0") if company else Decimal("19")
    )
    invoice = Invoice.objects.create(
        owner=owner,
        number=next_number(owner, "invoice", {
            "customer": customer,
            "project": project,
            "invoice": SimpleNamespace(
                customer=customer, project=project, issue_date=issue_date
            ),
        }),
        customer=customer,
        project=project,
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=payment_terms_days),
        vat_rate=vat_rate if vat_rate is not None else default_vat_rate,
        currency=company.currency if company else "EUR",
        e_invoice_format=e_invoice_format,
        template=template,
        bank_account_override=bank_account,
    )

    invoice.contacts.set(
        contacts if contacts is not None else customer.contacts.filter(
            is_invoice_contact=True
        )
    )

    for position, (_, group) in enumerate(sorted(groups.items(), key=lambda g: g[0]), start=1):
        first = group[0]
        scope = first.project.name if first.project else customer.name
        if group_by == "entry":
            desc = f"{first.date} — {scope}: {first.description or 'Services'}"
        elif group_by == "day":
            desc = f"{first.date} — {scope}"
        else:
            desc = f"{scope} — consulting services"
        line = _line_for_entries(owner, group, desc)
        InvoiceLineItem.objects.create(
            owner=owner, invoice=invoice, position=position, **line
        )

    position = invoice.items.count()
    for line in extra_lines or []:
        position += 1
        InvoiceLineItem.objects.create(
            owner=owner,
            invoice=invoice,
            position=position,
            description=line["description"],
            quantity=line["quantity"],
            unit=line["unit"],
            unit_price=line["unit_price"],
        )

    invoice.recalc_totals()
    qs.update(invoice=invoice)
    return invoice
