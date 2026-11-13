
import uuid

from django.db import models


class Direction(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    inquiry_category = models.ForeignKey(
        "inquiries.InquiryCategory",
        on_delete=models.PROTECT,
        related_name="directions",
        null=True,
        blank=True,
    )

    chinese_char = models.CharField(
        max_length=10,
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
        verbose_name = "Direction"
        verbose_name_plural = "Directions"
        ordering = ["order", "id"]
        indexes = [
            models.Index(
                fields=["is_active", "order"],
                name="direction_active_order_idx",
            ),
        ]

    def __str__(self):
        return f"Direction {self.id}"
