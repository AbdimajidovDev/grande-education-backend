
import uuid

from django.db import models


class Office(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    is_active = models.BooleanField(default=True)

    is_main = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Office"
        verbose_name_plural = "Offices"
        ordering = ["-is_main", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_main"],
                condition=models.Q(is_main=True),
                name="unique_main_office",
            ),
        ]

    def __str__(self):
        return self.name
