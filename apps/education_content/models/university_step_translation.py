import uuid

from django.db import models

from .hybrid_teacher_translation import Language


class UniversityStepTranslation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    step = models.ForeignKey(
        "education_content.UniversityStep",
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language_code = models.CharField(
        max_length=2,
        choices=Language.choices,
    )

    action_verb = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField()

    class Meta:
        verbose_name = "University Step Translation"
        verbose_name_plural = "University Step Translations"
        ordering = ("step", "language_code")
        constraints = [
            models.UniqueConstraint(
                fields=("step", "language_code"),
                name="unique_university_step_language",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.language_code})"
