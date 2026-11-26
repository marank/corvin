"""Invoices written elsewhere (another program, by hand): uploaded as they went out, so the
time entries they billed count as invoiced and payments and reminders work as usual."""

from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from core.models import CompanySettings, Customer, Invoice, InvoiceLineItem, Project

from .archiving import store_document
from .consolidation import billable_entries, header_defaults


def _check_files(pdf: bytes, xml: bytes | None) -> None:
    if not pdf.startswith(b"%PDF"):
        raise ValidationError({"pdf": _("The file is no PDF.")})
    if xml is not None and not xml.lstrip().startswith(b"<"):
        raise ValidationError({"xml": _("The file is no XML.")})


@transaction.atomic
def import_external_invoice(
    *,
    owner: User,
    customer: Customer,
    number: str,
    issue_date: date,
    net: Decimal,
    pdf: bytes,
    project: Project | None = None,
    due_date: date | None = None,
    vat_rate: Decimal | None = None,
    xml: bytes | None = None,
    entry_ids: list[Any] | None = None,
) -> Invoice:
    """An issued invoice as uploaded: its number and amounts, its PDF (and XML) archived
    unchanged, the time entries it billed linked to its one line."""
    number = number.strip()
    if Invoice.objects.filter(owner=owner, number=number).exists():
        raise ValidationError({"number": _("This number is already taken.")})
    _check_files(pdf, xml)
    ids = [str(i) for i in entry_ids or []]
    entries = list(billable_entries(owner=owner, customer=customer, entry_ids=ids))
    if len(entries) != len(set(ids)):
        raise ValidationError({"entry_ids": _("Some time entries are not open (any more).")})

    company: CompanySettings | None = getattr(owner, "company_settings", None)
    defaults = header_defaults(customer, company, issue_date)
    vat_enabled = company.vat_enabled if company else True
    # Without a project of its own, an invoice billing one project's entries belongs to it.
    projects = {e.project_id for e in entries}
    if project is None and len(projects) == 1 and None not in projects:
        project = entries[0].project
    invoice = Invoice.objects.create(
        owner=owner,
        number=number,
        customer=customer,
        project=project,
        issue_date=issue_date,
        due_date=due_date or defaults["due_date"],
        vat_rate=(vat_rate if vat_rate is not None else defaults["vat_rate"])
        if vat_enabled
        else Decimal(0),
        currency=defaults["currency"],
        # An XML is the e-invoice itself, as with XRechnung.
        e_invoice_format=Invoice.EInvoiceFormat.XRECHNUNG if xml else Invoice.EInvoiceFormat.NONE,
        status=Invoice.Status.ISSUED,
        is_external=True,
    )
    item = InvoiceLineItem.objects.create(
        owner=owner,
        invoice=invoice,
        position=1,
        description=_("As per the attached invoice"),
        quantity=Decimal(1),
        unit=InvoiceLineItem.Unit.FLAT,
        unit_price=net,
    )
    item.time_entries.add(*entries)
    invoice.time_entries.add(*entries)
    invoice.recalc_totals()
    store_document(invoice, "pdf", pdf, ".pdf")
    if xml:
        store_document(invoice, "xml", xml, ".xml")
    return invoice
