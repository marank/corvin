from django.db import models

from .base import OwnedModel


class TimeEntryBreak(OwnedModel):
    time_entry = models.ForeignKey("TimeEntry", on_delete=models.CASCADE, related_name="breaks")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"Break {self.time_entry} {self.start_datetime}"
