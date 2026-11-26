import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, NotRequired, TypedDict

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from core.models import (
    BankAccount,
    CompanySettings,
    Contact,
    Customer,
    DocumentTemplate,
    Invoice,
    InvoiceLineItem,
    Project,
    TimeEntry,
)

from .numbering import next_number
from .rates import resolve_rate, round_up_minutes, rounding_increment


class Line(TypedDict):
    """An invoice line before it is saved (`total` only in previews)."""

    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: NotRequired[Decimal]


class EntryLine(TypedDict):
    """A line built from time entries: the line and the entries it bills. Grouped lines
    also carry their group's key and generated text."""

    line: Line
    entries: list[TimeEntry]
    key: NotRequired[str]
    default_description: NotRequired[str]


class EntryLineSpec(TypedDict):
    """A line the user put together: these entries, billed under this text."""

    entry_ids: list[Any]
    description: str


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


def _line_for_entries(
    owner: User, customer: Customer, entries: list[TimeEntry], description: str
) -> Line:
    """One line item from a group of entries: round each entry, apply
    each entry's own effective-dated rate, average the unit price."""
    total_minutes = 0
    total_amount = Decimal(0)
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
    unit_price = (total_amount / quantity).quantize(Decimal("0.01")) if quantity else Decimal(0)
    return {
        "description": description,
        "quantity": quantity,
        "unit": InvoiceLineItem.Unit.HOURS,
        "unit_price": unit_price,
    }


def _entry_text(description: str, scope: str) -> str:
    """The entry's description, prefixed with the project/customer unless it already names it."""
    if not description:
        description = _("Services")
        return f"{scope}: {description}"
    if scope.casefold() in description.casefold():
        return description
    return f"{scope}: {description}"


def _default_vat_rate(company: CompanySettings | None) -> Decimal:
    if company is None:
        return Decimal(19)
    return company.default_vat_rate if company.vat_enabled else Decimal(0)


def header_defaults(
    customer: Customer, company: CompanySettings | None, issue_date: date
) -> dict[str, Any]:
    """What an invoice gets for the fields left open: due after the customer's (else the
    company's) payment terms, the company's VAT rate and currency, the customer's e-invoice."""
    payment_terms_days = (
        customer.payment_terms_days
        if customer.payment_terms_days is not None
        else company.payment_terms_days
        if company
        else 14
    )
    return {
        "due_date": issue_date + timedelta(days=payment_terms_days),
        "vat_rate": _default_vat_rate(company),
        "currency": company.currency if company else "EUR",
        "e_invoice_format": customer.e_invoice_format,
    }


def billable_entries(
    *,
    owner: User,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entry_ids: list[Any] | None = None,
    invoice: Invoice | None = None,
) -> QuerySet[TimeEntry]:
    """Uninvoiced, billable, finished entries of a customer that a new invoice may bill.
    `entry_ids` narrows them to the user's selection (ids outside the set are ignored).
    With `invoice` (a draft being edited), the entries it bills count as open too."""
    open_ = Q(invoice__isnull=True)
    if invoice is not None:
        open_ |= Q(invoice=invoice)
    qs = TimeEntry.objects.filter(
        open_,
        owner=owner,
        customer=customer,
        billable=True,
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


# What puts entries on the same line, per `group_by`; also the line's key (as text).
_GROUP_KEYS: dict[str, Callable[[TimeEntry], tuple[Any, ...]]] = {
    "entry": lambda e: (e.id,),
    "day": lambda e: (e.project_id, timezone.localdate(e.start_datetime)),
    "project": lambda e: (e.project_id,),
}


def _group_entries(
    entries: list[TimeEntry], group_by: str
) -> dict[tuple[Any, ...], list[TimeEntry]]:
    key = _GROUP_KEYS.get(group_by)
    if key is None:
        raise ValidationError(_("Unknown grouping: %(group_by)s") % {"group_by": group_by})
    groups: dict[tuple[Any, ...], list[TimeEntry]] = defaultdict(list)
    for e in entries:
        groups[key(e)].append(e)
    return groups


def _line_description(group_by: str, first: TimeEntry, scope: str, work_date: str) -> str:
    """Per entry its date and text, per day the date, per project the project's name;
    the entries behind a line are listed in the invoice's time report."""
    # Line texts end up on the document, which always renders in LANGUAGE_CODE.
    with override(settings.LANGUAGE_CODE):
        if group_by == "entry":
            return f"{work_date} — {_entry_text(first.description, scope)}"
        if group_by == "day":
            return work_date
        return scope


def build_lines(
    *, owner: User, customer: Customer, entries: list[TimeEntry], group_by: str
) -> list[EntryLine]:
    """Group entries into lines, chronologically, with generated texts."""
    groups = _group_entries(entries, group_by)
    company: CompanySettings | None = getattr(owner, "company_settings", None)
    lines: list[EntryLine] = []
    for group_key, group in sorted(
        groups.items(), key=lambda item: min(e.start_datetime for e in item[1])
    ):
        first = group[0]
        scope = first.project.name if first.project else customer.name
        work_date = _format_date(
            timezone.localdate(first.start_datetime),
            company.date_format if company else "DD.MM.YYYY",
        )
        key = ":".join([group_by, *(str(part) for part in group_key)])
        default = _line_description(group_by, first, scope, work_date)
        lines.append(
            {
                "line": _line_for_entries(owner, customer, group, default),
                "entries": group,
                "key": key,
                "default_description": default,
            }
        )
    return lines


def lines_from_specs(
    *, owner: User, customer: Customer, entries: list[TimeEntry], specs: list[EntryLineSpec]
) -> list[EntryLine]:
    """The user's lines: each bills the given entries (open ones of the customer, each on
    one line only) under the given text; hours and prices come from the entries."""
    by_id = {str(e.id): e for e in entries}
    used: set[str] = set()
    lines: list[EntryLine] = []
    for spec in specs:
        ids = [str(entry_id) for entry_id in spec["entry_ids"]]
        if not ids or any(i not in by_id or i in used for i in ids):
            raise ValidationError(_("A line bills time entries that are not open or twice."))
        used.update(ids)
        group = [by_id[i] for i in ids]
        lines.append(
            {
                "line": _line_for_entries(owner, customer, group, spec["description"]),
                "entries": group,
            }
        )
    return lines


def make_entry_lines(
    *,
    owner: User,
    customer: Customer,
    entries: list[TimeEntry],
    group_by: str,
    entry_lines: list[EntryLineSpec] | None,
) -> list[EntryLine]:
    if entry_lines is None:
        return build_lines(owner=owner, customer=customer, entries=entries, group_by=group_by)
    return lines_from_specs(owner=owner, customer=customer, entries=entries, specs=entry_lines)


def spec_entry_ids(entry_lines: list[EntryLineSpec] | None, entry_ids: Any) -> Any:
    """With explicit lines, the entries are the ones they name."""
    if entry_lines is None:
        return entry_ids
    return [entry_id for spec in entry_lines for entry_id in spec["entry_ids"]]


def _line_context(entries: list[TimeEntry]) -> dict[str, Any]:
    """What a preview shows next to a line: its entries, project and period."""
    days = [timezone.localdate(e.start_datetime) for e in entries]
    projects = {e.project.name for e in entries if e.project}
    return {
        "entry_ids": [e.id for e in entries],
        "project_name": projects.pop() if len(projects) == 1 else None,
        "date_from": min(days),
        "date_to": max(days),
    }


def only_project(lines: list[EntryLine]) -> Project | None:
    """The project all lines bill, if they bill exactly one."""
    projects = {e.project_id: e.project for built in lines for e in built["entries"]}
    return next(iter(projects.values())) if len(projects) == 1 else None


def _line_total(line: Mapping[str, Any]) -> Decimal:
    return (Decimal(line["quantity"]) * Decimal(line["unit_price"])).quantize(Decimal("0.01"))


def preview(
    *,
    owner: User,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entry_ids: list[Any] | None = None,
    group_by: str = "entry",
    entry_lines: list[EntryLineSpec] | None = None,
    extra_lines: list[Line] | None = None,
    vat_rate: Decimal | None = None,
    invoice: Invoice | None = None,
) -> dict[str, Any]:
    """What `consolidate` would create, without writing anything. Lines built from entries
    carry their entries (and, grouped, their key and generated text), so a client can take
    them over and edit their text."""
    entries = list(
        billable_entries(
            owner=owner,
            customer=customer,
            project=project,
            date_from=date_from,
            date_to=date_to,
            entry_ids=spec_entry_ids(entry_lines, entry_ids),
            invoice=invoice,
        )
    )
    built = make_entry_lines(
        owner=owner, customer=customer, entries=entries, group_by=group_by, entry_lines=entry_lines
    )
    lines: list[dict[str, Any]] = [
        {
            **item["line"],
            **_line_context(item["entries"]),
            "key": item.get("key"),
            "default_description": item.get("default_description", item["line"]["description"]),
        }
        for item in built
    ]
    lines += [{**line, "key": None, "entry_ids": []} for line in extra_lines or []]
    for line in lines:
        line["total"] = _line_total(line)
    subtotal = sum((line["total"] for line in lines), Decimal(0))
    if vat_rate is None:
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
    owner: User,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entry_ids: list[Any] | None = None,
    group_by: str = "entry",
    entry_lines: list[EntryLineSpec] | None = None,
    vat_rate: Decimal | None = None,
    template: DocumentTemplate | None = None,
    contacts: Iterable[Contact] | None = None,
    bank_account: BankAccount | None = None,
    e_invoice_format: str | None = None,
    extra_lines: list[Line] | None = None,
    issue_date: date | None = None,
    due_date: date | None = None,
    notes: str = "",
) -> Invoice:
    qs = billable_entries(
        owner=owner,
        customer=customer,
        project=project,
        date_from=date_from,
        date_to=date_to,
        entry_ids=spec_entry_ids(entry_lines, entry_ids),
    )
    entries = list(qs)
    if not entries and not extra_lines:
        raise ValidationError(_("No billable, uninvoiced time entries found."))
    lines = make_entry_lines(
        owner=owner, customer=customer, entries=entries, group_by=group_by, entry_lines=entry_lines
    )
    # Without a project of its own, an invoice that bills one project belongs to it.
    project = project or only_project(lines)

    company: CompanySettings | None = getattr(owner, "company_settings", None)
    issue_date = issue_date or timezone.localdate()
    defaults = header_defaults(customer, company, issue_date)
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
        due_date=due_date or defaults["due_date"],
        vat_rate=vat_rate if vat_rate is not None else defaults["vat_rate"],
        notes=notes,
        currency=defaults["currency"],
        e_invoice_format=e_invoice_format or defaults["e_invoice_format"],
        template=template,
        bank_account_override=bank_account,
        group_by=group_by if lines else "",
    )

    invoice.contacts.set(
        contacts if contacts is not None else customer.contacts.filter(is_invoice_contact=True)
    )

    create_items(invoice, lines, extra_lines)
    return invoice


def create_items(invoice: Invoice, lines: list[EntryLine], extra_lines: list[Line] | None) -> None:
    """Saves the lines in order, entry lines first, links their entries and totals up."""
    position = 0
    for built in lines:
        position += 1
        item = InvoiceLineItem.objects.create(
            owner=invoice.owner, invoice=invoice, position=position, **built["line"]
        )
        TimeEntry.objects.filter(id__in=[e.id for e in built["entries"]]).update(
            invoice=invoice, invoice_item=item
        )

    for line in extra_lines or []:
        position += 1
        InvoiceLineItem.objects.create(
            owner=invoice.owner,
            invoice=invoice,
            position=position,
            description=line["description"],
            quantity=line["quantity"],
            unit=line["unit"],
            unit_price=line["unit_price"],
        )

    invoice.recalc_totals()
