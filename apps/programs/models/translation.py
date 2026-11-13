
import uuid

from django.db import models


class ProgramTranslation(models.Model):

    class Language(models.TextChoices):
        UZ = "uz", "O'zbekcha"
        RU = "ru", "Русский"
        EN = "en", "English"
        ZH = "zh", "中文"
        JA = "ja", "日本語"
        DE = "de", "Deutsch"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="translations",
    )

    language_code = models.CharField(
        max_length=2,
        choices=Language.choices,
    )

    title = models.CharField(max_length=255)

    subtitle = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField()

    features = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "program_translations"

        constraints = [
            models.UniqueConstraint(
                fields=["program", "language_code"],
                name="unique_program_translation_language",
            ),
        ]

    def __str__(self):
        return f"{self.program.slug} - {self.language_code}"
