
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from urllib.parse import urlencode

from apps.users.services.password_reset_service import PasswordResetService

User = get_user_model()

logger = logging.getLogger(__name__)


class ForgotPasswordService:
    """Parolni tiklash email xabarlarini boshqarish."""

    @staticmethod
    def request_password_reset(*, email: str) -> None:
        """Faol foydalanuvchiga parolni tiklash havolasini yuboradi."""

        user = User.objects.filter(
            email__iexact=email.strip(),
            is_active=True,
        ).first()

        if user is None:
            return

        raw_token = PasswordResetService.create_token(user=user)

        uid = urlsafe_base64_encode(force_bytes(user.pk))

        query_params = urlencode({
            "uid": uid,
            "token": raw_token,
        })

        reset_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/"
            f"?{query_params}"
        )

        subject = "CU Grande Education — Parolni tiklash"

        message = (
            f"Assalomu alaykum, {user.get_full_name() or user.username}!\n\n"
            "Parolingizni tiklash uchun quyidagi havolaga o'ting:\n\n"
            f"{reset_url}\n\n"
            "Havola 15 daqiqa davomida amal qiladi.\n"
            "Agar parolni tiklash so'rovini siz yubormagan bo'lsangiz, "
            "ushbu xabarni e'tiborsiz qoldiring.\n\n"
            "CU Grande Education"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Password reset email delivery failed for user_id=%s",
                user.pk,
            )
            raise
