import uuid

from django.db import models


class HybridTeacher(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    badge = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    chinese_tag = models.CharField(max_length=50)
    image = models.ImageField(
        upload_to="education/hybrid/teachers/",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hybrid Teacher"
        verbose_name_plural = "Hybrid Teachers"
        ordering = ("order", "id")
        indexes = [
            models.Index(
                fields=("is_active", "order"),
                name="hybrid_tch_active_ord_idx",
            ),
        ]

    def __str__(self):
        return self.chinese_tag