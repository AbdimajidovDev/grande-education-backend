import uuid

from django.db import models
from django.db.models import Q


class UniversityStepPage(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "University Steps Page"
        verbose_name_plural = "University Steps Pages"
        constraints = [
            models.UniqueConstraint(
                fields=("is_active",),
                condition=Q(is_active=True),
                name="unique_active_university_step_page",
            ),
        ]

    def __str__(self):
        return f"University Steps Page ({self.pk})"