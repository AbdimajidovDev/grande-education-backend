from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


def dummy_get_response(request):
    return None


class CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_cookie_name = settings.AUTH_COOKIE_ACCESS
        raw_token = request.COOKIES.get(access_cookie_name)

        # Cookie mavjud bo'lmasa, Bearer token orqali tekshiramiz.
        if raw_token is None:
            return super().authenticate(request)

        validated_token = self.get_validated_token(raw_token)

        # Cookie orqali autentifikatsiyada CSRF tekshiruvi majburiy.
        self.enforce_csrf(request)

        return self.get_user(validated_token), validated_token

    @staticmethod
    def enforce_csrf(request):
        check = CSRFCheck(dummy_get_response)
        check.process_request(request)

        reason = check.process_view(request, None, (), {})

        if reason:
            raise PermissionDenied(f"CSRF validation failed: {reason}")

