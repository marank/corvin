from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models

from .base import OwnedModel
from .customer import Customer
from .project import Project
from .support_contract import SupportContract
from .visit import OnSiteVisit


class TimeEntry(OwnedModel):
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="time_entries"
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, related_name="time_entries",
        null=True, blank=True,
    )
    visit = models.ForeignKey(
        OnSiteVisit, on_delete=models.SET_NULL, related_name="time_entries",
        null=True, blank=True,
    )
    contract = models.ForeignKey(
        SupportContract, on_delete=models.SET_NULL, related_name="time_entries",
        null=True, blank=True,
        help_text="Covered by this support contract's included hours "
                  "(excluded from normal consolidation)",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)  # null = running timer
    break_minutes = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0, editable=False)
    description = models.CharField(max_length=500, blank=True)
    billable = models.BooleanField(default=True)
    invoice = models.ForeignKey(
        "core.Invoice", on_delete=models.SET_NULL, related_name="time_entries",
        null=True, blank=True,
    )

    class Meta:
        ordering = ["-date", "-start_time"]

    @property
    def is_running(self) -> bool:
        return self.end_time is None

    @property
    def hours(self) -> float:
        return round(self.duration_minutes / 60, 2)

    def clean(self):
        if self.project and self.project.customer_id != self.customer_id:
            raise ValidationError(
                {"project": "Project does not belong to the customer."}
            )
        if self.contract:
            if self.contract.customer_id != self.customer_id:
                raise ValidationError(
                    "Contract does not belong to the entry's customer."
                )
            if self.contract.project_id and (
                self.contract.project_id != self.project_id
            ):
                raise ValidationError(
                    "Contract is limited to a different project."
                )
        if self.visit and self.visit.customer_id != self.customer_id:
            raise ValidationError(
                "Visit does not belong to the entry's customer."
            )

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            start = datetime.combine(self.date, self.start_time)
            end = datetime.combine(self.date, self.end_time)
            minutes = int((end - start).total_seconds() // 60) - self.break_minutes
            self.duration_minutes = max(minutes, 0)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} {self.date} ({self.hours}h)"
