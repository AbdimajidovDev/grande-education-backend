
import uuid

from django.core.validators import EmailValidator
from django.db import models


class ContactInfo(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    office = models.OneToOneField(
        "site_settings.Office",
        on_delete=models.CASCADE,
        related_name="contact_info",
    )

    phone_raw = models.CharField(max_length=20)

    email = models.EmailField(
        max_length=254,
        validators=[EmailValidator()],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"

    def __str__(self):
        return f"Contacts: {self.office.name}"
