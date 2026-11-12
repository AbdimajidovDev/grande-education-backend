
import hashlib

from rest_framework.throttling import SimpleRateThrottle


class PasswordResetRequestIPThrottle(SimpleRateThrottle):
    """Parol tiklash so'rovlarini IP bo'yicha cheklaydi."""

    scope = "password_reset_request_ip"

    def get_cache_key(self, request, view):
        ip_address = self.get_ident(request)

        if not ip_address:
            return None

        return self.cache_format % {
            "scope": self.scope,
            "ident": ip_address,
        }


class PasswordResetRequestEmailThrottle(SimpleRateThrottle):
    """Parol tiklash so'rovlarini email bo'yicha cheklaydi."""

    scope = "password_reset_request_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email", "")

        if not isinstance(email, str):
            return None

        email = email.strip().lower()

        if not email:
            return None

        email_hash = hashlib.sha256(
            email.encode("utf-8")
        ).hexdigest()

        return self.cache_format % {
            "scope": self.scope,
            "ident": email_hash,
        }


class PasswordResetConfirmIPThrottle(SimpleRateThrottle):
    """Parolni tiklash urinishlarini IP bo'yicha cheklaydi."""

    scope = "password_reset_confirm"

    def get_cache_key(self, request, view):
        ip_address = self.get_ident(request)

        if not ip_address:
            return None

        return self.cache_format % {
            "scope": self.scope,
            "ident": ip_address,
        }
