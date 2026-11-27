"""Trips to on-site visits, billed as invoice lines: a flat amount per trip or a rate per km.

Each visit with `bill_travel` is one trip. Rates resolve like hourly rates (project > customer >
company default, by the visit's date); per km the visit's distance, else the customer's, counts
once or there and back. Contracts with `travel_included` cover their customer's trips.
"""

from datetime import date
from typing import Any, NotRequired, TypedDict

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils.translation import override

from core.models import (
    CompanySettings,
    Customer,
    Invoice,
    InvoiceLineItem,
    OnSiteVisit,
    Project,
    SupportContract,
    TravelRate,
)

from .dates import format_date


class TravelLineSpec(TypedDict):
    """A trip the invoice bills, with the user's text (none: the generated one)."""

    visit_id: Any
    description: NotRequired[str | None]


def resolve_travel_rate(
    *, owner: User, customer: Customer, project: Project | None, on_date: date
) -> TravelRate | None:
    qs = TravelRate.objects.filter(owner=owner, valid_from__lte=on_date).order_by("-valid_from")
    if project is not None and (rate := qs.filter(project=project).first()):
        return rate
    if rate := qs.filter(customer=customer, project__isnull=True).first():
        return rate
    return qs.filter(customer__isnull=True, project__isnull=True).first()


def _travel_contracts(owner: User, customer: Customer) -> list[SupportContract]:
    return list(
        SupportContract.objects.filter(
            owner=owner, customer=customer, active=True, travel_included=True
        )
    )


def _covered(on_date: date, project_id: Any, contracts: list[SupportContract]) -> bool:
    return any(
        c.start_date <= on_date
        and (c.end_date is None or on_date <= c.end_date)
        and (c.project_id is None or c.project_id == project_id)
        for c in contracts
    )


def travel_included(
    *, owner: User, customer: Customer, project: Project | None, on_date: date
) -> bool:
    """Whether a contract covers trips to this customer on that day."""
    contracts = _travel_contracts(owner, customer)
    return _covered(on_date, project.pk if project else None, contracts)


def billable_visits(
    *,
    owner: User,
    customer: Customer,
    project: Project | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    visit_ids: list[Any] | None = None,
    invoice: Invoice | None = None,
) -> list[OnSiteVisit]:
    """The customer's trips not billed yet and not covered by a contract. With `invoice` (a
    draft being edited), the trips it bills count as open too."""
    open_ = Q(invoice__isnull=True)
    if invoice is not None:
        open_ |= Q(invoice=invoice)
    qs = OnSiteVisit.objects.filter(open_, owner=owner, customer=customer, bill_travel=True)
    if project:
        qs = qs.filter(project=project)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if visit_ids is not None:
        qs = qs.filter(id__in=visit_ids)
    contracts = _travel_contracts(owner, customer)
    visits = qs.select_related("customer", "project").order_by("date", "arrival", "number")
    return [v for v in visits if not _covered(v.date, v.project_id, contracts)]


def travel_description(visit: OnSiteVisit) -> str:
    company: CompanySettings | None = getattr(visit.owner, "company_settings", None)
    pattern = company.date_format if company else "DD.MM.YYYY"
    with override(settings.LANGUAGE_CODE):
        text = _("Travel %(date)s") % {"date": format_date(visit.date, pattern)}
    return f"{text} ({visit.number})" if visit.number else text


def travel_line(visit: OnSiteVisit, description: str | None = None) -> dict[str, Any]:
    """The invoice line for one trip. The visit's own price beats the rate's amount; without a
    rate it counts per km."""
    rate = resolve_travel_rate(
        owner=visit.owner, customer=visit.customer, project=visit.project, on_date=visit.date
    )
    when = visit.date.strftime("%d.%m.%Y")
    price = visit.travel_price if visit.travel_price is not None else rate and rate.amount
    if price is None:
        raise ValidationError(
            _("No travel rate found for %(customer)s on %(date)s.")
            % {"customer": visit.customer.name, "date": when}
        )
    line = {
        "description": description or travel_description(visit),
        "quantity": 1,
        "unit": InvoiceLineItem.Unit.FLAT,
        "unit_price": price,
    }
    if rate is None or rate.kind == TravelRate.Kind.KM:
        distance = visit.distance_km or visit.customer.travel_distance_km
        if not distance:
            raise ValidationError(_("No distance for the visit on %(date)s.") % {"date": when})
        line["quantity"] = distance * 2 if rate is None or rate.round_trip else distance
        line["unit"] = InvoiceLineItem.Unit.KM
    return line


def travel_lines(
    *, owner: User, customer: Customer, specs: list[TravelLineSpec], invoice: Invoice | None = None
) -> list[tuple[OnSiteVisit, dict[str, Any]]]:
    """The trips the user put on the invoice, each once, with its line."""
    ids = [str(spec["visit_id"]) for spec in specs]
    visits = {
        str(v.id): v
        for v in billable_visits(owner=owner, customer=customer, visit_ids=ids, invoice=invoice)
    }
    if len(set(ids)) != len(ids) or any(i not in visits for i in ids):
        raise ValidationError(_("Some trips are not open (any more)."))
    return [
        (
            visits[str(spec["visit_id"])],
            travel_line(visits[str(spec["visit_id"])], spec.get("description")),
        )
        for spec in specs
    ]
