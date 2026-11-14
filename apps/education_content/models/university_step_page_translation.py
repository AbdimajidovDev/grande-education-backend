import uuid

from django.db import models

from .hybrid_teacher_translation import Language


class UniversityStepPageTranslation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    page = models.ForeignKey(
        "education_content.UniversityStepPage",
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language_code = models.CharField(
        max_length=2,
        choices=Language.choices,
    )
    title = models.CharField(max_length=255)
    subtitle = models.TextField()

    class Meta:
        verbose_name = "University Steps Page Translation"
        verbose_name_plural = "University Steps Page Translations"
        ordering = ("language_code",)
        constraints = [
            models.UniqueConstraint(
                fields=("page", "language_code"),
                name="unique_university_page_language",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.language_code})"