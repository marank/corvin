import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import (
    Customer,
    Invoice,
    InvoiceLineItem,
    Project,
    TimeEntry,
)

from .numbering import next_number
from .rates import resolve_rate, round_up_minutes, rounding_increment


def _format_date(d: date, pattern: str) -> str:
    """Render a date with the company's Day.js-style pattern (DD, MM, YYYY, ...)."""
    tokens = {
        "YYYY": f"{d.year:04d}",
        "YY": f"{d.year % 100:02d}",
        "MM": f"{d.month:02d}",
        "DD": f"{d.day:02d}",
        "M": str(d.month),
        "D": str(d.day),
    }
    return re.sub(r"YYYY|YY|MM|DD|M|D", lambda m: tokens[m.group()], pattern)


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
        work_date = timezone.localdate(e.start_datetime)
        rate = resolve_rate(owner=owner, customer=customer, project=e.project, on_date=work_date)
        if rate is None:
            raise ValidationError(
                _("No hourly rate found for %(customer)s on %(date)s.")
                % {"customer": customer.name, "date": work_date.strftime("%d.%m.%Y")}
            )
        total_minutes += minutes
        total_amount += Decimal(minutes) / 60 * rate
    quantity = (Decimal(total_minutes) / 60).quantize(Decimal("0.01"))
    unit_price = (total_amount / quantity).quantize(Decimal("0.01")) if quantity else Decimal("0")
    return {
        "description": description,
        "quantity": quantity,
        "unit": InvoiceLineItem.Unit.HOURS,
        "unit_price": unit_price,
    }


def _default_vat_rate(company) -> Decimal:
    if company is None:
        return Decimal("19")
    return company.default_vat_rate if company.vat_enabled else Decimal("0")


def billable_entries(
    *,
    owner,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entry_ids: list | None = None,
):
    """Uninvoiced, billable, finished entries of a customer that a new invoice may bill.
    `entry_ids` narrows them to the user's selection (ids outside the set are ignored)."""
    qs = TimeEntry.objects.filter(
        owner=owner,
        customer=customer,
        billable=True,
        invoice__isnull=True,
        contract__isnull=True,  # contract-covered entries bill via the contract
        end_datetime__isnull=False,  # running timers excluded
    ).select_related("customer", "project")
    if project:
        qs = qs.filter(project=project)
    if date_from:
        qs = qs.filter(start_datetime__date__gte=date_from)
    if date_to:
        qs = qs.filter(start_datetime__date__lte=date_to)
    if entry_ids is not None:
        qs = qs.filter(id__in=entry_ids)
    return qs.order_by("start_datetime")


def build_lines(*, owner, customer: Customer, entries, group_by: str):
    """Group entries into line-item dicts. Returns [(line, entries_on_that_line), ...]."""
    groups: dict[tuple, list[TimeEntry]] = defaultdict(list)
    if group_by == "entry":
        for e in entries:
            groups[(e.id,)].append(e)
    elif group_by == "day":
        for e in entries:
            groups[(e.project_id, timezone.localdate(e.start_datetime))].append(e)
    elif group_by == "project":
        for e in entries:
            groups[(e.project_id,)].append(e)
    else:
        raise ValidationError(_("Unknown grouping: %(group_by)s") % {"group_by": group_by})

    company = getattr(owner, "company_settings", None)
    lines = []
    # Chronological lines, whatever order the entries were created in.
    for group in sorted(groups.values(), key=lambda g: min(e.start_datetime for e in g)):
        first = group[0]
        scope = first.project.name if first.project else customer.name
        work_date = _format_date(
            timezone.localdate(first.start_datetime),
            company.date_format if company else "DD.MM.YYYY",
        )
        if group_by == "entry":
            desc = f"{work_date} — {scope}: {first.description or 'Services'}"
        elif group_by == "day":
            desc = f"{work_date} — {scope}"
        else:
            desc = f"{scope} — consulting services"
        lines.append((_line_for_entries(owner, group, desc), group))
    return lines


def _line_total(line: dict) -> Decimal:
    return (Decimal(line["quantity"]) * Decimal(line["unit_price"])).quantize(Decimal("0.01"))


def preview(
    *,
    owner,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entry_ids: list | None = None,
    group_by: str = "entry",
    extra_lines: list[dict] | None = None,
) -> dict:
    """What `consolidate` would create, without writing anything."""
    entries = list(
        billable_entries(
            owner=owner,
            customer=customer,
            project=project,
            date_from=date_from,
            date_to=date_to,
            entry_ids=entry_ids,
        )
    )
    lines = [
        line
        for line, _group in build_lines(
            owner=owner, customer=customer, entries=entries, group_by=group_by
        )
    ]
    lines += [dict(line) for line in extra_lines or []]
    for line in lines:
        line["total"] = _line_total(line)
    subtotal = sum((line["total"] for line in lines), Decimal("0"))
    vat_rate = _default_vat_rate(getattr(owner, "company_settings", None))
    vat_amount = (subtotal * vat_rate / 100).quantize(Decimal("0.01"))
    return {
        "lines": lines,
        "entry_count": len(entries),
        "subtotal": subtotal,
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "total": subtotal + vat_amount,
    }


@transaction.atomic
def consolidate(
    *,
    owner,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entry_ids: list | None = None,
    group_by: str = "entry",
    vat_rate: Decimal | None = None,
    template=None,
    contacts=None,
    bank_account=None,
    e_invoice_format: str = Invoice.EInvoiceFormat.NONE,
    extra_lines: list[dict] | None = None,
) -> Invoice:
    qs = billable_entries(
        owner=owner,
        customer=customer,
        project=project,
        date_from=date_from,
        date_to=date_to,
        entry_ids=entry_ids,
    )
    entries = list(qs)
    if not entries and not extra_lines:
        raise ValidationError(_("No billable, uninvoiced time entries found."))
    lines = build_lines(owner=owner, customer=customer, entries=entries, group_by=group_by)

    company = getattr(owner, "company_settings", None)
    issue_date = timezone.localdate()
    payment_terms_days = (
        customer.payment_terms_days
        if customer.payment_terms_days is not None
        else company.payment_terms_days
        if company
        else 14
    )
    invoice = Invoice.objects.create(
        owner=owner,
        number=next_number(
            owner,
            "invoice",
            {
                "customer": customer,
                "project": project,
                "invoice": SimpleNamespace(
                    customer=customer, project=project, issue_date=issue_date
                ),
            },
        ),
        customer=customer,
        project=project,
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=payment_terms_days),
        vat_rate=vat_rate if vat_rate is not None else _default_vat_rate(company),
        currency=company.currency if company else "EUR",
        e_invoice_format=e_invoice_format,
        template=template,
        bank_account_override=bank_account,
    )

    invoice.contacts.set(
        contacts if contacts is not None else customer.contacts.filter(is_invoice_contact=True)
    )

    position = 0
    for line, group in lines:
        position += 1
        item = InvoiceLineItem.objects.create(
            owner=owner, invoice=invoice, position=position, **line
        )
        TimeEntry.objects.filter(id__in=[e.id for e in group]).update(
            invoice=invoice, invoice_item=item
        )

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
    return invoice
