
import uuid

from django.db import models
from django.db.models import Q


class WorkingHour(models.Model):

    class Weekday(models.IntegerChoices):
        MONDAY = 1, "Monday"
        TUESDAY = 2, "Tuesday"
        WEDNESDAY = 3, "Wednesday"
        THURSDAY = 4, "Thursday"
        FRIDAY = 5, "Friday"
        SATURDAY = 6, "Saturday"
        SUNDAY = 7, "Sunday"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    office = models.ForeignKey(
        "site_settings.Office",
        on_delete=models.CASCADE,
        related_name="working_hours",
    )

    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
    )

    opens_at = models.TimeField(
        null=True,
        blank=True,
    )

    closes_at = models.TimeField(
        null=True,
        blank=True,
    )

    is_closed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Working Hour"
        verbose_name_plural = "Working Hours"
        ordering = ["weekday"]
        constraints = [
            models.UniqueConstraint(
                fields=["office", "weekday"],
                name="unique_office_weekday",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        is_closed=True,
                        opens_at__isnull=True,
                        closes_at__isnull=True,
                    )
                    | Q(
                        is_closed=False,
                        opens_at__isnull=False,
                        closes_at__isnull=False,
                        opens_at__lt=models.F("closes_at"),
                    )
                ),
                name="valid_office_working_hours",
            ),
        ]

    def __str__(self):
        return f"{self.office.name} - {self.get_weekday_display()}"
