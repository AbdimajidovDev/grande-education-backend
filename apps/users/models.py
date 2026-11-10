from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    """CU Grande Education CMS foydalanuvchisi va xodimi."""

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Telefon raqami",
    )

    class Meta:
        db_table = "users"
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

        permissions = [
            (
                "assign_roles",
                "Foydalanuvchilarni rollarga biriktirish",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="unique_user_username_ci",
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.username