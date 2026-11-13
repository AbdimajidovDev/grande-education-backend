
import uuid

from django.db import models
from django.core.validators import URLValidator


class ContactAddress(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    office = models.OneToOneField(
        "site_settings.Office",
        on_delete=models.CASCADE,
        related_name="address",
    )

    city = models.CharField(max_length=100)

    street = models.CharField(max_length=255)

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    map_url = models.URLField(
        max_length=1000,
        validators=[URLValidator(schemes=["https"])],
    )

    class Meta:
        verbose_name = "Contact Address"
        verbose_name_plural = "Contact Addresses"

    def __str__(self):
        return f"{self.city}, {self.street}"
