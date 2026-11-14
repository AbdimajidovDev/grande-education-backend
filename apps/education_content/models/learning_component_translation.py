import uuid

from django.db import models

from .hybrid_teacher_translation import Language


class LearningComponentTranslation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    component = models.ForeignKey(
        "education_content.LearningComponent",
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language_code = models.CharField(
        max_length=2,
        choices=Language.choices,
    )
    title = models.CharField(max_length=255)
    description = models.TextField()

    class Meta:
        verbose_name = "Learning Component Translation"
        verbose_name_plural = "Learning Component Translations"
        ordering = ("component", "language_code")
        constraints = [
            models.UniqueConstraint(
                fields=("component", "language_code"),
                name="unique_learning_component_language",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.language_code})"