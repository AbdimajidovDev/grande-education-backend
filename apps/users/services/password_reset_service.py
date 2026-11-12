
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.users.models import PasswordResetToken, User


class PasswordResetService:
    """Parolni tiklash tokenlarini boshqarish xizmatlari."""

    TOKEN_TTL_MINUTES = 15
    TOKEN_BYTES = 32

    @staticmethod
    def _generate_token() -> str:
        """Kriptografik xavfsiz tasodifiy token yaratadi."""
        return secrets.token_urlsafe(
            PasswordResetService.TOKEN_BYTES
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        """Tokenning SHA-256 hash qiymatini qaytaradi."""
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    @transaction.atomic
    def create_token(*, user: User) -> str:
        """
        Yangi reset token yaratadi.

        Avvalgi tokenlar bekor qilinadi.
        Bazada faqat token hash saqlanadi.
        """

        user = User.objects.select_for_update().get(pk=user.pk)

        PasswordResetToken.objects.filter(
            user=user,
            used_at__isnull=True,
        ).delete()

        raw_token = PasswordResetService._generate_token()
        token_hash = PasswordResetService._hash_token(raw_token)

        PasswordResetToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(
                minutes=PasswordResetService.TOKEN_TTL_MINUTES
            ),
        )

        return raw_token


    @staticmethod
    @transaction.atomic
    def mark_token_as_used(*, token_id: int) -> bool:
        """Tokenni bir marta ishlatilgan deb belgilaydi."""

        updated = PasswordResetToken.objects.filter(
            pk=token_id,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
            user__is_active=True,
        ).update(used_at=timezone.now())

        return updated == 1



    @staticmethod
    @transaction.atomic
    def reset_password(
        *,
        user_id: int,
        raw_token: str,
        new_password: str,
    ) -> bool:
        """Faqat tegishli foydalanuvchining parolini token orqali yangilaydi."""

        token_hash = PasswordResetService._hash_token(raw_token)

        reset_token = (
            PasswordResetToken.objects
            .select_for_update()
            .filter(
                user_id=user_id,
                token_hash=token_hash,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
                user__is_active=True,
            )
            .first()
        )

        if reset_token is None:
            return False

        user = User.objects.select_for_update().get(
            pk=reset_token.user_id,
            is_active=True,
        )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        now = timezone.now()

        PasswordResetToken.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=now)

        return True




