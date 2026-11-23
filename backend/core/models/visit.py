from django.db import models

from .base import OwnedModel
from .customer import Customer
from .project import Project


class OnSiteVisit(OwnedModel):
    number = models.CharField(max_length=50, blank=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="visits")
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name="visits",
        null=True,
        blank=True,
    )
    date = models.DateField()
    location = models.CharField(max_length=255, blank=True)
    arrival = models.TimeField(null=True, blank=True)
    departure = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "number"],
                condition=~models.Q(number=""),
                name="unique_visit_number_per_owner",
            )
        ]

    def __str__(self) -> str:
        return f"{self.customer.name} @ {self.date}"
