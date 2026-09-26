from django.db import models

from .base import OwnedModel
from .customer import Customer


class Project(OwnedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        DONE = "done", "Done"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    budget_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    budget_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    rounding_increment_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.customer.name} — {self.name}"
