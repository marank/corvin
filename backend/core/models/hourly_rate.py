from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _

from .base import OwnedModel
from .customer import Customer
from .project import Project


class HourlyRate(OwnedModel):
    """Ledger-style effective-dated hourly rate.

    customer=null & project=null  -> company default
    customer set & project=null   -> customer-wide rate
    project set                   -> project-specific rate (most specific)
    """

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="hourly_rates",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="hourly_rates",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-valid_from"]

    def clean(self):
        if self.project and self.customer and self.project.customer_id != self.customer_id:
            raise ValidationError(_("Project does not belong to the selected customer."))
        if self.project and not self.customer:
            self.customer = self.project.customer

    def __str__(self):
        return f"{self.amount} €/h from {self.valid_from}"
