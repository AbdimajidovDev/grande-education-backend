
import uuid

from django.db import models
from django.core.validators import URLValidator


class SocialLink(models.Model):

    class Platform(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"
        YOUTUBE = "youtube", "YouTube"
        TIKTOK = "tiktok", "TikTok"
        LINKEDIN = "linkedin", "LinkedIn"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    office = models.ForeignKey(
        "site_settings.Office",
        on_delete=models.CASCADE,
        related_name="social_links",
    )

    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
    )

    username = models.CharField(
        max_length=100,
        blank=True,
    )

    url = models.URLField(
        max_length=1000,
        validators=[URLValidator(schemes=["https"])],
    )

    is_active = models.BooleanField(default=True)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Social Link"
        verbose_name_plural = "Social Links"
        ordering = ["order", "platform"]
        constraints = [
            models.UniqueConstraint(
                fields=["office", "platform"],
                name="unique_office_social_platform",
            ),
        ]

    def __str__(self):
        return f"{self.office.name} - {self.get_platform_display()}"
