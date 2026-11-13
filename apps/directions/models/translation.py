
import uuid

from django.db import models


class DirectionTranslation(models.Model):

    class Language(models.TextChoices):
        UZ = "uz", "Uzbek"
        RU = "ru", "Russian"
        EN = "en", "English"
        ZH = "zh", "Chinese"
        JA = "ja", "Japanese"
        DE = "de", "German"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    direction = models.ForeignKey(
        "directions.Direction",
        on_delete=models.CASCADE,
        related_name="translations",
    )

    language_code = models.CharField(
        max_length=2,
        choices=Language.choices,
    )

    number_label = models.CharField(
        max_length=100,
    )

    title = models.CharField(
        max_length=255,
    )

    summary = models.TextField()

    tags = models.JSONField(
        default=list,
        blank=True,
    )

    goal_text = models.TextField()

    steps = models.JSONField(
        default=list,
    )

    note = models.TextField(
        blank=True,
    )

    path_text = models.CharField(
        max_length=255,
    )

    class Meta:
        verbose_name = "Direction Translation"
        verbose_name_plural = "Direction Translations"
        ordering = ["direction", "language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["direction", "language_code"],
                name="unique_direction_language",
            ),
        ]

    def __str__(self):
        return f"{self.direction_id} ({self.language_code})"
