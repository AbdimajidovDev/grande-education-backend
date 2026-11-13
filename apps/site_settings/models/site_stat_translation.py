
import uuid

from django.db import models


class SiteStatTranslation(models.Model):

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

    stat = models.ForeignKey(
        "site_settings.SiteStat",
        on_delete=models.CASCADE,
        related_name="translations",
    )

    language_code = models.CharField(
        max_length=2,
        choices=Language.choices,
    )

    label = models.CharField(max_length=255)

    hint = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Site Statistic Translation"
        verbose_name_plural = "Site Statistic Translations"
        ordering = ["stat", "language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["stat", "language_code"],
                name="unique_site_stat_language",
            ),
        ]

    def __str__(self):
        return f"{self.stat.number} ({self.language_code})"
