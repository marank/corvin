from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _

from .base import OwnedModel
from .customer import Customer
from .project import Project
from .support_contract import SupportContract
from .visit import OnSiteVisit


class TimeEntry(OwnedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    visit = models.ForeignKey(
        OnSiteVisit,
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        SupportContract,
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
        help_text="Covered by this support contract's included hours "
        "(excluded from normal consolidation)",
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)  # null = running timer
    normalized_start_datetime = models.DateTimeField(null=True, blank=True)
    normalized_end_datetime = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0, editable=False)
    description = models.CharField(max_length=500, blank=True)
    billable = models.BooleanField(default=True)
    invoice = models.ForeignKey(
        "core.Invoice",
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    # The line item this entry was billed on, so deleting the line from a draft
    # releases the entry for the next invoice.
    invoice_item = models.ForeignKey(
        "core.InvoiceLineItem",
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-start_datetime"]

    @property
    def is_running(self) -> bool:
        return self.end_datetime is None

    @property
    def hours(self) -> float:
        return round(self.duration_minutes / 60, 2)

    def clean(self):
        if self.customer:
            if self.project and self.project.customer_id != self.customer_id:
                raise ValidationError({"project": _("Project does not belong to the customer.")})
            if self.contract:
                if self.contract.customer_id != self.customer_id:
                    raise ValidationError(_("Contract does not belong to the entry's customer."))
                if self.contract.project_id and (self.contract.project_id != self.project_id):
                    raise ValidationError(_("Contract is limited to a different project."))
            if self.visit and self.visit.customer_id != self.customer_id:
                raise ValidationError(_("Visit does not belong to the entry's customer."))

    def _round_minutes(self, value: datetime, direction: str, increment: int) -> datetime:
        total_seconds = value.hour * 3600 + value.minute * 60 + value.second
        increment_seconds = increment * 60
        if direction == "forwards":
            rounded = (
                (total_seconds + increment_seconds - 1) // increment_seconds
            ) * increment_seconds
        elif direction == "backwards":
            rounded = (total_seconds // increment_seconds) * increment_seconds
        else:  # nearest
            rounded = (
                (total_seconds + increment_seconds // 2) // increment_seconds
            ) * increment_seconds
        midnight = value.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight + timedelta(seconds=rounded)

    def _apply_rounding(self):
        company = getattr(self.owner, "company_settings", None)
        if not company:
            return
        if self.start_datetime:
            self.normalized_start_datetime = self._round_minutes(
                self.start_datetime,
                company.time_rounding_start_direction,
                company.time_rounding_start_minutes,
            )
        if self.end_datetime:
            self.normalized_end_datetime = self._round_minutes(
                self.end_datetime,
                company.time_rounding_end_direction,
                company.time_rounding_end_minutes,
            )

    def _break_minutes(self) -> int:
        total = 0
        for b in self.breaks.all():
            if b.end_datetime:
                total += int((b.end_datetime - b.start_datetime).total_seconds() // 60)
        return total

    def save(self, *args, **kwargs):
        self._apply_rounding()
        if self.normalized_start_datetime and self.normalized_end_datetime:
            minutes = (
                int(
                    (self.normalized_end_datetime - self.normalized_start_datetime).total_seconds()
                    // 60
                )
                - self._break_minutes()
            )
            self.duration_minutes = max(minutes, 0)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        customer = self.customer.name if self.customer else "—"
        return f"{customer} {timezone.localdate(self.start_datetime)} ({self.hours}h)"
