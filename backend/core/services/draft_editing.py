"""Editing a draft invoice on the page that creates invoices.

The page holds the entries an invoice bills, a grouping and the user's texts per line;
`draft_state` recovers those from a saved draft, `update_draft` saves the page's state back:
header fields replaced, lines rebuilt, entries no longer on a line open again.
"""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from core.models import (
    BankAccount,
    CompanySettings,
    Contact,
    Customer,
    DocumentTemplate,
    Invoice,
    InvoiceLineItem,
    OnSiteVisit,
    Project,
    TimeEntry,
)

from .consolidation import (
    EntryLine,
    EntryLineSpec,
    Line,
    billable_entries,
    build_lines,
    create_items,
    header_defaults,
    make_entry_lines,
    only_project,
    spec_entry_ids,
)
from .number_changes import validate_number_change
from .travel import TravelLineSpec, travel_description, travel_lines

# Tried in this order when recovering an older draft's grouping; the first with most
# matches wins.
GROUPINGS = ("day", "entry", "project")


def _matching_lines(
    invoice: Invoice, entries: list[TimeEntry], group_by: str, texts: dict[frozenset[str], str]
) -> list[EntryLine]:
    """The lines `group_by` builds from the draft's entries that the draft has as well."""
    try:
        built = build_lines(
            owner=invoice.owner, customer=invoice.customer, entries=entries, group_by=group_by
        )
    except ValidationError:  # e.g. a rate removed since: this grouping can't be told
        return []
    return [line for line in built if _ids(line["entries"]) in texts]


def _ids(entries: Iterable[TimeEntry]) -> frozenset[str]:
    return frozenset(str(e.id) for e in entries)


class _DraftLines:
    """A draft's lines by what they bill: entries (texts by their ids), trips (texts that
    differ from the generated one, by line key) or nothing (own lines)."""

    def __init__(self, invoice: Invoice) -> None:
        self.texts: dict[frozenset[str], str] = {}
        self.entries: list[TimeEntry] = []
        self.trips: list[OnSiteVisit] = []
        self.trip_texts: dict[str, str] = {}
        self.own_lines: list[InvoiceLineItem] = []
        items = invoice.items.order_by("position").prefetch_related(
            "time_entries__project", "travel_visits__customer", "travel_visits__owner"
        )
        for item in items:
            self._add(item)

    def _add(self, item: InvoiceLineItem) -> None:
        item_entries = list(item.time_entries.all())
        item_trips = list(item.travel_visits.all())
        if item_entries:
            self.texts[_ids(item_entries)] = item.description
            self.entries += item_entries
        elif item_trips:
            self.trips += item_trips
            if item.description != travel_description(item_trips[0]):
                self.trip_texts[f"travel:{item_trips[0].id}"] = item.description
        else:
            self.own_lines.append(item)


def draft_state(invoice: Invoice) -> dict[str, Any]:
    """The entries a draft bills, the grouping its lines follow, the texts that differ from
    the generated ones (by line key), and its lines without entries."""
    lines_ = _DraftLines(invoice)
    texts, entries, own_lines = lines_.texts, lines_.entries, lines_.own_lines
    trips, trip_texts = lines_.trips, lines_.trip_texts
    entries.sort(key=lambda e: e.start_datetime)

    # Kept since the create page saves it; older drafts: the grouping that fits best.
    group_by, matched = invoice.group_by or "entry", list[EntryLine]()
    for candidate in [invoice.group_by] if invoice.group_by else GROUPINGS:
        lines = _matching_lines(invoice, entries, candidate, texts) if entries else []
        if len(lines) > len(matched):
            group_by, matched = candidate, lines
    return {
        "group_by": group_by,
        "entries": entries,
        "texts": {
            line["key"]: texts[_ids(line["entries"])]
            for line in matched
            if "key" in line and texts[_ids(line["entries"])] != line.get("default_description")
        },
        "trips": trips,
        "trip_texts": trip_texts,
        "own_lines": own_lines,
    }


@transaction.atomic
def update_draft(
    invoice: Invoice,
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
    travel: list[TravelLineSpec] | None = None,
    vat_rate: Decimal | None = None,
    template: DocumentTemplate | None = None,
    contacts: Iterable[Contact] | None = None,
    bank_account: BankAccount | None = None,
    e_invoice_format: str | None = None,
    issue_date: date | None = None,
    due_date: date | None = None,
    notes: str = "",
    number: str | None = None,
) -> Invoice:
    """Saves the page's state onto a draft: its customer stays, all else is replaced (the
    number only when given). Entries the draft billed and no line names any more are open
    again."""
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError(_("Only draft invoices can be edited."))
    if customer.pk != invoice.customer_id:
        raise ValidationError(_("The customer of an invoice cannot be changed."))
    if number is not None:
        invoice.number = validate_number_change(invoice, number)
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
    lines = make_entry_lines(
        owner=owner, customer=customer, entries=entries, group_by=group_by, entry_lines=entry_lines
    )
    trips = travel_lines(owner=owner, customer=customer, specs=travel or [], invoice=invoice)
    if not lines and not extra_lines and not trips:
        raise ValidationError(_("Invoice has no line items."))

    # Contract-covered entries stay linked to their contract's invoice (they are on no line).
    invoice.time_entries.filter(invoice_item__isnull=False).update(invoice=None, invoice_item=None)
    invoice.travel_visits.update(invoice=None, invoice_item=None)
    invoice.items.all().delete()

    company: CompanySettings | None = getattr(owner, "company_settings", None)
    invoice.issue_date = issue_date or invoice.issue_date
    defaults = header_defaults(customer, company, invoice.issue_date)
    invoice.project = project or only_project(lines)
    invoice.due_date = due_date or defaults["due_date"]
    if vat_rate is not None:
        invoice.vat_rate = vat_rate
    invoice.notes = notes
    invoice.e_invoice_format = e_invoice_format or invoice.e_invoice_format
    invoice.template = template
    invoice.bank_account_override = bank_account
    invoice.group_by = group_by if lines else ""
    invoice.save()
    if contacts is not None:
        invoice.contacts.set(contacts)
    create_items(invoice, lines, extra_lines, trips)
    return invoice
