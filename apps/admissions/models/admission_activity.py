
import uuid

from django.conf import settings
from django.db import models


class AdmissionActivity(models.Model):

    class Action(models.TextChoices):
        CREATED = "created", "Admission yaratildi"
        STAGE_CHANGED = "stage_changed", "Bosqich o'zgartirildi"
        CURATOR_ASSIGNED = "curator_assigned", "Kurator biriktirildi"
        COMMENT = "comment", "Izoh qo'shildi"
        DETAILS_UPDATED = "details_updated", "Ma'lumotlar yangilandi"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    admission = models.ForeignKey(
        "admissions.Admission",
        on_delete=models.CASCADE,
        related_name="activities",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_activities",
    )

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )

    old_value = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    new_value = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    note = models.TextField(
        blank=True,
        default="",
    )
    field_name = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admission_activities"
        verbose_name = "Admission faoliyati"
        verbose_name_plural = "Admission faoliyatlari"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["admission", "-created_at"],
                name="admission_activity_date_idx",
            ),
        ]
        permissions = [
            (
                "view_admission_activity",
                "Can view admission activity",
            ),
        ]

    def __str__(self):
        return f"{self.admission_id} - {self.action}"

