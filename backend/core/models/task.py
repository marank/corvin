from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _

from .base import OwnedModel
from .customer import Customer
from .project import Project


class Task(OwnedModel):
    number = models.CharField(max_length=50, blank=True, db_index=True)

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    visit = models.ForeignKey(
        "core.OnSiteVisit",
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "due_date", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "number"],
                condition=~models.Q(number=""),
                name="unique_task_number_per_owner",
            )
        ]

    def clean(self):
        super().clean()
        if self.project and self.customer and (self.project.customer_id != self.customer_id):
            raise ValidationError({"project": _("Project does not belong to the customer.")})

    def save(self, *args, **kwargs):
        if self.project and not self.customer_id:
            self.customer = self.project.customer
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
