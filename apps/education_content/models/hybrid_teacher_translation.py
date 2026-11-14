import uuid

from django.db import models


class Language(models.TextChoices):
    UZ = "uz", "Uzbek"
    RU = "ru", "Russian"
    EN = "en", "English"
    ZH = "zh", "Chinese"
    JA = "ja", "Japanese"
    DE = "de", "German"


class HybridTeacherTranslation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    teacher = models.ForeignKey(
        "education_content.HybridTeacher",
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language_code = models.CharField(
        max_length=2,
        choices=Language.choices,
    )
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255)
    features = models.JSONField(default=list)

    class Meta:
        verbose_name = "Hybrid Teacher Translation"
        verbose_name_plural = "Hybrid Teacher Translations"
        ordering = ("teacher", "language_code")
        constraints = [
            models.UniqueConstraint(
                fields=("teacher", "language_code"),
                name="unique_hybrid_teacher_language",
            ),
        ]

    def __str__(self):
        return f"{self.teacher} ({self.language_code})"