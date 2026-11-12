
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
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="unique_user_email_ci",
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.username


class PasswordResetToken(models.Model):
    """Foydalanuvchining parolini tiklash uchun bir martalik token."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        verbose_name="Foydalanuvchi",
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Token hash",
    )

    expires_at = models.DateTimeField(
        verbose_name="Amal qilish muddati",
    )

    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ishlatilgan vaqt",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt",
    )

    class Meta:
        db_table = "password_reset_tokens"
        verbose_name = "Parolni tiklash tokeni"
        verbose_name_plural = "Parolni tiklash tokenlari"
        indexes = [
            models.Index(
                fields=["user", "expires_at"],
                name="pwd_reset_user_exp_idx",
            ),
        ]

    def __str__(self):
        return f"Password reset token: {self.user_id}"
