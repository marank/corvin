from django.db import models

from .base import OwnedModel
from .customer import Customer
from .project import Project


class OnSiteVisit(OwnedModel):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="visits"
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, related_name="visits",
        null=True, blank=True,
    )
    date = models.DateField()
    location = models.CharField(max_length=255, blank=True)
    arrival = models.TimeField(null=True, blank=True)
    departure = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.customer.name} @ {self.date}"
