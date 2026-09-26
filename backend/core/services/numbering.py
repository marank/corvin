from django.db import transaction
from django.utils import timezone

from core.models import NumberSequence


def next_invoice_number(owner, prefix: str = "RE") -> str:
    year = timezone.localdate().year
    with transaction.atomic():
        seq, _ = (
            NumberSequence.objects.select_for_update()
            .get_or_create(owner=owner, year=year, prefix=prefix)
        )
        seq.last_number += 1
        seq.save(update_fields=["last_number"])
    return f"{prefix}-{year}-{seq.last_number:04d}"
