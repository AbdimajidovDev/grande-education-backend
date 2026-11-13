
import uuid

from django.db import models


class Teacher(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,)
    full_name = models.CharField(max_length=255,)
    photo = models.ImageField(upload_to="teachers/photos/",)
    order = models.PositiveIntegerField(default=0,)
    is_active = models.BooleanField(default=True,)
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True,)

    class Meta:
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"
        ordering = ["order", "full_name"]
        indexes = [
            models.Index(
                fields=["is_active", "order"],
                name="teacher_active_order_idx",
            ),
        ]

    def __str__(self):
        return self.full_name

