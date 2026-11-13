
import uuid

from django.db import models


class Partner(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=255,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    logo = models.ImageField(
        upload_to="partners/logos/",
    )

    website = models.URLField(
        max_length=500,
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partners"
        ordering = ["order", "name"]
        indexes = [
            models.Index(
                fields=["is_active", "order"],
                name="partner_active_order_idx",
            ),
        ]

    def __str__(self):
        return self.name
