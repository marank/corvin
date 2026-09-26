from django.db import models

from .base import OwnedModel
from .project import Project


class Task(OwnedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="tasks",
        null=True, blank=True,
    )
    visit = models.ForeignKey(
        "core.OnSiteVisit", on_delete=models.SET_NULL, related_name="tasks",
        null=True, blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "due_date", "title"]

    def __str__(self):
        return self.title
