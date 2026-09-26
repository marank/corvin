import calendar
from datetime import date

from django.db import models

from .base import OwnedModel
from .customer import Customer
from .project import Project


def add_periods(d: date, period: str, count: int = 1) -> date:
    """Advance a date by N billing periods."""
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[period] * count
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class SupportContract(OwnedModel):
    """Recurring retainer: fixed price per period covering a fixed
    number of hours, with optional overage billing."""

    class Period(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="contracts"
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, related_name="contracts",
        null=True, blank=True,
        help_text="Limit coverage to this project; empty = whole customer",
    )
    name = models.CharField(max_length=255)
    included_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text="Hours included per period (0 = flat fee only)",
    )
    period = models.CharField(
        max_length=10, choices=Period.choices, default=Period.MONTHLY
    )
    fixed_price = models.DecimalField(max_digits=10, decimal_places=2)
    bill_overage = models.BooleanField(
        default=False, help_text="Bill hours beyond included_hours"
    )
    overage_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Rate for overage hours; empty = standard rate",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField()
    active = models.BooleanField(default=True)
    template = models.ForeignKey(
        "core.InvoiceTemplate", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="contracts",
    )

    class Meta:
        ordering = ["name"]

    def current_period(self) -> tuple[date, date]:
        """[start, end) of the current billing period."""
        start = self.next_billing_date
        # walk back one period to find the start
        prev = self.start_date
        while add_periods(prev, self.period) < start:
            prev = add_periods(prev, self.period)
        return prev, start

    def __str__(self):
        return f"{self.name} ({self.customer.name})"
