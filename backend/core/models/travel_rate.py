from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _

from .base import OwnedModel
from .customer import Customer
from .project import Project


class TravelRate(OwnedModel):
    """What a trip to the customer costs, effective-dated and scoped like HourlyRate:
    project > customer > company default."""

    class Kind(models.TextChoices):
        FLAT = "flat", "Flat rate per trip"
        KM = "km", "Per kilometre"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="travel_rates", null=True, blank=True
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="travel_rates", null=True, blank=True
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.FLAT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Per km: the distance counts twice, there and back.
    round_trip = models.BooleanField(default=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-valid_from"]

    def clean(self) -> None:
        if self.project and self.customer and self.project.customer_id != self.customer_id:
            raise ValidationError(_("Project does not belong to the selected customer."))
        if self.project and not self.customer:
            self.customer = self.project.customer

    def __str__(self) -> str:
        return f"{self.amount} ({self.kind}) from {self.valid_from}"
