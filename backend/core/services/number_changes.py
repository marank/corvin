"""Changing a number by hand after it was assigned.

Numbers stay editable until they appear on a document that went out: an invoice's own number
once it is finalized, and the customer, project and contract numbers once a finalized invoice
names them (templates and invoice number formats can print them). Visits and tasks never reach
an invoice and stay editable.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils.translation import gettext as _

from core.models import DocumentArchive, Invoice
from core.models.base import OwnedModel

FINALIZED_STATUSES = [Invoice.Status.ISSUED, Invoice.Status.SENT, Invoice.Status.PAID]
# The Invoice field that points at each lockable model.
INVOICE_LINKS = {"Customer": "customer", "Project": "project", "SupportContract": "contract"}


def finalized_invoices() -> QuerySet[Invoice]:
    """Invoices that were finalized: issued, sent, paid, or cancelled after being archived."""
    archived = DocumentArchive.objects.filter(
        content_type=ContentType.objects.get_for_model(Invoice)
    ).values("object_id")
    return Invoice.objects.filter(Q(status__in=FINALIZED_STATUSES) | Q(id__in=archived))


def number_locked_annotation(model: type[OwnedModel]) -> Exists | None:
    """`Exists` for annotating querysets of a lockable model; None for models that never lock."""
    link = INVOICE_LINKS.get(model.__name__)
    if link is None:
        return None
    return Exists(finalized_invoices().filter(**{link: OuterRef("pk")}))


def is_number_locked(obj: OwnedModel) -> bool:
    annotated = getattr(obj, "number_locked", None)
    if annotated is not None:
        return bool(annotated)
    if isinstance(obj, Invoice):
        return finalized_invoices().filter(pk=obj.pk).exists()
    link = INVOICE_LINKS.get(type(obj).__name__)
    return link is not None and finalized_invoices().filter(**{link: obj}).exists()


def validate_number_change(obj: OwnedModel, number: str) -> str:
    """The cleaned new number for `obj`, or ValidationError if it may not take it."""
    number = number.strip()
    current = getattr(obj, "number", "")  # every numbered model has one
    if number == current:
        return number
    if not number:
        raise ValidationError(_("The number cannot be empty."))
    if is_number_locked(obj):
        raise ValidationError(
            _("The number appears on a finalized invoice and can no longer be changed.")
        )
    taken = (
        type(obj)
        ._default_manager.filter(**{"owner_id": obj.owner_id, "number": number})
        .exclude(pk=obj.pk)
        .exists()
    )
    if taken:
        raise ValidationError(_("This number is already taken."))
    return number
