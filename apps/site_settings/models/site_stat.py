
import uuid

from django.db import models


class SiteStat(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    number = models.CharField(max_length=50)

    is_counter = models.BooleanField(default=False)

    order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Statistic"
        verbose_name_plural = "Site Statistics"
        ordering = ["order", "id"]
        indexes = [
            models.Index(
                fields=["is_active", "order"],
                name="site_stat_active_order_idx",
            ),
        ]

    def __str__(self):
        return self.number
