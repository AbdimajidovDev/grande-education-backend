import uuid

from django.db import models


class LearningComponent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    icon = models.CharField(
        max_length=100,
        default="circle-help",
    )
    chinese_char = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Learning Component"
        verbose_name_plural = "Learning Components"
        ordering = ("order", "id")
        indexes = [
            models.Index(
                fields=("is_active", "order"),
                name="learning_comp_active_order_idx",
            ),
        ]

    def __str__(self):
        return self.chinese_char